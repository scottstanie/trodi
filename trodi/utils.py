import os
import datetime

from glob import glob

DATE_FMT = "%Y%m%d"


def find_igrams(directory=".", ext=".int", parse=True, filename=None):
    """Reads the list of igrams to return dates of images as a tuple

    Args:
        directory (str): path to the igram directory
        ext (str): file extension when searching a directory
        parse (bool): output as parsed datetime tuples. False returns the filenames
        filename (str): name of a file with .geo filenames

    Returns:
        tuple(date, date) of (early, late) dates for all igrams (if parse=True)
            if parse=False: returns list[str], filenames of the igrams

    """
    if filename is not None:
        with open(filename) as f:
            igram_file_list = [
                line
                for line in f.read().splitlines()
                if not line.strip().startswith("#")
            ]
    else:
        igram_file_list = sorted(glob(os.path.join(directory, "*" + ext)))

    if parse:
        igram_fnames = [os.path.split(f)[1] for f in igram_file_list]
        date_pairs = [intname.strip(ext).split("_")[:2] for intname in igram_fnames]
        return parse_intlist_strings(date_pairs, ext=ext)
    else:
        return igram_file_list


def parse_intlist_strings(date_pairs, ext=".int"):
    # If we passed filename YYYYmmdd_YYYYmmdd.int
    if isinstance(date_pairs, str):
        # TODO: isn't this better than stripping 'ext'?
        date_pairs = [date_pairs.split(".")[0].split("_")[:2]]
    elif isinstance(date_pairs, Iterable) and isinstance(date_pairs[0], str):
        date_pairs = [f.split(".")[0].split("_")[:2] for f in date_pairs]

    return [(_parse(early), _parse(late)) for early, late in date_pairs]


def _parse(datestr):
    return datetime.datetime.strptime(datestr, DATE_FMT).date()


def ignore_geo_dates(
    geo_date_list, int_date_list, ignore_file="geolist_ignore.txt", parse=True
):
    """Read extra file to ignore certain dates of interferograms"""
    ignore_geos = set(find_geos(filename=ignore_file, parse=parse))
    logger.info("Ignoring the following .geo dates:")
    logger.info(sorted(ignore_geos))
    valid_geos = [g for g in geo_date_list if g not in ignore_geos]
    valid_igrams = [
        i for i in int_date_list if i[0] not in ignore_geos and i[1] not in ignore_geos
    ]
    return valid_geos, valid_igrams