import argparse

from . import core

description = """
'--level pixel' means individual pixels for each SAR date are labeled (good for larger scenes).
'--level scene' means whole SAR images are labeled (good for smaller scenes).
For scene level labeling, the variance of each average interferogram is used.
"""


def get_cli_args():
    """ """
    p = argparse.ArgumentParser(description=description)
    p.add_argument(
        "--input-files",
        "-i",
        help=(
            "Provide the list of input interferogram filenames in a text file."
            "Alternate to `--search-path`."
        ),
    )
    p.add_argument(
        "--search-path",
        "-p",
        default=".",
        help="location of igram files. (default=%(default)s)",
    )
    p.add_argument(
        "--ext",
        default=".unw",
        help="filename extension of unwrapped igrams to average (default=%(default)s)",
    )
    p.add_argument(
        "--band",
        type=int,
        default=1,
        help="If using GDAL to load igrams, specify which band represents unwrapped phase (default=%(default)s)",
    )
    p.add_argument(
        "--outfile",
        "-o",
        default="labels.nc",
        help="Location to save final labels (default=%(default)s)",
    )
    p.add_argument(
        "--level",
        default="scene",
        choices=["pixel", "scene"],
        help=("Level at which to label outliers. (default=%(default)s).\n"),
    )
    p.add_argument(
        "--avg-file",
        default="average_ifgs.nc",
        help="Location to save stack of averaged igrams (default=%(default)s)",
    )
    p.add_argument(
        "--deramp-order",
        default=2,
        type=int,
        help="Specify order of surface to remove from phase when averaging. "
        " 1 = linear ramp, 2 = quadratic surface, 0 = no ramp adjustment (default=%(default)s)",
    )
    p.add_argument(
        "--nsigma",
        "-n",
        type=int,
        help=(
            "Number of sigma_mad deviations away from median to label as outlier"
            " (default=%(default)s)"
        ),
        default=5,
    )
    p.add_argument(
        "--rsc-file", help="If using ROI_PAC .rsc files, location of .rsc file"
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing averaged files (default=%(default)s)",
    )
    p.add_argument(
        "--max-temporal-baseline",
        type=int,
        help=(
            "Maximum temporal baseline to use when averaging interferograms. (default=%(default)s)"
        ),
        default=400,
    )
    p.add_argument(
        "--mask-files",
        nargs="+",
        help="List of binary mask files (e.g. water mask) to apply when creating average interferograms.",
    )
    p.add_argument(
        "--mask-is-zero",
        action="store_true",
        help=(
            "Indicate that the areas to mask are 0 in the files given by `--mask-files`. "
            "The default is the numpy convention where True (1) is masked."
        ),
    )
    p.add_argument(
        "--no-data",
        type=int,
        help="Indicate a nodata value to mask in all interferograms (default=%(default)s)",
    )
    p.add_argument(
        "--no-sign-flip",
        action="store_false",
        dest="do_flip",
        help="Skip the sign-flipping that makes interferogram averages have same direction."
        " Skipping for interferograms will make averages including long term deformation, "
        "but is useful for, e.g., averaging correlation images.",
    )
    return p.parse_args()


def average_and_label():
    """ """
    args = get_cli_args()
    core.create_averages(**vars(args))
    core.label_outliers(
        fname=args.avg_file,
        outfile=args.outfile,
        nsigma=args.nsigma,
        level=args.level,
    )
