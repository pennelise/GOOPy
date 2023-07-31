# satellite-operators

Mass-conserving vertical interpolation and satellite observation operator for inclusion in GCPy. 

- Inputs: nobs x nedges for 1) satellite observations and 2) corresponding GEOS-Chem columns (requires GEOS-Chem LevelEdgeDiags output).
- Outputs: GEOS-Chem concentrations interpolated to the satellite layer centers (nobs x nlayers) or satellite layer edges (nobs x nedges)
- The code will be parallelized so it should be reasonably fast in Python. 

Discussed in this issue for GCPy: https://github.com/geoschem/gcpy/issues/242
