import os
import xarray as xr
import numpy as np
import pandas as pd
import re
import inspect
from interpolation import VerticalGrid

def _open_geoschem(file_path, variables):
    # Open the dataset
    # data = xr.open_mfdataset(file_path, parallel=True)
    data = []
    for f in file_path:
        data.append(xr.open_dataset(f).compute())
    data = xr.concat(data, dim="time", data_vars="all")

    # Now we get the variables we want, accounting for regex options. We also 
    # save out a dictionary that will rename the variables as needed to the 
    # standard names.
    save_vars = {}
    for default_name, var_pattern in variables.items():
        # If the item looks like a regex (contains special characters like "*"), 
        # treat it as regex
        if re.search(r"[\*]", var_pattern):
            save_vars.update(
                {var : 
                 f"{default_name}_{var.split(var_pattern.split(".*")[0])[-1]}" 
                 for var in data.variables if re.match(var_pattern, var)})
        else:
            # If it"s an exact match, check if it"s in the dataset
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
    # Remove quality_flag if it isn"t present in the fields
    data_fields = {k : v for k, v in data_fields.items() if v.lower() != "none"}

    # Open the file (and remove subsetting because we want to keep variables)
    satellite = xr.open_dataset(file_path)

    # Rename satellite dimension names to the standard from config.yaml
    rename_fields = {v : k for k, v in data_fields.items()}
    satellite = satellite.rename(rename_fields)

    # Return the data
    return satellite


def read_TCCON_MIP(file_path, data_fields):
    tccon = xr.open_dataset(file_path, group="CO2")

    rename_fields = {v : k for k, v in data_fields.items()
                     if v != "none"}
    tccon = tccon.rename(rename_fields)

    # First, drop unneeded variables
    tccon = tccon.drop_vars(["prior_h2o",
                             "sza",
                             "prior_mixing_tccon",
                             "public"])

    # Then, adjust the units of TCCON to match GEOS-Chem
    ## Pa to hPa
    for var in ["p_surf", "p_levels_prior", "p_levels_ak"]:
        tccon[var] *= 1e-2
    ## ppm to mol/mol (dry)
    for var in ["PRIOR_PROFILE", "SATELLITE_COLUMN", "sigma_column_mixing"]:
        tccon[var] *= 1e-6

    # Process the time to be a reasonable format
    time = pd.DataFrame({
        "year" : tccon["TIME"].isel(idate=0),
        "month" : tccon["TIME"].isel(idate=1),
        "day" : tccon["TIME"].isel(idate=2),
        "hour" : tccon["TIME"].isel(idate=3),
        "minute" : tccon["TIME"].isel(idate=4),
        "second" : tccon["TIME"].isel(idate=5)
    })
    tccon["TIME"] = xr.DataArray(pd.to_datetime(time).values, 
                                 dims=["N_OBS"], 
                                 coords={"N_OBS" : tccon.coords["N_OBS"]})
    tccon = tccon.drop_vars(["solar_time_bin"])

    # The averaging kernel is defined on the fixed pressure grid p_levels_ak.
    # We cut off everything at the TCCON surface pressure.
    pressure = tccon["p_levels_ak"].expand_dims(N_OBS=tccon.sizes["N_OBS"])

    # Deal with the case where the pressure grid is fully above the surface
    # pressure. We replace the bottom level with the surface pressure.
    p0 = pressure.isel(N_EDGES=0)
    p0 = p0.where(p0 >= tccon["p_surf"], tccon["p_surf"])
    pressure = xr.where(
        pressure["N_EDGES"] == pressure["N_EDGES"][0],
        p0,
        pressure
    )

    # Truncate the dataset to only be above the TCCON surface. Fill in the 
    # first nan value with p_surf.
    pressure = pressure.where(pressure <= tccon["p_surf"])
    edge_index = xr.DataArray(np.arange(pressure.sizes["N_EDGES"]), 
                              dims="N_EDGES")
    replace_mask = (edge_index == (pressure.notnull().argmax("N_EDGES") - 1))
    pressure = xr.where(replace_mask, tccon["p_surf"], pressure)
    
    # Now, shift any variables that are on the N_OBS x N_EDGES grid so that
    # the surface is the first 
    shift_grid = lambda var, fill_zero : xr.apply_ufunc(
        shift_tccon_pressure_grid,
        var,
        kwargs={"fill_zero": fill_zero},
        input_core_dims=[["N_EDGES"]],
        output_core_dims=[["N_EDGES"]],
        vectorize=True
    )
    for name, var in tccon.data_vars.items():
        if ("N_EDGES" in var.dims) & ("N_OBS" in var.dims):
            # Truncate the dataset to only be above the TCCON surface
            print(name)
            var = var.where(~pressure.isnull())

            # Shift so that the first level is first
            tccon[name] = shift_grid(var, True)
    
    # And finally shift the pressure variable
    pressure = shift_grid(pressure, False)

    # Save out the pressure edges in hPa
    tccon["PRESSURE_EDGES"] = pressure
    
    # Define the pressure weights. Note that tccon["p_surf"] and the first level
    # of pressure should be the same.
    pressure_weight = - pressure.diff(dim="N_EDGES") / tccon["p_surf"]
    pressure_weight = pressure_weight.rename({'N_EDGES' : 'N_CENTERS'})
    tccon["PRESSURE_WEIGHT"] = pressure_weight

    # We are now working on a pressure center grid. We need to interpolate
    # the prior and the averaging kernel onto this grid.

    # First, the prior. This is currently defined on p_levels_prior, which is
    # different from the pressure grid (based on p_levels_ak). First, we 
    # very simply interpolate to pressure centers, then we use Vertical Grid 
    # to interpolate to the new grid.
    prior_profile_centers = (
        tccon["PRIOR_PROFILE"].isel(N_EDGES=slice(None, -1)) + 
        tccon["PRIOR_PROFILE"].isel(N_EDGES=slice(1, None))
    ) / 2
    prior_profile_on_new_grid = VerticalGrid(
        np.stack([prior_profile_centers.values], axis=-1), # The values to regrid
        tccon["p_levels_prior"].values, # The original grid
        tccon["PRESSURE_EDGES"].values, # The target grid
        "centers", 
        save_interpolation="False", 
        save_dir=None, 
        expand_model_edges=False
    ).interpolate()
    tccon["PRIOR_PROFILE"] = xr.DataArray(
        prior_profile_on_new_grid[:, :, 0], 
        dims=["N_OBS", "N_CENTERS"],
    )

    # Finally, we need to interpolate the averaging kernel to the pressure 
    # centers. Because our PRESSURE_EDGES are based on the p_levels_ak,
    # this is much simpler.
    ak_centers = (
        tccon["AVERAGING_KERNEL"].isel(N_EDGES=slice(None, -1)) + 
        tccon["AVERAGING_KERNEL"].isel(N_EDGES=slice(1, None))
    ) / 2
    p_levels_ak = tccon["p_levels_ak"].expand_dims(N_OBS=tccon.sizes["N_OBS"])
    ak_on_new_grid = VerticalGrid(
        np.stack([ak_centers.values], axis=-1), # The values to regrid
        p_levels_ak.values, # The original grid
        tccon["PRESSURE_EDGES"].values, # The target grid
        "centers", 
        save_interpolation="False", 
        save_dir=None,
        expand_model_edges=False
    ).interpolate()
    tccon["AVERAGING_KERNEL"] = xr.DataArray(
        ak_on_new_grid[:, :, 0], 
        dims=["N_OBS", "N_CENTERS"],
    )

    # Now, remove superfluous pressure information
    tccon = tccon.drop_vars(["p_levels_prior", "p_levels_ak"])

    return tccon


def shift_tccon_pressure_grid(row, fill_zero=True):
    # Count leading NaNs in reference
    isnan = np.isnan(row)

    if np.all(isnan):
        return row  # nothing sensible to shift

    # Get the fill value
    if fill_zero:
        fill_value = 0
    else:
        fill_value = row[~isnan][-1]  # last non-NaN value
    
    shift = max(np.argmax(~isnan), 0)

    if shift == 0:
        return row

    return np.concatenate([
        row[shift:],                     # shift left
        np.full(shift, fill_value)       # pad end
    ])


def read_TROPOMI(file_path, data_fields):
    # Define where each of the needed variables are found
    group_to_vars = {
        "PRODUCT/" : [
            "latitude",
            "longitude",
            "methane_mixing_ratio_bias_corrected",
            "qa_value",
            "time_utc",
        ],
        "PRODUCT/SUPPORT_DATA/DETAILED_RESULTS" : [
            "surface_albedo_SWIR",
            "surface_albedo_NIR",
            "column_averaging_kernel",
        ],
        "PRODUCT/SUPPORT_DATA/INPUT_DATA" : [
            "surface_altitude",
            "surface_pressure",
            "pressure_interval",
            "methane_profile_apriori",
            "dry_air_subcolumns",
            "surface_classification",
        ],
        # "PRODUCT/SUPPORT_DATA/GEOLOCATIONS" : [
        #     "longitude_bounds",
        #     "latitude_bounds",
        # ] # HN: Not supported yet
    }

    # Open the data
    satellite = []
    for group, vars in group_to_vars.items():
        satellite.append(xr.open_dataset(file_path, group=group)[vars])
    satellite = xr.merge(satellite)

    # Rename satellite dimension names to the standard from config.yaml)
    rename_fields = {v : k for k, v in data_fields.items()
                     if v.lower() != "none"}
    satellite = satellite.rename(rename_fields)

    # Collapse the scanline x groundpixel dimensions into nobs. We also get rid
    # of the time variable and move the latitude/longitude coordinates into 
    # the variables. Finally, we drop nans.
    satellite = satellite.squeeze(drop=True)
    satellite = satellite.stack(N_OBS=("scanline", "ground_pixel"))
    satellite = satellite.reset_index("N_OBS", drop=True)
    satellite = satellite.reset_coords(["LATITUDE", "LONGITUDE"])
    satellite = satellite.where(~satellite["SATELLITE_COLUMN"].isnull(),
                                drop=True)

    # Convert the satellite column from ppb to mol/mol (GEOS-Chem base units)
    satellite["SATELLITE_COLUMN"] *= 1e-9 

    # The prior and the dry_air_subcolumns are both in mol/m2. We use 
    # dry_air_subcolumns to convert the prior to mol/mol
    satellite["PRIOR_PROFILE"] = (satellite["PRIOR_PROFILE"] / 
                                  satellite["dry_air_subcolumns"])

    # Handle pressure
    z = xr.DataArray(np.arange(satellite["N_CENTERS"].shape[0] + 1)[::-1],
                     dims="N_EDGES")                     
    satellite["PRESSURE_EDGES"] = (
        satellite["surface_pressure"] - z*satellite["pressure_interval"]
    ) / 100 # convert to hPa
    satellite = satellite.drop_vars(["surface_pressure", "pressure_interval"])

    # Calculate the pressure weights
    satellite["PRESSURE_WEIGHT"] = (
        satellite["dry_air_subcolumns"] / 
        satellite["dry_air_subcolumns"].sum(dim="N_CENTERS")
    )
    satellite = satellite.drop_vars(["dry_air_subcolumns"])

    # Process the time variable
    satellite["TIME"] = xr.DataArray(
        [t.replace("Z", "") for t in satellite["TIME"].values],
        coords=satellite["TIME"].coords,
        dims=satellite["TIME"].dims).astype("datetime64[ns]"
    )

    # Define the blended albedo 
    satellite["blended_albedo"] = (
        2.4 * satellite["surface_albedo_NIR"] - 
        1.13 * satellite["surface_albedo_SWIR"])

    # TODO: Handle QA masking? 
    # TODO: I'm also currently not handling the surface classification variable

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
    # satellite = satellite.where(satellite["type_flag"] < 2, drop=True)

    return satellite


def check_satellite_data(satellite):
    # TODO: assert type(sat["TIME"]) == datetime (need to deal with the fact
    # that dtype shows up as "<M8[ns]" or ">M8[ns]" depending on the endianess
    # ?? of the system)
    # Ensure that satellite pressure levels are in descending order:
    if np.all(np.diff(satellite["PRESSURE_EDGES"]) >= 0):
        print("  Switching direction of N_EDGES/N_CENTERS.")
        # Identify which flip dims actually exist in this dataset, then flip them
        dims_to_flip = {"N_CENTERS", "N_EDGES"}
        active_flip_dims = dims_to_flip & set(satellite.dims)
        satellite = satellite.isel(
            {dim: slice(None, None, -1) for dim in active_flip_dims}
        )
        
    # Ensure that the satellite data has the correct ordering of dimensions
    satellite = satellite.transpose("N_OBS", ...)

    return satellite


def get_satellite_parser(config):
    # Get the function that opens the satellite data. Check that the function
    # has a default value for satellite_name. If not, use satellite_name
    satellite_name = config["LOCAL_SETTINGS"]["SATELLITE_NAME"]
    read_sat = globals()[config[satellite_name]["PARSER"]]
    name_param = inspect.signature(read_sat).parameters["data_fields"]
    if name_param.default is not name_param.empty:
        satellite_name = name_param.default
    print(f"satellite_name : {satellite_name}")
    print(f"parser : {config[satellite_name]['PARSER']}")

    # Define the function
    def read_satellite(file_path):
        dataset = read_sat(file_path, config[satellite_name]["DATA_FIELDS"])
        dataset = check_satellite_data(dataset)
        return dataset
    
    return read_satellite
