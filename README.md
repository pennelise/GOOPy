# Draft of README 

Mass-conserving vertical interpolation and satellite observation operator for inclusion in GCPy. 

- Inputs: nobs x nedges for 1) satellite observations and 2) corresponding GEOS-Chem columns (requires GEOS-Chem LevelEdgeDiags output).
- Outputs: GEOS-Chem concentrations interpolated to the satellite layer centers (nobs x nlayers) or satellite layer edges (nobs x nedges)
- The code will be parallelized so it should be reasonably fast in Python. 

Discussed in this issue for GCPy: https://github.com/geoschem/gcpy/issues/242

## The Keppens et al., 2019 equation

- todo: put an explanation of the equation here. 

##  Configuration file for satellite operators
 This file describes the structure of the satellite or model files used as inputs for the 
 satellite operator. 

 Satellite files:
 The description of the satellite files requires the following fields to be defined:
     - AVERAGING_KERNEL_USES_CENTERS_OR_EDGES: A string with value 
        'centers' or 'edges' that corresponds to whether the satellite averaging
        kernel values are measured at the pressure centers or edges of the vertical
        grid.
     - PARSER: A string corresponding to the name of a parsing function defined in
        parsers.py. If new satellites are added, new parsers need to be written.
    -  DATA_FIELDS: These fields all define the variable names in the netCDF file for your satellite. 
        name in the satellite file netcdfs.
        - N_OBS: The observation dimension (number of observations)
        - N_EDGES: The dimension containing the vertical level edges
        - N_CENTERS: The dimension containing the vertical level centers
        - Other variable values are as described by the yaml fields.

 Model files:
 The description of the model files requires the following fields to be defined:
     - LEVEL_EDGE_FILE_FORMAT: A regex string giving the format of the level edge 
        file names
     - CH4_FILE_NAME: A regex string giving the format of the methane output files
     - PRESSURE_EDGES: A string corresponding to the netcdf variable containing
        the pressure edges
     - CH4_CENTERS: A string corresponding to the netcdf variable containing the 
        methane concentrations at the center of each pressure level
     - LATITUDE, LONGITUDE, and TIME: Strings corresponding to the netcdf dimensions
        for each of the corresponding quantities