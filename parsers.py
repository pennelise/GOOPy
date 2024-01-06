import xarray as xr
import yaml
# from gcpy import read_geos_chem_file

with open("config.yaml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)


def _open_geoschem(file_path, variables):
    preprocess = lambda ds : ds[variables]
    return xr.open_mfdataset(file_path, preprocess=preprocess)


def read_geoschem_file(file_path_edges, file_path_conc):
    '''
    Eventually, this should be switched to a gcpy function. 
    From Elise:
        read_gc_file = read_geoschem_file # use gcpy function for reading GEOS-Chem files, may need to wrap
    '''
    # Define the variables that should be maintained when opening the files
    fields = config["MODEL"]["DATA_FIELDS"]

    conc_vars = dict(fields)
    del conc_vars["PRESSURE_EDGES"]

    edge_vars = dict(fields)
    del edge_vars["CONCENTRATION_AT_PRESSURE_CENTERS"]

    # Open and combine edge and concentration files
    gc = xr.merge([_open_geoschem(file_path_conc, list(conc_vars.values())),
                   _open_geoschem(file_path_edges, list(edge_vars.values()))])

    # Rename the fields to the standard (as defined in config.yaml)
    rename_fields = {v : k for k, v in fields.items()}
    gc = gc.rename(rename_fields)

    return gc


def read_satellite_file(file_path, satellite_name):
    '''
    This generic parser assumes that the data is a netcdf with a single, 
    main group with variables as defined in the config.yaml file. It 
    also assumes that all filtering is contained in an optional quality_flag
    file that is 0 for quality data and 1 elsewhere. In reality, satellite
    data may be contained in complex netcdf files with multiple groups and 
    may require filtering along multiple criteria. Please write your own 
    parser in these cases.
    '''
    # Get the fields for the satellite specified as defined in config.yaml
    fields = config[satellite_name]["DATA_FIELDS"]
    
    # Remove quality_flag if it isn't present in the fields
    fields = {k : v for k, v in fields.items() if v.lower() != 'none'}

    # Open the file and subset
    satellite = xr.open_dataset(file_path)[list(fields.values())]

    # Rename satellite dimension names to the standard (as defined in 
    # config.yaml)
    rename_fields = {v : k for k, v in fields.items()}
    satellite = satellite.rename(rename_fields)

    # Return the data
    return satellite

def read_TROPOMI_vXX(file_path, satellite_name="TROPOMI_vXX"):
    # read TROPOMI file
    # grab tropomi data columns specified in config and rename them to standard naming
    pass


def read_GOSAT_vXX(file_path, satellite_name="GOSAT_vXX"):
    # read GOSAT file
    # grab tropomic data columns specified in config and rename them to standard naming
    pass


def read_OCO2(file_path, satellite_name="OCO2"):
    pass