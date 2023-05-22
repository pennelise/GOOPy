import numpy as np


class VerticalGrid:
    """
    Can be used independently to interpolate, or used inside functions
    in operators.py.

    dim(satellite_levels) = nobs x nlevels
    """

    def __init__(self, model_edges, satellite_edges, interpolate_to_centers_or_edges):
        self.model_edges = model_edges
        self.satellite_edges = satellite_edges
        self.interpolate_to_centers_or_edges = interpolate_to_centers_or_edges

        if self.model_edges.ndim == 1:
            self.model_edges = np.expand_dims(self.model_edges, axis=0)
        if self.satellite_edges.ndim == 1:
            self.satellite_edges = np.expand_dims(self.satellite_edges, axis=0)

        self.__check_input_structure()

    def __check_input_structure(self):
        assert (
            self.model_edges.ndim == 2
        ), "GEOS-Chem pressure edges must be 2D (nobs x nlevels), or 1D (nlevels)."
        assert (
            self.satellite_edges.ndim == 2
        ), "Satellite pressure edges must be 2D (nobs x nlevels), or 1D (nlevels)."

        assert np.all(
            np.diff(self.model_edges) < 0
        ), "GEOS-Chem pressure levels must be in descending order."
        assert np.all(
            np.diff(self.satellite_edges) < 0
        ), "Satellite pressure levels must be in descending order."

        assert self.model_edges.shape[0] == self.satellite_edges.shape[0], (
            f"GEOS-Chem and satellite must have the same number of observations. "
            f"GEOS-Chem nobs = {self.model_edges.shape[0]} "
            f"Satellite nobs = {self.satellite_edges.shape[0]} "
        )

    def __get_interpolation_map(self):
        return None
        # Hannah's GC_to_sat_levels function

    def __centers_to_edges(self):
        return None
        # extra step not needed in all cases

    def __handle_edge_cases(self):
        return None
        # handle edge cases (e.g. extrapolation)
        # use Hannah's parallelized implementation

    def interpolate(self):
        self.__handle_edge_cases()
        self.__get_interpolation_map()
        if self.interpolate_to_centers_or_edges == "centers":
            self.__centers_to_edges()
        return None
        # interpolate model to satellite grid
        # all observations at once (in chunks of 1 million?)
        # I plan to use dry air if it's not too cumbersome
        # units??

    def get_pressure_weight(self):
        return None
        # calculate pressure weight from GEOS-Chem (optional)
