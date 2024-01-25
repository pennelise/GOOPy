
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
    if sat_fields["REPROCESS"].lower() == "false":
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

        print(f"  Skipping ", excl_files)

    return sat_files, model_edge_files, model_conc_files


def get_gc_dates(file_names):
    '''
    TO DO: switch to YYYYMMDD reading of config.yaml inputs
    so that this is more flexible if file formats ever change.
    '''
    dates = [d.split("/")[-1].split(".")[-2].split("_")[0] 
             for d in file_names]
    dates = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in dates]
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

def get_missing_times(satellite_times, model_times):
    satellite_times = satellite_times.dt.strftime("%Y-%m-%d.%H")
    missing_times = xr.DataArray(
        ~np.in1d(satellite_times, model_times.dt.strftime("%Y-%m-%d.%H")),
        dims="N_OBS")
    if missing_times.sum() > 0:
        print(f"  Missing model data at the following"
              f" {missing_times.sum().values} times:")
        print(satellite_times[missing_times].values)
    return missing_times


def colocate_obs(model, satellite):
    """
    directly from Hannah's code
    get gridcells which are coincident with each satellite observation
    assumes model pixel size >> satellite pixel size
    fast implementation, credit Nick
    TO DO : This could be sped up using Nick's implementation, but that
    requires knowledge of the latitude and longitude delta
    """    
    # Now get indices, beginning with time
    time_idx = np.where(satellite["TIME"].dt.strftime("%Y-%m-%d.%H") 
                        == model["TIME"].dt.strftime("%Y-%m-%d.%H"))
    if len(time_idx) == 2:
        time_idx = time_idx[1]
    elif len(time_idx) == 1:
        time_idx = time_idx[0]
    else:
        raise ValueError('Time index is not recognized.')
    time_idx = xr.DataArray(time_idx, dims="N_OBS")

    # Longitude and latitude index
    lon_idx = get_closest_index(model["LONGITUDE"].values, 
                                satellite["LONGITUDE"].values)
    lat_idx = get_closest_index(model["LATITUDE"].values, 
                                satellite["LATITUDE"].values)

    # Subset the data
    model = model.isel(TIME=time_idx, LONGITUDE=lon_idx, LATITUDE=lat_idx)

    return model

def get_closest_index(model_data, satellite_data, xarray=True, dims="N_OBS"):
    idx = np.abs(
        model_data.reshape((-1, 1)) - satellite_data.reshape((1, -1)))
    idx = idx.argmin(axis=0)
    if xarray:
        idx = xr.DataArray(idx, dims=dims)
    return idx