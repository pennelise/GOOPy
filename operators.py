import os
import yaml
import numpy as np
import xarray as xr
from interpolation import VerticalGrid
import utilities as util
import parsers


with open("config.yaml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)

def apply_averaging_kernel(model_on_satellite_levels, satellite):
    model_column = np.sum(satellite["PRESSURE_WEIGHT"]
                          * (satellite["PRIOR_PROFILE"] 
                             + satellite["AVERAGING_KERNEL"]
                             * (model_on_satellite_levels 
                                - satellite["PRIOR_PROFILE"])),
                                axis=1)
    return  model_column

def get_model_columns(model, satellite, satellite_name):
    """
    generic function to apply an operator to a satellite
    takes:
        - GEOS-Chem dataframe (not a problem b/c this is standard)
        - all required satellite inputs as np arrays
    """
    # Get the spatial and temporal indices linking each satellite observation
    # back to the model grid and apply them to the model data
    model = util.colocate_obs(model, satellite)

    # Create an instance of the VerticalGrid class and interpolate the model
    # onto satellite levels
    model_on_satellite_levels = VerticalGrid(
        model["CONC_AT_PRESSURE_CENTERS"].values,
        model["PRESSURE_EDGES"].values,
        satellite["PRESSURE_EDGES"].values,
        config[satellite_name]["AVERAGING_KERNEL_USES_CENTERS_OR_EDGES"])
    model_on_satellite_levels = model_on_satellite_levels.interpolate()

    # Apply the averaging kernel
    model_columns = apply_averaging_kernel(
        model_on_satellite_levels, satellite)
    
    return model_columns


def regrid_gc_to_sat_pixels(sat_lat, sat_lon, gc_lat, gc_lon):
    pass
    # calculate pixels which overlap each satellite observation
    # this is what the IMI does
    # assumes model pixel size is close to satellite pixel size
