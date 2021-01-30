import argparse
from . import core


description = """
'--level pixel' means individual pixels for each SAR date are labeled (good for larger scenes).
'--level scene' means whole SAR images are labeled (good for smaller scenes).
For scene level labeling, the variance of each average interferogram is used.

"""


def get_cli_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--level",
        default="pixel",
        choices=["pixel", "scene"],
        help=("Level at which to label outliers. (default=%(default)s).\n"),
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
        "--outfile",
        "-o",
        default="labels.nc",
        help="Location to save final labels (default=%(default)s)",
    )
    p.add_argument(
        "--deramp",
        action="store_true",
        default=True,
        help="remove a linear ramp from phase after averaging (default=%(default)s)",
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


def create_labels():
    args = get_cli_args()
    arg_dict = vars(args)
    arg_dict["outfile"] = "average_slcs.nc"
    avg_slc_file = core.create_averages(**arg_dict)
    core.label_outliers(fname=avg_slc_file, outfile=args.outfile)
    # args.deramp,
    # args.ext,
    # search_path=args.search_path,
    # overwrite=args.overwrite,
    # )


def main():
    create_labels()
