#!/usr/bin/env python
"""
Averages all unwrapped igrams, making images of the averge phase per date
"""
# import h5py
import numpy as np
import argparse

from scipy.stats import median_abs_deviation

from . import utils
from . import sario
from .logger import get_log, log_runtime
from .deramp import remove_ramp

log = get_log()
"""
# TODO: once averaged... just need to label the idxs which are more than n-sigma above the median
means = mean_abs_val(geo, int, val)
out_idxs = two_way_outliers(means, nsigma, min_spread)

mednsigma(arr, n = 4) = n * mad(arr, normalize = true)

    function two_way_cutoff(arr, nsigma, min_spread = 0)
    # min_spread = abs(2 * median(arr))
    # spread = 1.5 * iqr(arr)
    spread = max(min_spread, mednsigma(arr, nsigma))
    #@show spread
    # spread = max(min_spread, std(arr)*nsigma)
    #@show std(arr)*nsigma

    # Make we dont cut off very low var points
    low = min(0, median(arr) - spread)
    high = median(arr) + spread
    return (low, high)
end
"""


def mad(stack, axis=0):
    return median_abs_deviation(stack, scale=1 / 1.4826, nan_policy="omit", axis=axis)


def label_outliers(stack, nsigma=4, axis=0):
    threshold_img = nsigma * mad(np.abs(stack))
    return stack > threshold_img


@log_runtime
def create_averages(
    deramp,
    ext,
    search_path=".",
    rsc_file=None,
    overwrite=False,
    normalize_time=False,
    band=2,
    outfile="average_slcs.nc",
    ds_name="igrams",
    **kwargs,
):

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


def plot_avgs(fname="average_slcs.nc", stack=None, cmap=None, nimg=9):
    import xarray as xr

    # import matplotlib.pyplot as plt
    if stack is None:
        with xr.open_dataarray(fname) as ds:
            stack = ds[:nimg]
    else:
        stack = stack[:nimg]

    # vmin, vmax = np.nanmin(avgs), np.nanmax(avgs)
    # vm = np.max(np.abs([vmin, vmax]))
    ntotal = stack.shape[0]
    ntiles = nimg if nimg < ntotal else ntotal

    nside = int(np.ceil(np.sqrt(ntiles)))
    stack.plot(
        x="lon",
        y="lat",
        col="date",
        col_wrap=nside,
        cmap=cmap,
        # vmax=np.percentile(ds.data, 95),
        # cmap="gray",
        #     cmap="discrete_seismic7",
    )
    # fig, axes = plt.subplots(nside, nside)
    # for (avg, ax, fn) in zip(avgs, axes.ravel(), fnames):
    # axim = ax.imshow(avg, vmin=-vm, vmax=vm, cmap=cmap)
    # ax.set_title(f"{fn}: {np.var(avg):.2f}")
    # fig.colorbar(axim, ax=ax)
    # return fig, axes


def get_cli_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--deramp",
        action="store_true",
        default=True,
        help="remove a linear ramp from phase after averaging (default=%(default)s)",
    )
    p.add_argument(
        "--ext",
        default=".unw",
        help="filename extension of unwrapped igrams to average (default=%(default)s)",
    )
    p.add_argument(
        "--search-path",
        "-p",
        default=".",
        help="location of igram files. (default=%(default)s)",
    )
    p.add_argument(
        "--rsc-file", help="If using ROI_PAC .rsc files, location of .rsc file"
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing averaged files (default=%(default)s)",
    )
    p.add_argument(
        "--normalize-time",
        "-n",
        action="store_true",
        default=False,
        help="Divide igram phase by temporal baseline (default=%(default)s)",
    )
    return p.parse_args()


def run_create_averages():
    args = get_cli_args()
    create_averages(**vars(args))
    # args.deramp,
    # args.ext,
    # search_path=args.search_path,
    # overwrite=args.overwrite,
    # )
