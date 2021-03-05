# trodi

Label outliers on a stack of interferograms, either at the pixel level, or SAR-scene level.


## Usage


```
$ trodi --outfile labels_scene.nc --level scene
[03/04 22:37:15] [INFO core.py] Searching for igrams in igrams/ with extention .unw
[03/04 22:37:15] [INFO core.py] Found 9 igrams, 5 unique SAR dates
[03/04 22:37:15] [INFO utils.py] Making dimensions and variables
[03/04 22:37:15] [INFO utils.py] Writing dummy data for igrams
[03/04 22:37:15] [INFO core.py] Averaging 4 igrams for 2015-02-08 (1 out of 5)
[03/04 22:37:15] [INFO core.py] Averaging 4 igrams for 2015-03-28 (2 out of 5)
[03/04 22:37:15] [INFO core.py] Averaging 3 igrams for 2015-04-09 (3 out of 5)
[03/04 22:37:15] [INFO core.py] Averaging 3 igrams for 2015-05-27 (4 out of 5)
[03/04 22:37:15] [INFO core.py] Averaging 4 igrams for 2015-06-20 (5 out of 5)
[03/04 22:37:16] [INFO logger.py] Total elapsed time for create_averages : 0.02 minutes (1.26 seconds)
[03/04 22:37:17] [INFO core.py] Computing 5 sigma outlier labels at scene level.
[03/04 22:37:17] [INFO core.py] Saving outlier labels to labels_scene.nc:/labels
[03/04 22:37:17] [INFO core.py] Saving data to labels_scene.nc:/data
[03/04 22:37:17] [INFO core.py] Saving threshold to labels_scene.nc:/threshold
```


With the outliers recorded, we can read these in Python with xarray, (or h5py, or a NetCDF reader):

```python
import xarray as xr
>>> ds = xr.open_dataset("labels_scene.nc")
>>> ds
<xarray.Dataset>
Dimensions:    (date: 5)
Coordinates:
  * date       (date) datetime64[ns] 2015-02-08 2015-03-28 ... 2015-06-20
Data variables:
    labels     (date) bool ...
    data       (date) float32 ...
    threshold  float32 ...

>>> print(ds['labels'])
<xarray.DataArray 'labels' (date: 5)>
array([False, False, False, False,  True])
Coordinates:
  * date     (date) datetime64[ns] 2015-02-08 2015-03-28 ... 2015-06-20
```

The `labels` dataset gives a `True` for any SAR dates determined to be an outlier.

In MATLAB, reading the results would use `ncread`:

```matlab
>> ncread('labels_scene.nc', 'labels')
ans =
  5×1 int8 column vector
   0
   0
   0
   0
   1

>> ncread('labels_scene.nc', 'threshold')
ans =
    0.8059
```
We see that for this dummy example, the threshold was 0.8059 on the average interferograms.

#### Full options:

```
$ trodi --help
usage: trodi [-h] [--level {pixel,scene}] [--ext EXT] [--search-path SEARCH_PATH] [--outfile OUTFILE] [--avg-file AVG_FILE] [--deramp] [--nsigma NSIGMA] [--rsc-file RSC_FILE]
             [--overwrite] [--normalize-time]

'--level pixel' means individual pixels for each SAR date are labeled (good for larger scenes). '--level scene' means whole SAR images are labeled (good for smaller scenes).
For scene level labeling, the variance of each average interferogram is used.

optional arguments:
  -h, --help            show this help message and exit
  --level {pixel,scene}
                        Level at which to label outliers. (default=pixel).
  --ext EXT             filename extension of unwrapped igrams to average (default=.unw)
  --search-path SEARCH_PATH, -p SEARCH_PATH
                        location of igram files. (default=.)
  --outfile OUTFILE, -o OUTFILE
                        Location to save final labels (default=labels.nc)
  --avg-file AVG_FILE   Location to save stack of averaged igrams (default=average_slcs.nc)
  --deramp              remove a linear ramp from phase after averaging (default=True)
  --nsigma NSIGMA, -n NSIGMA
                        Number of sigma_mad deviations away from median to label as outlier (default=5)
  --rsc-file RSC_FILE   If using ROI_PAC .rsc files, location of .rsc file
  --overwrite           Overwrite existing averaged files (default=False)
  --normalize-time      Divide igram phase by temporal baseline (default=False)
  ```