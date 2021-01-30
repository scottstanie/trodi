#!/usr/bin/env python
"""
Create labels of outlier interferogram pixels.

Uses the averaged unwrapped igrams per date.
"""
import numpy as np

# faster on nans
from bottleneck import median

from . import utils
from . import sario
from .logger import get_log, log_runtime
from .deramp import remove_ramp

log = get_log()


def mad(stack, axis=0, scale=1.4826):
    """Median absolute deviation,

    default is scaled such that +/-MAD covers 50% (between 1/4 and 3/4)
    of the standard normal cumulative distribution
    """
    stack_abs = np.abs(stack)
    med = median(stack_abs, axis=0)
    return scale * median(np.abs(stack_abs - med), axis=axis)


def label_outliers(
    fname=None,
    stack=None,
    outfile="labels.nc",
    nsigma=5,
    axis=0,
    min_spread=0.5,
):
    # TODO: out of core? worth doing?
    if stack is None:
        import xarray as xr

        stack = xr.open_dataarray(fname)

    stack_abs = np.abs(stack)
    median_img = stack_abs.median(axis=axis)
    spread = np.maximum(min_spread, nsigma * mad(stack_abs))
    threshold_img = median_img + spread

    labels = stack_abs > threshold_img
    if outfile:
        log.info("Saving outlier labels to " + outfile)
        labels.to_netcdf(outfile)
    return labels


@log_runtime
def create_averages(
    search_path=".",
    ext=".unw",
    rsc_file=None,
    deramp=True,
    outfile="average_slcs.nc",
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
        outfile (str):
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

    log.info("Searching for igrams in {} with extention {}".format(search_path, ext))
    ifg_date_list = utils.find_igrams(directory=search_path, ext=ext)
    unw_file_list = utils.find_igrams(directory=search_path, ext=ext, parse=False)
    sar_date_list = utils.dates_from_igrams(ifg_date_list)

    nigrams, ndates = len(ifg_date_list), len(sar_date_list)
    log.info("Found {} igrams, {} unique SAR dates".format(nigrams, ndates))

    utils.create_empty_nc_stack(
        outfile,
        date_list=sar_date_list,
        rsc_file=rsc_file,
        gdal_file=unw_file_list[0],
        stack_data_name=ds_name,
        overwrite=overwrite,
    )

    f = nc.Dataset(outfile, mode="r+")
    ds = f["igrams"]
    _, rows, cols = ds.shape

    # # TODO: make ignore into a CLI option
    # sar_date_list, ifg_date_list = utils.ignore_geo_dates(
    #     sar_date_list,
    #     ifg_date_list,
    #     ignore_file=os.path.join(search_path, "geolist_ignore.txt"),
    # )

    out_mask = np.zeros((rows, cols)).astype(bool)

    # TODO: support masks or not?
    # Get masks for deramping
    # mask_igram_date_list = utils.load_intlist_from_h5(mask_fname)

    for (idx, gdate) in enumerate(sar_date_list):
        # outfile = "avg_" + gdate.strftime("%Y%m%d") + ".tif"
        # if os.path.exists(outfile) and not overwrite:
        # print(f"{outfile} exists: skipping")
        # continue

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
    return outfile
