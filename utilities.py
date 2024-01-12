
import yaml
import glob
import inspect
import numpy as np
import xarray as xr
import parsers

# Open the config file
with open("config.yaml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)


def get_file_lists(satellite_name):
    # Satellite files
    sat_fields = config[satellite_name]
    sat_files = f"{sat_fields['OBS_DIR']}/{sat_fields['FILE_NAME_FORMAT']}"
    sat_files = np.array(sorted(glob.glob(sat_files)))

    # Model fields
    mod_fields = config["MODEL"]

    ## Level edges
    model_edge_files = (f"{mod_fields['MODEL_DIR']}/"
                     f"{mod_fields['LEVEL_EDGE_FILE_FORMAT']}")
    model_edge_files = np.array(sorted(glob.glob(model_edge_files)))

    ## Concentrations
    model_conc_files = (f"{mod_fields['MODEL_DIR']}/"
                        f"{mod_fields['CONCENTRATION_FILE_FORMAT']}")
    model_conc_files = np.array(sorted(glob.glob(model_conc_files)))

    # Require that all of these lists contain files.
    assert ((len(sat_files) > 0) 
            and (len(model_edge_files) > 0)
            and (len(model_conc_files) > 0)), \
            "One of the provided directories is empty."
    
    # If not reprocess, remove 
    if ~bool(sat_fields["REPROCESS"]):
        # Get list of processed files
        proc_files = f"{mod_fields['SAVE_DIR']}/*"
        proc_files = np.array(sorted(glob.glob(proc_files)))

        # Compare to the staellite files
        proc_files = [f.split("/")[-1].split("_operator.nc")[0] 
                      for f in proc_files]
        excl_files = [f.split("/")[-1] for f in sat_files
                      if f.split("/")[-1].split(".")[0] in proc_files]
        sat_files = [f for f in sat_files 
                     if f.split("/")[-1].split(".")[0] not in proc_files]
        print(excl_files)

        print(f"  Skipping ", excl_files)

    return sat_files, model_edge_files, model_conc_files


def get_gc_dates(file_names):
    '''
    TO DO: switch to YYYYMMDD reading of config.yaml inputs
    so that this is more flexible if file formats ever change.
    '''
    dates = [d.split('/')[-1].split('.')[-2].split('_')[0] 
             for d in file_names]
    return dates


def get_gc_files_for_dates(file_names, dates):
    return file_names[np.in1d(get_gc_dates(file_names), dates)]


def get_satellite_parser(satellite_name):
    # Get the function that opens the satellite data. Check that the function
    # has a default value for satellite_name. If not, use satellite_name
    read_sat = getattr(parsers, config[satellite_name]["PARSER"])
    name_param = inspect.signature(read_sat).parameters["satellite_name"]
    if name_param.default is not name_param.empty:
        satellite_name = name_param.default
    print(f"satellite_name : {satellite_name}")
    print(f"parser : {config[satellite_name]['PARSER']}")

    # Define the function
    def read_satellite(file_path):
        dataset = read_sat(file_path, satellite_name)
        dataset = parsers.check_satellite_data(dataset)
        return dataset
    
    return read_satellite

def colocate_obs(model, satellite):
    """
    directly from Hannah's code
    get gridcells which are coincident with each satellite observation
    assumes model pixel size >> satellite pixel size
    fast implementation, credit Nick
    TO DO : This could be sped up using Nick's implementation, but that
    requires knowledge of the latitude and longitude delta
    """
    # First, check that everything in the satellite time is in the model
    # data.
    satellite_times = satellite["TIME"].dt.strftime("%Y%m%d.%H")
    model_times = model["TIME"].dt.strftime("%Y%m%d.%H")
    missing_times = np.in1d(satellite_times, model_times)
    if (~missing_times).sum() > 0:
        print(f"  Missing model data at the following {missing_times.sum()} times:")
        print(satellite_times[missing_times].values)
        print("  And the following missing dates:")
        print(np.unique([str(d.values)[:6] for d in satellite_times[missing_times]]))
    
    # Now get indices, beginning with time
    time_idx = np.where(satellite_times[missing_times]
                        == model_times)[1]
    time_idx = xr.DataArray(time_idx, dims="NOBS")

    # Longitude index
    lon_idx = np.abs(
        model["LONGITUDE"].values.reshape((-1, 1))
        - satellite["LONGITUDE"].values[missing_times].reshape((1, -1))
    )
    lon_idx = lon_idx.argmin(axis=0)
    lon_idx = xr.DataArray(lon_idx, dims="NOBS")

    # Latitude index
    lat_idx = np.abs(
        model["LATITUDE"].values.reshape((-1, 1))
        - satellite["LATITUDE"].values[missing_times].reshape((1, -1))
    )
    lat_idx = lat_idx.argmin(axis=0)
    lat_idx = xr.DataArray(lat_idx, dims="NOBS")

    return lon_idx, lat_idx, time_idx