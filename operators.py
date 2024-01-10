import yaml
import numpy as np
import xarray as xr
from interpolation import VerticalGrid
import utilities as util
import parsers

with open("config.yaml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)


def apply_operator(satellite_name, file_length_threshold=1e6):
    """apply one of the default operators to a satellite"""

    # Obtain a list of the satellite and GEOS-Chem files.
    files = util.get_file_lists(satellite_name)
    satellite_files, model_edge_files, model_conc_files = files

    # Get the dates for which we have model files.
    # TO DO: Currently, this assumes that the GEOS-Chem files are daily or monthly
    # We should update this to be more flexible.)
    model_dates = np.unique(
        [date for date in util.get_gc_dates(model_edge_files)
         if date in util.get_gc_dates(model_conc_files)]
         )

    # Get the satellite parser. 
    read_satellite = util.get_satellite_parser(satellite_name)

    # Iterate through the satellite files:
    for sf in satellite_files:
        # Read the first file
        satellite = read_satellite(sf)

        # Get unique dates from the file that overlap with the model dates.
        satellite_dates = [date for date 
                           in np.unique(satellite["TIME"].dt.strftime("%Y%m%d"))
                           if date in model_dates]
        if len(satellite_dates) == 0:
            print(f"There are no temporally overlapping model data for {sf}")
            continue

        # Next, open the model files. We iterate through this in chunks of
        # file_length_threshold to balance memory constraints with the
        # benefits of vectorization.
        i = 0
        tick = int(satellite.dims["N_OBS"]/20)
        model_columns = []
        satellite_columns = []
        while i < satellite.dims["N_OBS"]:
            # Tick if relevant
            if i % tick == 0:
                pct_complete = 100*i/satellite.dims["N_OBS"]
                print(f'{pct_complete:.0f}%')

            # Get model columns and append to list
            model_columns.append(
                apply_operator_to_chunks(
                    model_conc_files, model_edge_files, satellite, 
                    satellite_name, i, file_length_threshold
                    )
                )

            # Step up i
            i += file_length_threshold
        
        # Concatenate together, combine, and return
        model_columns = xr.concat(model_columns, dim="N_OBS")
        satellite_columns = satellite[["SATELLITE_COLUMN", "LATITUDE", 
                                       "LONGITUDE", "TIME"]]
        satellite_columns["MODEL_COLUMN"] = model_columns
        satellite_columns.to_netcdf(config["MODEL"]["SAVE_DIR"])


def apply_operator_to_chunks(model_conc_files,
                             model_edge_files,
                             satellite, 
                             satellite_name,
                             i, file_length_threshold):
    # Subset the satellite data
    satellite_i = satellite.isel(N_OBS=slice(int(i), 
                                             int(i + file_length_threshold)))
    
    # Get the dates that need to be processed
    process_dates = np.unique(satellite_i["TIME"].dt.strftime("%Y%m%d"))

    # Load the model data for those dates
    model_i = parsers.read_geoschem_file(
        util.get_gc_files_for_dates(model_conc_files, process_dates),
        util.get_gc_files_for_dates(model_edge_files, process_dates))
    
    # Run the column operator
    model_columns_i = get_model_columns(model_i, satellite_i, 
                                        satellite_name)
    
    return model_columns_i


def get_model_columns(model, satellite, satellite_name):
    """
    generic function to apply an operator to a satellite
    takes:
        - GEOS-Chem dataframe (not a problem b/c this is standard)
        - all required satellite inputs as np arrays
    """
    # Get the spatial and temporal indices linking each satellite observation
    # back to the model grid and apply them to the model data
    lon_idx, lat_idx, time_idx = util.colocate_obs(model, satellite)
    model = model.isel(TIME=time_idx, LONGITUDE=lon_idx, LATITUDE=lat_idx)

    # Create an instance of the VerticalGrid class and interpolate the model
    # onto satellite levels
    model_on_satellite_levels = VerticalGrid(
            model["CONC_AT_PRESSURE_CENTERS"].values,
            model["PRESSURE_EDGES"].values,
            satellite["PRESSURE_EDGES"].values,
            config[satellite_name]["AVERAGING_KERNEL_USES_CENTERS_OR_EDGES"]
            )
    model_on_satellite_levels = model_on_satellite_levels.interpolate()

    # Apply the averaging kernel
    model_columns = apply_averaging_kernel(
        model_on_satellite_levels, satellite
        )
    
    return model_columns


def apply_averaging_kernel(model_on_satellite_levels, satellite):
    model_column = np.sum(satellite["PRESSURE_WEIGHT"]
                          * (satellite["PRIOR_PROFILE"] 
                             + satellite["AVERAGING_KERNEL"]
                             * (model_on_satellite_levels 
                                - satellite["PRIOR_PROFILE"])),
                                axis=1)
    return  model_column


def regrid_gc_to_sat_pixels(sat_lat, sat_lon, gc_lat, gc_lon):
    pass
    # calculate pixels which overlap each satellite observation
    # this is what the IMI does
    # assumes model pixel size is close to satellite pixel size


if __name__ == "__main__":
    import sys
    satellite_name = sys.argv[1]
    apply_operator(satellite_name)