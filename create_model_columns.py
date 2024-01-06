'''
A python script to demonstrate the use of the operator.
'''

import yaml
import numpy as np
import xarray as xr
import utilities as util
import parsers

# TO DO: Implement a working version that doesn't assume the user has dask
# installed.

# Define the name of the satellite that the operator is being applied to. In
# the future, this can be replaced by sys.argv[1] so that the operator can be
# called from the command line as: 
# python create_model_columns.py satellite_name
sat_name = 'OCO2_v11.1_preprocessed'
file_length_threshold = 1e4

# Open the config file
with open("config.yaml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)

# Obtain a list of the satellite and GEOS-Chem files.
sat_files, gc_edge_files, gc_conc_files = util.get_file_lists(sat_name)

# Require that all of these contain files.
assert ((len(sat_files) > 0) 
        and (len(gc_edge_files) > 0)
        and (len(gc_conc_files) > 0)), \
        "One of the provided directories is empty."

# Get the dates for which we have gc_edge_files and gc_conc_files
# TO DO: Currently, this assumes that the GEOS-Chem files are daily or monthly
#(i.e., that the hours are 0, or that the files end in _0000z.nc). We should 
# update this to be more flexible.)
gc_dates = np.unique([date for date in util.get_gc_dates(gc_edge_files)
                      if date in util.get_gc_dates(gc_conc_files)])

# Get the function that opens the satellite data. Check that the function has
# a default value for satellite_name. If not, use the default sat_name defined
# at the top of this script.
read_sat = util.get_satellite_parser(sat_name)

# Iterate through the satellite files.
for sf in sat_files:
    # Open the file
    sat = read_sat(sf)

    # Get all unique dates from the file, and check for overlap with the 
    # GEOS-Chem files.
    # TO DO: assert type(sat["TIME"]) == datetime (need to deal with the fact
    # that dtype shows up as '<M8[ns]' or '>M8[ns]' depending on the endianess
    # ?? of the system)
    sat_dates = np.unique(sat["TIME"].dt.strftime("%Y%m%d"))
    sat_dates = [date for date in sat_dates if date in gc_dates]
    if len(sat_dates) == 0:
        print(f"There are no temporally overlapping GEOS-Chem data for {sf}")
        continue

    # Next, open the GEOS-Chem files. We iterate through this in chunks of
    # file_length_threshold to balance memory constraints with the benefits
    # of vectorization.
    i = 0
    while i < len(sat_dates):
        # Subset the satellite file so that we are dealing with a smaller file
        sat_i = sat.isel(N_OBS=slice(int(i), int(i + file_length_threshold)))

        # Get the dates that need to be processed
        process_dates = np.unique(sat_i["TIME"].dt.strftime("%Y%m%d"))

        # Get gc_edge and gc_conc file names for these dates.
        gc_edge_i = util.get_gc_files_for_dates(gc_edge_files, process_dates)
        gc_conc_i = util.get_gc_files_for_dates(gc_conc_files, process_dates)
        
        # Open these files
        gc = parsers.read_geoschem_file(gc_edge_i, gc_conc_i)

        # Run the column operator
        ...

        # Tick i upward
