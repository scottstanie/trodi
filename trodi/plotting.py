import numpy as np


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
    )
