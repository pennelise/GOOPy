# General Observation Operator for Python (GOOPy)

Mass-conserving vertical interpolation and satellite observation operator for inclusion in GCPy. 

- Inputs: nobs x nedges for 1) satellite observations and 2) corresponding GEOS-Chem columns (requires GEOS-Chem LevelEdgeDiags and SpeciesConc outputs).
- Outputs: GEOS-Chem concentrations interpolated to the satellite layer centers (nobs x nlayers) or satellite layer edges (nobs x nedges)
- The code is parallelized so it is reasonably fast in Python. 

Discussed in this issue for GCPy: https://github.com/geoschem/gcpy/issues/242

## Installing GOOPy

- GOOPy is currently just a set of python code you can clone to your laptop - it's not pip-installable (but we plan to add this soon!)
- Therefore, the easiest way to get the dependencies is to use conda. 
- Create a new conda environment with `conda create -n goopyenv` (or install the following to your existing conda environment):
     - `conda install xarray netcdf4 h5py pyyaml dask`
- Clone GOOPy to your laptop:
     - `git clone git@github.com:pennelise/GOOPy.git`

## Using GOOPy

- Modify the directories and filenames in `config.yaml` under `LOCAL_SETTINGS` to match your satellite and model directories and filenames. 
- Navigate to your GOOPy folder (e.g. `cd ~/GOOPy/`)
- While inside your GOOPy folder, run:
     - `conda activate goopyenv`
     - `python main.py`