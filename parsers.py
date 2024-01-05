import xarray as xr
import yaml
# from gcpy import read_geoschem_file

with open("config.yaml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)

def read_geoschem_file(file_path):
    '''
    Eventually, this should be switched to a gcpy function. 
    From Elise:
        read_gc_file = read_geoschem_file # use gcpy function for reading GEOS-Chem files, may need to wrap
    '''


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

    # Rename satellite dimension names to the standard (again, as defined in
    # config.yaml)
    rename_fields = {v : k for k, v in fields.items()}
    satellite = satellite.rename(rename_fields)

    # Return the data
    return satellite

def read_TROPOMI_vXX(file_path):
    # read TROPOMI file
    # grab tropomi data columns specified in config and rename them to standard naming
    pass


def read_GOSAT_vXX(file_path):
    # read GOSAT file
    # grab tropomic data columns specified in config and rename them to standard naming
    pass


def read_OCO2(file_path):
    pass