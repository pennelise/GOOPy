import os
import numpy as np
import xarray as xr
from interpolation import VerticalGrid
import utilities as util

def apply_averaging_kernel(model_on_satellite_levels, satellite):
    model_column = np.sum(satellite["PRESSURE_WEIGHT"].values[:, :, None]
                          * (satellite["PRIOR_PROFILE"].values[:, :, None] 
                             + satellite["AVERAGING_KERNEL"].values[:, :, None]
                             * (model_on_satellite_levels 
                                - satellite["PRIOR_PROFILE"].values[:, :, None])),
                                axis=1)
    return  model_column


def get_model_columns(model, satellite, config, save_dir):
    """
    generic function to apply an operator to a satellite
    takes:
        - GEOS-Chem dataframe (not a problem b/c this is standard)
        - all required satellite inputs as np arrays
    """
    satellite_name = config["LOCAL_SETTINGS"]["SATELLITE_NAME"]
    avker_center_or_edges = config[satellite_name][
        "AVERAGING_KERNEL_USES_CENTERS_OR_EDGES"
    ]
    save_interpolation = config["LOCAL_SETTINGS"]["SAVE_INTERPOLATION"]

    # Get the spatial and temporal indices linking each satellite observation
    # back to the model grid and apply them to the model data
    if save_interpolation:
        model = util.colocate_obs(model, satellite, save_dir)
    else:
        model = util.colocate_obs(model, satellite)

    # Create an instance of the VerticalGrid class and interpolate the model
    # onto satellite levels
    conc_vars = [
        v for v in model.variables 
        if v[:len("CONC_AT_PRESSURE_CENTERS")] == "CONC_AT_PRESSURE_CENTERS"]
    # all_model_columns = xr.Dataset(coords={"N_OBS" : satellite["N_OBS"]})
    model_on_satellite_levels = VerticalGrid(
        np.stack([model[v].values for v in conc_vars], axis=-1),
        model["PRESSURE_EDGES"].values,
        satellite["PRESSURE_EDGES"].values,
        avker_center_or_edges,
        save_interpolation,
        save_dir)
    model_on_satellite_levels = model_on_satellite_levels.interpolate()

    # Apply the averaging kernel
    model_columns = apply_averaging_kernel(model_on_satellite_levels, satellite)
    model_columns = xr.Dataset(
        {v: (['N_OBS'], model_columns[:, i]) for i, v in enumerate(conc_vars)},
        coords={'N_OBS': satellite["N_OBS"]})
    return model_columns


def regrid_gc_to_sat_pixels(sat_lat, sat_lon, gc_lat, gc_lon):
    pass
    # calculate pixels which overlap each satellite observation
    # this is what the IMI does
    # assumes model pixel size is close to satellite pixel size
