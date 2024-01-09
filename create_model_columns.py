'''
A python script to demonstrate the use of the operator.
'''

import yaml
import numpy as np
import utilities as util
import operators as op
import parsers

# TO DO: Implement a working version that doesn't assume the user has dask
# installed.

# Define the name of the satellite that the operator is being applied to. In
# the future, this can be replaced by sys.argv[1] so that the operator can be
# called from the command line as: 
# python create_model_columns.py satellite_name
satellite_name = "OCO2_v11.1_preprocessed"
file_length_threshold = 1e5

# Open the config file
with open("config.yaml", "r", encoding="utf8") as f:
    config = yaml.safe_load(f)

# Obtain a list of the satellite and GEOS-Chem files.
sat_files, gc_edge_files, gc_conc_files = util.get_file_lists(sat_name)

# Get the dates for which we have gc_edge_files and gc_conc_files
# TO DO: Currently, this assumes that the GEOS-Chem files are daily or monthly
#(i.e., that the hours are 0, or that the files end in _0000z.nc). We should 
# update this to be more flexible.)
gc_dates = np.unique([date for date in util.get_gc_dates(gc_edge_files)
                      if date in util.get_gc_dates(gc_conc_files)])

# Get the satellite parser. 
read_sat = util.get_satellite_parser(sat_name)

# Iterate through the satellite files.
for sf in sat_files:
    # Open the file
    sat = read_sat(sf)

    # Get all unique dates from the file, and check for overlap with the 
    # GEOS-Chem files.
    sat_dates = np.unique(sat["TIME"].dt.strftime("%Y%m%d"))
    sat_dates = [date for date in sat_dates if date in gc_dates]
    if len(sat_dates) == 0:
        print(f"There are no temporally overlapping GEOS-Chem data for {sf}")
        continue

    # Next, open the GEOS-Chem files. We iterate through this in chunks of
    # file_length_threshold to balance memory constraints with the benefits
    # of vectorization.
    i = 0
    while i < sat.dims["N_OBS"]:
        # Subset the satellite file so that we are dealing with a smaller file
        sat_i = sat.isel(N_OBS=slice(int(i), int(i + file_length_threshold)))

        # Get the dates that need to be processed
        process_dates = np.unique(sat_i["TIME"].dt.strftime("%Y%m%d"))

        # Get gc_edge and gc_conc file names for these dates.
        gc_conc_i = util.get_gc_files_for_dates(gc_conc_files, process_dates)
        gc_edge_i = util.get_gc_files_for_dates(gc_edge_files, process_dates)
        
        # Open these files
        gc_i = parsers.read_geoschem_file(gc_conc_i, gc_edge_i)

        # Run the column operator
        gc_col_i = op.get_model_columns(
            gc_i, 
            sat_i, 
            config[sat_name]["AVERAGING_KERNEL_USES_CENTERS_OR_EDGES"]
            )
        


        # Tick i upward
