#!/usr/bin/env python
"""
Create labels of outlier interferogram pixels.

Uses the averaged unwrapped igrams per date.
"""
import os
import numpy as np

from . import utils
from . import sario
from .logger import get_log, log_runtime
from .deramp import remove_ramp

log = get_log()


def label_outliers(
    fname=None,
    stack=None,
    outfile="labels.nc",
    nsigma=5,
    level="pixel",
    min_spread=0.5,
):
    if stack is None:
        import xarray as xr

        stack = xr.open_dataarray(fname)
    log.info("Computing {} sigma outlier labels at {} level.".format(nsigma, level))

    if level == "pixel":
        # Use all pixel absolute values here, shape: (ndates, rows, cols)
        stack_data = np.abs(stack)
        labels, threshold = label(stack_data, nsigma=nsigma, min_spread=min_spread)
    elif level == "scene":
        # Use just scene-level variance, shape: (ndates, 1, 1)
        stack_data = np.var(stack, axis=(1, 2), keepdims=True)
        labels, threshold = label(stack_data, nsigma=nsigma, min_spread=min_spread)
        # Add squeeze for the scene-level case, dont need lat/lon dims
        labels = labels.squeeze()
        stack_data = stack_data.squeeze()
        threshold = threshold.squeeze()
    else:
        raise ValueError("`level` must be 'pixel' or 'scene'")

    # Rename the xarray dataarrays
    labels = labels.rename("labels")
    stack_data = stack_data.rename("data")
    threshold = threshold.rename("threshold")
    if outfile:
        log.info("Saving outlier labels to {}:/labels".format(outfile))
        labels.to_netcdf(outfile)
        log.info("Saving data to {}:/data".format(outfile))
        stack_data.to_netcdf(outfile, mode="a")
        log.info("Saving threshold to {}:/threshold".format(outfile))
        threshold.to_netcdf(outfile, mode="a")
    return labels, threshold


def label(
    data,
    nsigma=5,
    min_spread=0.5,
):
    med = data.median(axis=0)
    spread = np.maximum(min_spread, nsigma * mad(data, axis=0))
    threshold = med + spread
    return (data > threshold), threshold


def mad(stack, axis=0, scale=1.4826):
    """Median absolute deviation,

    default is scaled such that +/-MAD covers 50% (between 1/4 and 3/4)
    of the standard normal cumulative distribution
    """
    stack_abs = np.abs(stack)
    med = np.nanmedian(stack_abs, axis=axis)
    return scale * np.nanmedian(np.abs(stack_abs - med), axis=axis)


@log_runtime
def create_averages(
    search_path=".",
    ext=".unw",
    rsc_file=None,
    deramp=True,
    avg_file="average_slcs.nc",
    overwrite=False,
    normalize_time=False,
    band=2,
    ds_name="igrams",
    **kwargs,
):
    """Create a NetCDF stack of "average interferograms" for each date

    Args:
        search_path (str):
            directory to find igrams
        ext (str):
            extension name of unwrapped interferograms (default = .unw)
        rsc_file (str):
            filename of .rsc resource file, if loading binary files like snaphu outputs
        deramp (bool):
            remove a linear ramp from unwrapped igrams when averaging
        avg_file (str):
            name of output file to save stack
        overwrite (bool):
            clobber current output file, if exists
        normalize_time (bool):
            Divide igram phase by temporal baseline (default = false)
            true: units = [rad / day], false: units = [rad]
        band (int):
            if using rasterio to load igrams, which image band to load
        ds_name (str):
            Name of the data variable used in the netcdf stack
    """
    import netCDF4 as nc

    if os.path.exists(avg_file) and not overwrite:
        log.info("{} exists, not overwriting.".format(avg_file))
        return avg_file

    log.info("Searching for igrams in {} with extention {}".format(search_path, ext))
    ifg_date_list = utils.find_igrams(directory=search_path, ext=ext)
    unw_file_list = utils.find_igrams(directory=search_path, ext=ext, parse=False)
    sar_date_list = utils.dates_from_igrams(ifg_date_list)

    nigrams, ndates = len(ifg_date_list), len(sar_date_list)
    log.info("Found {} igrams, {} unique SAR dates".format(nigrams, ndates))

    utils.create_empty_nc_stack(
        avg_file,
        date_list=sar_date_list,
        rsc_file=rsc_file,
        gdal_file=unw_file_list[0],
        stack_data_name=ds_name,
        overwrite=overwrite,
    )

    f = nc.Dataset(avg_file, mode="r+")
    ds = f["igrams"]
    _, rows, cols = ds.shape

    # TODO: support masks or not?
    # Get masks for deramping
    # mask_igram_date_list = utils.load_intlist_from_h5(mask_fname)
    out_mask = np.zeros((rows, cols)).astype(bool)

    for (idx, gdate) in enumerate(sar_date_list):
        cur_unws = [
            (f, date_pair)
            for (date_pair, f) in zip(ifg_date_list, unw_file_list)
            if gdate in date_pair
        ]
        log.info(
            "Averaging {} igrams for {} ({} out of {})".format(
                len(cur_unws), gdate, idx + 1, len(sar_date_list)
            )
        )

        # reset the matrix to all zeros
        out = 0
        for unwf, date_pair in cur_unws:
            img = sario.load(unwf, rsc_file=rsc_file, band=band)
            if normalize_time:
                img /= (date_pair[1] - date_pair[0]).days
            out += img

            # mask_idx = mask_igram_date_list.index(date_pair)
            # out_mask |= mask_stack[mask_idx]

        out /= len(cur_unws)

        if deramp:
            out = remove_ramp(out, deramp_order=1, mask=out_mask)
        else:
            out[out_mask] = np.nan

        # Write the single layer out
        ds[idx, :, :] = out

    # Close to save it
    f.close()
    return avg_file
