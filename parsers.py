import os

os.environ['OPENBLAS_NUM_THREADS'] = '8'
os.environ['MPI_NUM_THREADS'] = '8'
os.environ['MKL_NUM_THREADS'] = '8'
os.environ['OMP_NUM_THREADS'] = '8'

import xarray as xr
import numpy as np
import re

def _open_geoschem(file_path, variables):
    # Open the dataset
    # data = xr.open_mfdataset(file_path, parallel=True)
    data = []
    for f in file_path:
        data.append(xr.open_dataset(f).compute())
    data = xr.merge(data)

    # Now we get the variables we want, accounting for regex options. We also 
    # save out a dictionary that will rename the variables as needed to the 
    # standard names.
    save_vars = {}
    for default_name, var_pattern in variables.items():
        # If the item looks like a regex (contains special characters like '*'), 
        # treat it as regex
        if re.search(r"[\*]", var_pattern):
            save_vars.update(
                {var : 
                 f"{default_name}_{var.split(var_pattern.split('.*')[0])[-1]}" 
                 for var in data.variables if re.match(var_pattern, var)})
        else:
            # If it's an exact match, check if it's in the dataset
            if var_pattern in data.variables:
                save_vars.update({var_pattern : default_name})

    # Return the subsetted data
    return data[save_vars.keys()].rename(save_vars)


def read_geoschem_file(file_path_conc, file_path_edges, data_fields):
    '''
    Eventually, this should be switched to a gcpy function. 
    From Elise:
        read_gc_file = read_geoschem_file 
        # use gcpy function for reading GEOS-Chem files, may need to wrap
    '''
    # Define the variables that should be maintained when opening the files
    ## For concentration files, keep everything except PRESSURE_EDGES. Also,
    ## get rid of CONC_AT_PRESSURE_CENTERS for edge files.
    conc_vars = dict(data_fields)
    del conc_vars["PRESSURE_EDGES"]

    edge_vars = dict(data_fields)
    del edge_vars["CONC_AT_PRESSURE_CENTERS"]

    # Open and combine edge and concentration files
    gc = xr.merge([_open_geoschem(file_path_conc, conc_vars),
                   _open_geoschem(file_path_edges, edge_vars)])

    # Transpose
    gc = gc.transpose("TIME", "LONGITUDE", "LATITUDE", "LEV", "ILEV")

    #  TO DO: Check if we need to fill the first hour of the data.

    return gc


def read_satellite_file(file_path, data_fields):
    '''
    This generic parser assumes that the data is a netcdf with a single, 
    main group with variables as defined in the config.yaml file. It 
    also assumes that all filtering is contained in an optional quality_flag
    file that is 0 for quality data and 1 elsewhere. In reality, satellite
    data may be contained in complex netcdf files with multiple groups and 
    may require filtering along multiple criteria. Please write your own 
    parser in these cases.
    '''
    # Remove quality_flag if it isn't present in the fields
    data_fields = {k : v for k, v in data_fields.items() if v.lower() != 'none'}

    # Open the file (and remove subsetting because we want to keep variables)
    satellite = xr.open_dataset(file_path)

    # Rename satellite dimension names to the standard from config.yaml
    rename_fields = {v : k for k, v in data_fields.items()}
    satellite = satellite.rename(rename_fields)

    # Return the data
    return satellite

def read_TROPOMI(file_path, data_fields):
    # Remove quality_flag if it isn't present in the fields
    data_fields = {k : v for k, v in data_fields.items() if v.lower() != 'none'}

    satellite = xr.open_dataset(file_path)


    # Correct units from molecules/cm2 to mol/m2
    satellite['ch4_profile_apriori'] *= 1e4/6.02214e23
    satellite['dry_air_subcolumns'] *= 1e4/6.02214e23


    # d = xr.open_dataset(file, group='diagnostics')    

    pass


def read_TROPOMI_blended(file_path, data_fields):
    # Remove none fields
    data_fields = {k : v for k, v in data_fields.items() if v.lower() != 'none'}

    # Open the satellite file. The blended data has all fields in one group.
    satellite = xr.open_dataset(file_path)

    # Rename satellite dimension names to the standard from config.yaml)
    rename_fields = {v : k for k, v in data_fields.items()}
    satellite = satellite.rename(rename_fields)

    # Get the pressure edges (Pa) based on the TROPOMI surface and pressure 
    # intervals. The pressure array is from TOA for consistency with other 
    # TROPOMI objects.
    z = satellite.layer.size
    p_surface = satellite['surface_pressure'].values.reshape((-1, 1))
    p_interval = satellite['pressure_interval'].values.reshape((-1, 1))
    p_edges = p_surface - np.arange(z + 1).reshape((1, -1))*p_interval
    p_edges = xr.DataArray(p_edges[:, ::-1], dims=['N_OBS', 'N_EDGES'])
    satellite = satellite.assign(PRESSURE_EDGES=p_edges)

    return satellite

def read_GOSAT_vXX(file_path, data_fields):
    # read GOSAT file
    # grab tropomic data columns specified in config and rename them to standard naming
    pass


def read_OCO2_v11_1_preprocessed(file_path, data_fields):
    # Use the standard parser first
    satellite = read_satellite_file(file_path, data_fields)
    
    # Convert units from ppm to mol/mol
    satellite["PRIOR_PROFILE"] *= 1e-6
    satellite["SATELLITE_COLUMN"] *= 1e-6

    # Filter (we will comment this out for the final round of iterations)
    satellite = satellite.compute()
    satellite = satellite.where(satellite["type_flag"] < 2, drop=True)

    return satellite


def check_satellite_data(satellite):
    # TO DO: assert type(sat["TIME"]) == datetime (need to deal with the fact
    # that dtype shows up as '<M8[ns]' or '>M8[ns]' depending on the endianess
    # ?? of the system)
        # Ensure that satellite pressure levels are in descending order:
    if np.all(np.diff(satellite["PRESSURE_EDGES"]) > 0):
        print("  Switching direction of N_EDGES.")
        satellite = satellite.reindex(
            N_EDGES=list(reversed(satellite["N_EDGES"]))
        )

    return satellite