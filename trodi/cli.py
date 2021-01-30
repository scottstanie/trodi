import argparse
from . import average_igrams


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
        "--outfile",
        "-o",
        default="labels.nc",
        help="Location to save final labels (default=%(default)s)",
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
    avg_slc_file = average_igrams.create_averages(**arg_dict)
    average_igrams.label_outliers(fname=avg_slc_file, outfile=args.outfile)
    # args.deramp,
    # args.ext,
    # search_path=args.search_path,
    # overwrite=args.overwrite,
    # )


def main():
    create_labels()
