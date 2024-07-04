import os
import yaml
import numpy as np
import xarray as xr
import utilities as util
import parsers
import operators
import sys

def apply_operator_to_chunks(model_conc_files,
                             model_edge_files,
                             satellite, 
                             config):
    # We iterate through this in chunks of
    # file_length_threshold to balance memory constraints with the
    # benefits of vectorization.
    i = 0
    model_columns = []
    satellite_columns = []
    while i < satellite.dims["N_OBS"]:
        # Subset the satellite data
        sat_i = satellite.isel(
            N_OBS=slice(
                int(i), 
                int(i + config["LOCAL_SETTINGS"]["FILE_LENGTH_THRESHOLD"])
            )
        )
    
        # Get the dates that need to be processed
        process_dates = np.unique(sat_i["TIME"].dt.strftime("%Y-%m-%d"))

        # Load the model data for those dates
        mod_i = parsers.read_geoschem_file(
            util.get_gc_files_for_dates(model_conc_files, process_dates),
            util.get_gc_files_for_dates(model_edge_files, process_dates),
            config["MODEL"]["DATA_FIELDS"])

        # Check for times that are missing in the satellite data and continue
        # if there are no overlapping itmes
        missing_times = util.get_missing_times(sat_i["TIME"], mod_i["TIME"])
        if (~missing_times).sum() == 0:
            print("  There are no overlapping satellite and model data in"
                  " this chunk.")
            i += config["LOCAL_SETTINGS"]["FILE_LENGTH_THRESHOLD"]
            continue

        # Run the column operator
        model_columns.append(
            operators.get_model_columns(
                mod_i, sat_i.where(~missing_times, drop=True), 
                config["LOCAL_SETTINGS"]["PARSER"]))
        if config["LOCAL_SETTINGS"]["SAVE_SATELLITE_DATA"].lower() == "true":
            satellite_columns.append(
                sat_i.drop(['PRESSURE_EDGES', 'PRESSURE_WEIGHT',
                            'AVERAGING_KERNEL', 'PRIOR_PROFILE', 'N_EDGES']))

        # Step up i
        i += config["LOCAL_SETTINGS"]["FILE_LENGTH_THRESHOLD"]

    # Concatenate together, combine, and return
    if len(model_columns) > 0:
        model_columns = xr.concat(model_columns, dim="N_OBS")
        model_columns = model_columns.rename("MODEL_COLUMN")
        if config["LOCAL_SETTINGS"]["SAVE_SATELLITE_DATA"].lower() == "true":
            satellite_columns = xr.concat(satellite_columns, dim="N_OBS")
            model_columns = xr.merge([model_columns, satellite_columns])
        return model_columns
    else:
        return None


def apply_operator(config):#satellite_name, file_length_threshold=1e6):
    """apply one of the default operators to a satellite"""

    # Make save out directory
    if not os.path.exists(config["LOCAL_SETTINGS"]["SAVE_DIR"]):
        os.makedirs(config["LOCAL_SETTINGS"]["SAVE_DIR"])

    # Obtain a list of the satellite and GEOS-Chem files.
    files = util.get_file_lists(config["LOCAL_SETTINGS"])
    satellite_files, model_edge_files, model_conc_files = files

    # Get the dates for which we have model files.
    # TO DO: Currently, this assumes that the GEOS-Chem files are daily or
    # monthly. We should update this to be more flexible.
    model_dates = np.unique(
        [date for date in util.get_gc_dates(model_edge_files)
         if date in util.get_gc_dates(model_conc_files)])

    # Get the satellite parser. 
    read_satellite = util.get_satellite_parser(config)

    # Iterate through the satellite files:
    for sf in satellite_files:
        short_name = sf.split("/")[-1]

        # Read the first file
        print(f"Processing {short_name}")
        satellite = read_satellite(sf)

        # Get unique dates from the file that overlap with the model dates
        # and subset for those dates.
        satellite_dates = [
            date for date 
            in np.unique(satellite["TIME"].dt.strftime("%Y-%m-%d"))
            if date in model_dates
        ]

        if len(satellite_dates) == 0:
            print(f"  There are no temporally overlapping model "
                  f"data for {short_name}")
            continue

        satellite = satellite.where(
            satellite["TIME"].dt.strftime("%Y-%m-%d").isin(satellite_dates), 
            drop=True)

        # Next, apply the operator
        model_columns = apply_operator_to_chunks(
            model_conc_files, model_edge_files, satellite, config)
        
        # Save
        if model_columns is not None:
            short_name = short_name.split('.')[0] + '_operator.nc'
            model_columns.to_netcdf(
                f'{config["LOCAL_SETTINGS"]["SAVE_DIR"]}/{short_name}')
    

if __name__ == "__main__":
    # Import the name of the config file and the name of the satellite
    # name
    import sys
    config_str = sys.argv[1]

    # Load the config file
    with open(config_str, "r", encoding="utf8") as f:
        config = yaml.safe_load(f)

    # Run the operator
    apply_operator(config)