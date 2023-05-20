from gcpy import read_geoschem_file

with open("config.yml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)


read_gc_file = read_geoschem_file # use gcpy function for reading GEOS-Chem files, may need to wrap


def read_TROPOMI_vXX(file_path):
    # read TROPOMI file
    # grab tropomi data columns specified in config and rename them to standard naming
    pass


def read_GOSAT_vXX(file_path):
    # read GOSAT file
    # grab tropomic data columns specified in config and rename them to standard naming
    pass
