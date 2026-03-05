import os
import glob
import numpy as np
import xarray as xr

def get_file_lists(local_config):
    '''
    Build lists of satellite, model edge, and model concentration files to process. 
    Directories and file name formats come from config.yaml LOCAL_SETTINGS.
    '''

    sat_files = f"{local_config['OBS_DIR']}/{local_config['OBS_FILE_FORMAT']}"
    sat_files = np.array(sorted(glob.glob(sat_files)))    


    model_edge_files = (f"{local_config['MODEL_LEVEL_EDGE_DIR']}/"
                     f"{local_config['LEVEL_EDGE_FILE_FORMAT']}")
    model_edge_files = np.array(sorted(glob.glob(model_edge_files)))

    model_conc_files = (f"{local_config['MODEL_CONCENTRATION_DIR']}/"
                        f"{local_config['CONCENTRATION_FILE_FORMAT']}")
    model_conc_files = np.array(sorted(glob.glob(model_conc_files)))

    # Require that all of these lists contain files.
    if len(sat_files) == 0:
        print(f"Satellite directory: "
              f"{local_config['OBS_DIR']}/{local_config['OBS_FILE_FORMAT']}")
        raise ValueError("Satellite files are empty.")
    
    if len(model_edge_files) == 0:
        print(f"Model edge directory: "
              f"{local_config['MODEL_LEVEL_EDGE_DIR']}/"
              f"{local_config['LEVEL_EDGE_FILE_FORMAT']}")
        raise ValueError("Model edge files are empty.")
    
    if len(model_conc_files) == 0:
        print(f"Model concentration directory: "
              f"{local_config['MODEL_CONCENTRATION_DIR']}/"
              f"{local_config['CONCENTRATION_FILE_FORMAT']}")
        raise ValueError("Model concentration files are empty.")
    
    # If not reprocess, remove 
    if local_config["REPROCESS"].lower() == "false":
        # Get list of processed files
        proc_files = f"{local_config['SAVE_DIR']}/*"
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


def colocate_obs(model, satellite, save_dir=None):
    """
    directly from Hannah's code
    get gridcells which are coincident with each satellite observation
    assumes model pixel size >> satellite pixel size
    fast implementation, credit Nick
    TO DO : This could be sped up using Nick's implementation, but that
    requires knowledge of the latitude and longitude delta
    """
    # We need to get indices in time and space (lat/lon). We begin by trying to
    # load these indices, because for Jacobian simulations, it can save time.
    # If this fails, we will calculate them.
    try:
        idx = xr.open_dataset(f'{save_dir}_idx.nc')
        print("  Using pre-computed time and space indices.")
    except:
        print("  Computing time and space indices.")
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
        
        idx = xr.Dataset({"lat" : lat_idx, "lon" : lon_idx, "time" : time_idx})
        
        # Save out
        idx.to_netcdf(f"{save_dir}_idx.nc")

    # Subset the data
    model = model.isel(TIME=idx['time'], 
                       LONGITUDE=idx['lon'], LATITUDE=idx['lat'])

    return model

def get_closest_index(model_data, satellite_data, xarray=True, dims="N_OBS"):
    idx = np.abs(
        model_data.reshape((-1, 1)) - satellite_data.reshape((1, -1)))
    idx = idx.argmin(axis=0)
    if xarray:
        idx = xr.DataArray(idx, dims=dims)
    return idx
