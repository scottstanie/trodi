#!/usr/bin/env python
"""
Create labels of outlier interferogram pixels.

Uses the averaged unwrapped igrams per date.
"""
import os

import numpy as np

from . import sario, utils
from .deramp import remove_ramp
from .logger import get_log, log_runtime

log = get_log()


def label_outliers(
    fname=None,
    stack=None,
    outfile="labels.nc",
    nsigma=5,
    level="pixel",
    min_spread=0.5,
):
    """

    Parameters
    ----------
    fname : str
        Filename of average interferogram (Default value = None)
    stack : xr.Dataset
        xr.Dataset containing the average, alternative to `fname` (Default value = None)
    outfile : str
        Name of output file to save (Default value = "labels.nc")
    nsigma : int
        Cutoff level to label outliers (Default value = 5)
    level : str
        Type of outlier labeling to use.
            "pixel" runs on each pixel individually
            "scene" takes each image variance as the input
            (Default value = "pixel")
    min_spread : float
        minimum value to use for calculating variances (Default value = 0.5)

    Returns
    -------
        labels, threshold: The labeled xr.Dataset and the threshold used to label outliers
    """
    if stack is None:
        import xarray as xr

        stack = xr.open_dataarray(fname, engine="h5netcdf")
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
        labels.to_netcdf(outfile, engine="h5netcdf")
        log.info("Saving data to {}:/data".format(outfile))
        stack_data.to_netcdf(outfile, mode="a", engine="h5netcdf")
        log.info("Saving threshold to {}:/threshold".format(outfile))
        threshold.to_netcdf(outfile, mode="a", engine="h5netcdf")
    return labels, threshold


def label(
    data,
    nsigma=5,
    min_spread=0.5,
):
    """Label outliers using the average interferograms

    Parameters
    ----------
    data : xr.DataArray (or np.ndarray)


    nsigma : int
         (Default value = 5)
    min_spread : float
         (Default value = 0.5)

    Returns
    -------
    labels : xr.DataArray
    threshold : xr.DataArray
    """
    med = data.median(axis=0)
    spread = np.maximum(min_spread, nsigma * mad(data, axis=0))
    threshold = med + spread
    return (data > threshold), threshold


def mad(stack, axis=0, scale=1.4826):
    """Median absolute deviation,

    Default `scale` is such that +/-MAD covers 50% (between 1/4 and 3/4)
    of the standard normal cumulative distribution

    Parameters
    ----------
    stack : xr.DataArray, or np.ndarray

    axis : int, optional
        axis along which to compute the MAD (Default value = 0)
    scale : float
        Multiplier to use for std dev (Default value = 1.4826)

    """
    stack_abs = np.abs(stack)
    med = np.nanmedian(stack_abs, axis=axis)
    return scale * np.nanmedian(np.abs(stack_abs - med), axis=axis)


@log_runtime
def create_averages(
    search_path=".",
    ext=".unw",
    rsc_file=None,
    deramp_order=2,
    avg_file="average_ifgs.nc",
    overwrite=False,
    band=2,
    ds_name="average_ifgs",
    max_temporal_baseline=800,
    do_flip=True,
    mask=None,
    mask_files=[],
    mask_is_zero=False,
    **kwargs,
):
    """Create a NetCDF stack of "average interferograms" for each date

    Parameters
    ----------
    search_path : str
        directory to find igrams (Default value = ".")
    ext : str
        extension name of unwrapped interferograms (default = .unw)
    rsc_file : str
        filename of .rsc resource file, if loading binary files like snaphu outputs (Default value = None)
    deramp_order : int
        remove a linear (or quadratic ramp) from unwrapped igrams
        if `deramp_order` = 1 (or 2) (Default value = 2)
    avg_file : str
        name of output file to save stack (Default value = "average_ifgs.nc")
    overwrite : bool
        clobber current output file, if exists (Default value = False)
    band : int
        if using gdal to load igrams, which image band to load (Default value = 2)
    ds_name : str
        Name of the data variable used in the netcdf stack (Default value = "average_ifgs")
    do_flip : bool
        Flip the sign of interferograms to always go from (cur date, other date) (Default value = True)
    max_temporal_baseline : int
        Maximum temporal baseline to use for averaging, in days. (Default value = 800)
    mask : np.ndarray
        binary mask to apply to all loaded interferograms (Default value = None)
    mask_files : list
        List of files to use as masks for the stack. (Default value = [])
    mask_is_zero : bool
        If True, areas in the `mask_files` which are 0 are the places to ignore. (Default value = False.)
        Note that `mask_is_zero=False` means that True/1s are the mask areas (matching numpy masking defaults).

    Returns
    -------
    str: name of output file
    """
    import h5netcdf.legacyapi as nc

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
    ds = f[ds_name]
    _, rows, cols = ds.shape

    # Get masks for deramping
    # mask_igram_date_list = utils.load_intlist_from_h5(mask_fname)
    if mask is None:
        mask = np.zeros((rows, cols)).astype(bool)
    if mask_files:
        mask = np.logical_or(mask, sario.load_mask(mask_files, mask_is_zero=mask_is_zero))

    for (idx, cur_date) in enumerate(sar_date_list):
        cur_unws = [
            (fname, date_pair)
            for (date_pair, fname) in zip(ifg_date_list, unw_file_list)
            if (
                cur_date in date_pair
                and _temp_baseline(date_pair) <= max_temporal_baseline
            )
        ]
        log.info(
            "Averaging {} igrams for {} ({} out of {})".format(
                len(cur_unws), cur_date, idx + 1, len(sar_date_list)
            )
        )

        # reset the matrix to all zeros
        out = 0
        for unwf, date_pair in cur_unws:
            # Since each ifg of (date1, date2) was made by phase2 - phase1,
            # flip ifg phase so that it's always positive: (other date, cur_date)
            # otherwise the date's phase was negative in the interferogram
            flip = -1 if do_flip and (cur_date == date_pair[0]) else 1
            img = sario.load(unwf, rsc_file=rsc_file, band=band)
            out += flip * img

            # mask_idx = mask_igram_date_list.index(date_pair)
            # mask |= mask_stack[mask_idx]

        out /= len(cur_unws)

        if deramp_order > 0:
            out = remove_ramp(out, deramp_order=deramp_order, mask=mask)
        else:
            out -= np.nanmean(out)
            out[mask] = np.nan

        # Write the single layer out
        ds[idx, :, :] = out

    # Close to save it
    f.close()
    return avg_file


def _temp_baseline(date_pair):
    """Calculate the temporal baseline of a date pair"""
    return abs(date_pair[1] - date_pair[0]).days
