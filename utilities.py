
import yaml
import glob
import inspect
import numpy as np
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
    gc_edge_files = (f"{mod_fields['MODEL_DIR']}/"
                     f"{mod_fields['LEVEL_EDGE_FILE_FORMAT']}")
    gc_edge_files = np.array(sorted(glob.glob(gc_edge_files)))

    ## Concentrations
    gc_conc_files = (f"{mod_fields['MODEL_DIR']}/"
                     f"{mod_fields['CONCENTRATION_FILE_FORMAT']}")
    gc_conc_files = np.array(sorted(glob.glob(gc_conc_files)))

    return sat_files, gc_edge_files, gc_conc_files


def get_gc_dates(file_names):
    dates = [d.split('/')[-1].split('.')[-2].split('_')[0] 
             for d in file_names]
    return dates


def get_gc_files_for_dates(file_names, dates):
    return file_names[np.in1d(get_gc_dates(file_names), dates)]


def get_satellite_parser(satellite_name):
    # Get the function that opens the satellite data. Check that the function
    # has a default value for satellite_name. If not, use satellite_name
    read_satellite = getattr(parsers, config[satellite_name]["PARSER"])
    name_param = inspect.signature(read_satellite).parameters["satellite_name"]
    if name_param.default is name_param.empty:
        print("satellite_name is not a default argument in the provided ")
        print("parser. The sat_name provided in this script is used ")
        print("instead. Please check that the appropriate parser is being ")
        print("used for this satellite: ")
        print(f"  satellite_name : {satellite_name}")
        print(f"  parser : {config[satellite_name]['PARSER']}")
        return lambda file_path: read_satellite(file_path, satellite_name)
    else:
        return read_satellite