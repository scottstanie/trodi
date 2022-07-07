import collections
from multiprocessing.sharedctypes import Value

import numpy as np

FLOAT_32_LE = np.dtype("<f4")
RSC_KEY_TYPES = [
    ("width", int),
    ("file_length", int),
    ("x_first", float),
    ("y_first", float),
    ("x_step", float),
    ("y_step", float),
    ("x_unit", str),
    ("y_unit", str),
    ("z_offset", int),
    ("z_scale", int),
    ("projection", str),
]


def load(
    filename,
    rsc_file=None,
    rows=None,
    cols=None,
    band=1,
    mask_nodata=True,
    **kwargs,
):
    """Load a file, either using numpy or rasterio

    Parameters
    ----------
    filename : str
        Name of file to load
    rsc_file : int
         (Default value = None)
    rows : int
        Manually specify number of rows of image
    cols :
        Manually specify number of cols of image
    band : int
        For gdal, specify the band of the image to load (Default value = 1)
    mask_nodata : bool
        If True, convert out gdal-indicated nodata values as nans (Default value = True)
    **kwargs :
        

    Returns
    -------
    ndarray : image data
    """
    if rsc_file:
        rsc_data = load_rsc(rsc_file)
        return load_stacked_img(filename, rsc_data=rsc_data, rows=rows, cols=cols)
    else:
        try:
            from osgeo import gdal
            gdal.UseExceptions()
        except ImportError:
            raise ValueError("Need to `conda install gdal` to load gdal-readable")

        ds = gdal.Open(filename)
        image = ds.GetRasterBand(band).ReadAsArray()
        # Get the nodata value, and set it to nan
        nodata = ds.GetRasterBand(band).GetNoDataValue()
        if nodata is not None:
            try:
                image[image == nodata] = np.nan
            except ValueError:  # non-float image type, dont mask
                pass
        ds = None
        return image


def load_rsc(filename, lower=False, **kwargs):
    """Loads and parses the .rsc file

    Parameters
    ----------
    lower : bool
        make keys of the dict lowercase (Default value = False)
    filename :
        
    **kwargs :
        

    Returns
    -------
    dict
        .rsc file parsed out
        example file:
        WIDTH         10801
        FILE_LENGTH   7201
        X_FIRST       -157.0
        Y_FIRST       21.0
        X_STEP        0.000277777777
        Y_STEP        -0.000277777777
        X_UNIT        degrees
        Y_UNIT        degrees
        Z_OFFSET      0
        Z_SCALE       1
        PROJECTION    LL

    """

    # Use OrderedDict so that upsample_dem_rsc creates with same ordering as old
    output_data = collections.OrderedDict()
    # Second part in tuple is used to cast string to correct type

    with open(filename, "r") as f:
        for line in f.readlines():
            for field, num_type in RSC_KEY_TYPES:
                if line.startswith(field.upper()):
                    output_data[field] = num_type(line.split()[1])

    if lower:
        output_data = {k.lower(): d for k, d in output_data.items()}
    return output_data


def load_stacked_img(
    filename,
    rows=None,
    cols=None,
    rsc_data=None,
    return_amp=False,
    dtype=FLOAT_32_LE,
    **kwargs,
):
    """Helper function to load .unw and .cor files from snaphu output
    
    Format is two stacked matrices:
        [[first], [second]] where the first "cols" number of floats
        are the first matrix, next "cols" are second, etc.
    Also called BIL, Band Interleaved by Line
    See http://webhelp.esri.com/arcgisdesktop/9.3/index.cfm?topicname=BIL,_BIP,_and_BSQ_raster_files
    for explantion
    
    For .unw height files, the first is amplitude, second is phase (unwrapped)
    For .cc correlation files, first is amp, second is correlation (0 to 1)

    Parameters
    ----------
    filename :
        str
    rows :
        int (Default value = None)
    cols :
        int (Default value = None)
    rsc_data :
        dict (Default value = None)
    return_amp :
        bool (Default value = False)
    dtype :
         (Default value = FLOAT_32_LE)
    **kwargs :
        

    Returns
    -------
    type
        ndarray: dtype=float32, the second matrix (height, correlation, ...) parsed
        if return_amp == True, returns two ndarrays stacked along axis=0

    """
    if rows is None or cols is None:
        rows, cols = rsc_data["file_length"], rsc_data["width"]

    data = np.fromfile(filename, dtype)

    first = data.reshape((rows, 2 * cols))[:, :cols]
    second = data.reshape((rows, 2 * cols))[:, cols:]
    if return_amp:
        return np.stack((first, second), axis=0)
    else:
        return second


def load_mask(mask_files, rsc_file=None, mask_is_zero=False):
    """Create one mask from a list of mask files

    Parameters
    ----------
    mask_files :
        
    rsc_file :
         (Default value = None)

    Returns
    -------
    ndarray
        dtype=bool, the mask

    """
    mask = np.ma.nomask
    for mask_file in mask_files:
        cur_mask = load(mask_file, band=1, rsc_file=rsc_file).astype(np.bool)
        if mask_is_zero:
            cur_mask = ~cur_mask
        mask = np.logical_or(mask, cur_mask)
    return mask
