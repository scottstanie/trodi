import datetime
import itertools
import os
import time
from collections.abc import Iterable
from glob import glob

import cftime
import h5netcdf.legacyapi as nc
import numpy as np

from . import sario
from .logger import get_log

log = get_log()
DATE_FMT = "%Y%m%d"


def find_igrams(directory=".", ext=".int", parse=True, filename=None):
    """Reads the list of igrams to return dates of images as a tuple

    Parameters
    ----------
    directory : str
        path to the igram directory (Default value = ".")
    ext : str
        file extension when searching a directory (Default value = ".int")
    parse : bool
        output as parsed datetime tuples. False returns the filenames (Default value = True)
    filename : str
        name of a file with SAR filenames separated by newlines (Default value = None)

    Returns
    -------
    
    list: list of tuples of datetime objects
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
        return _parse_intlist_strings(date_pairs, ext=ext)
    else:
        return igram_file_list


def _parse_intlist_strings(date_pairs, ext=".int"):
    # If we passed filename YYYYmmdd_YYYYmmdd.int
    if not date_pairs:
        return []
    if isinstance(date_pairs, str):
        date_pairs = [date_pairs.split(".")[0].split("_")[:2]]
    elif isinstance(date_pairs, Iterable) and isinstance(date_pairs[0], str):
        date_pairs = [f.split(".")[0].split("_")[:2] for f in date_pairs]

    return [(_parse(early), _parse(late)) for early, late in date_pairs]


def dates_from_igrams(igram_list):
    """Takes a list of [(reference, secondary),...] igram date pairs
    and returns the list of unique dates of SAR images used to form them

    Parameters
    ----------
    igram_list :
        

    Returns
    -------

    """
    return sorted(list(set(itertools.chain(*igram_list))))


def _parse(datestr):
    """

    Parameters
    ----------
    datestr :
        

    Returns
    -------

    """
    return datetime.datetime.strptime(datestr, DATE_FMT).date()


def get_latlon_arrs(h5_filename=None, rsc_file=None, gdal_file=None):
    """

    Parameters
    ----------
    h5_filename :
         (Default value = None)
    rsc_file :
         (Default value = None)
    gdal_file :
         (Default value = None)

    Returns
    -------

    """
    if rsc_file is not None:
        lon_arr, lat_arr = grid(**sario.load_rsc(rsc_file), sparse=True)
    elif gdal_file is not None:
        lon_arr, lat_arr = grid(fname=gdal_file)

    lon_arr, lat_arr = lon_arr.reshape(-1), lat_arr.reshape(-1)
    return lon_arr, lat_arr


def grid(
    rows=None,
    cols=None,
    y_step=None,
    x_step=None,
    y_first=None,
    x_first=None,
    width=None,
    file_length=None,
    sparse=True,
    fname=None,
    **kwargs,
):
    """Takes sizes and spacing info, creates a grid of values

    Parameters
    ----------
    rows : int
        number of rows (Default value = None)
    cols : int
        number of cols (Default value = None)
    y_step : float
        spacing between rows (Default value = None)
    x_step : float
        spacing between cols (Default value = None)
    y_first : float
        starting location of first row at top (Default value = None)
    x_first : float
        starting location of first col on left (Default value = None)
    sparse : bool
        Optional (default False). Passed through to
        np.meshgrid to optionally conserve memory
    width :
         (Default value = None)
    file_length :
         (Default value = None)
    fname :
         (Default value = None)
    **kwargs :
        

    Returns
    -------
    tuple[ndarray, ndarray]
        the XX, YY grids of longitudes and lats

    Examples
    --------

    >>> test_grid_data = {'cols': 2, 'rows': 3, 'x_first': -155.0, 'x_step': 0.01,\
    'y_first': 19.5, 'y_step': -0.2}
    >>> np.set_printoptions(legacy="1.13")
    >>> lons, lats = grid(**test_grid_data, sparse=False)
    >>> print(lons)
    [[-155.   -154.99]
     [-155.   -154.99]
     [-155.   -154.99]]
    >>> lons, lats = grid(**test_grid_data)
    >>> print(lats)
    [[ 19.5]
     [ 19.3]
     [ 19.1]]
    """
    if fname is None:
        rows = rows or file_length
        cols = cols or width
        x = np.linspace(x_first, x_first + (cols - 1) * x_step, cols).reshape((1, cols))
        y = np.linspace(y_first, y_first + (rows - 1) * y_step, rows).reshape((rows, 1))
    else:
        try:
            from osgeo import gdal
        except ImportError:
            raise ValueError(
                "Need to `conda install gdal` to pass gdal-readable files to `grid`"
            )

        # get size of the raster
        ds = gdal.Open(fname)
        cols = ds.RasterXSize
        rows = ds.RasterYSize
        ulx, xres, _, uly, _, yres  = ds.GetGeoTransform()
        ds = None

        # lon_list, lat_list = src.xy(np.arange(max_len), np.arange(max_len))
        x = ulx + np.arange(cols) * xres
        y = uly + np.arange(rows) * yres

    return np.meshgrid(x, y, sparse=sparse)


def create_empty_nc_stack(
    outname,
    date_list=None,
    rsc_file=None,
    gdal_file=None,
    dtype="float32",
    stack_dim_name="date",
    stack_data_name="average_ifgs",
    lat_units="degrees north",
    lon_units="degrees east",
    overwrite=False,
):
    """Creates skeleton of .nc stack without writing stack data

    Parameters
    ----------
    outname : str
        name of .nc output file to save
    date_list : list[datetime.date]
        if layers of stack correspond to dates of SAR images (Default value = None)
    rsc_file : str
        .rsc (resource) file containing the desired output lat/lon grid data (Default value = None)
    gdal_file : str
        instead of .rsc, and example GDAL-readable file in desired coordinates (Default value = None)
    dtype :
        default="float32", the numpy datatype of the stack data
    stack_dim_name : str
        default = "date". Name of the 3rd dimension of the stack
        (Dimensions are (stack_dim_name, lat, lon) )
    stack_data_name : str
        default="stack", name of the data variable in the file
    lat_units : str
        default = "degrees north",
    lon_units : str
        default = "degrees east",
    overwrite : bool
        default = False, will overwrite file if true

    Returns
    -------

    """
    if not outname.endswith(".nc"):
        raise ValueError("{} must be an .nc filename".format(outname))

    # TODO: allow for radar coordinates and just "x, y" generic?
    lon_arr, lat_arr = get_latlon_arrs(
        rsc_file=rsc_file,
        gdal_file=gdal_file,
    )

    rows, cols = len(lat_arr), len(lon_arr)
    depth = len(date_list)

    if date_list is None:
        raise ValueError("Need 'date_list' if 3rd dimension is 'date'")
    stack_dim_arr = to_datetimes(date_list)

    log.info("Making dimensions and variables")
    mode = "w" if overwrite else "x"
    with nc.Dataset(outname, mode) as f:
        f.history = "Created " + time.ctime(time.time())

        f.createDimension("lat", rows)
        f.createDimension("lon", cols)
        # Could make this unlimited to add to it later?
        latitudes = f.createVariable("lat", "f4", ("lat",), zlib=True)
        longitudes = f.createVariable("lon", "f4", ("lon",), zlib=True)
        latitudes.units = lat_units
        longitudes.units = lon_units

        f.createDimension(stack_dim_name, depth)
        stack_dim_variable = f.createVariable(
            stack_dim_name, "f4", (stack_dim_name,), zlib=True
        )
        stack_dim_variable.units = "days since {}".format(date_list[0])

        # Write data
        latitudes[:] = lat_arr
        longitudes[:] = lon_arr
        d2n = cftime.date2num(stack_dim_arr, units=stack_dim_variable.units)
        stack_dim_variable[:] = d2n

        # Finally, the actual stack
        # stackvar = rootgrp.createVariable("stack/1", "f4", ("date", "lat", "lon"))
        log.info("Writing dummy data for %s", stack_data_name)
        dt = np.dtype(dtype)
        fill_value = 0

        f.createVariable(
            stack_data_name,
            dt,
            (stack_dim_name, "lat", "lon"),
            fill_value=fill_value,
            zlib=True,
        )


def to_datetimes(date_list):
    """

    Parameters
    ----------
    date_list :
        

    Returns
    -------

    """
    return [datetime.datetime(*d.timetuple()[:6]) for d in date_list]


# def ignore_sar_dates(
#     sar_date_list, int_date_list, ignore_file="sarlist_ignore.txt", parse=True
# ):
#     """Read extra file to ignore certain dates of interferograms"""
#     ignore_sars = set(find_sars(filename=ignore_file, parse=parse))
#     log.info("Ignoring the following .sar dates:")
#     log.info(sorted(ignore_sars))
#     valid_sars = [g for g in sar_date_list if g not in ignore_sars]
#     valid_igrams = [
#         i for i in int_date_list if i[0] not in ignore_sars and i[1] not in ignore_sars
#     ]
#     return valid_sars, valid_igrams
