import numpy as np


class VerticalGrid:
    """
    Can be used independently to interpolate, or used inside functions
    in operators.py.

    model_ch4_layers:  nobs x n_model_edges-1,
                       units: concentration-type (ppb, vmr, etc.)
    satellite_edges:   nobs x n_satellite_edges
                       units: pressure
    model_edges:       nobs x n_model_edges
                       units: pressure
    """

    def __init__(
        self,
        model_ch4_layers,
        model_edges,
        satellite_edges,
        interpolate_to_centers_or_edges,
    ):
        self.model_ch4_layers = model_ch4_layers
        self.model_edges = model_edges
        self.satellite_edges = satellite_edges
        self.interpolate_to_centers_or_edges = interpolate_to_centers_or_edges

        self.__expand_profile_dims()
        self.__check_input_structure()

    def __expand_profile_dims(self):
        """
        If profiles have only one observation, 
        expand to a 2D array with dims (nobs x n_model edges) where n_obs=1.
        """
        if self.model_ch4_layers.ndim == 1:
            self.model_ch4_layers = np.expand_dims(self.model_ch4_layers, axis=0)
        if self.model_edges.ndim == 1:
            self.model_edges = np.expand_dims(self.model_edges, axis=0)
        if self.satellite_edges.ndim == 1:
            self.satellite_edges = np.expand_dims(self.satellite_edges, axis=0)

    def __check_input_structure(self):
        assert (
            self.model_ch4_layers.ndim == 2
        ), "GEOS-Chem methane layers must be 2D (nobs x nlevels), or 1D (nlevels)."
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

        assert (
            self.model_edges.shape[0]
            == self.satellite_edges.shape[0]
            == self.model_ch4_layers.shape[0]
        ), (
            f"GEOS-Chem and satellite must have the same number of observations. "
            f"model_ch4_layers nobs = {self.model_ch4_layers.shape[0]} "
            f"model_edges nobs = {self.model_edges.shape[0]} "
            f"satellite_edges nobs = {self.satellite_edges.shape[0]} "
        )
        assert self.model_ch4_layers.shape[1] + 1 == self.model_edges.shape[1], (
            "GEOS-Chem has mismatched vertical coordinates. "
            "model_ch4_layers should have one less vertical coordinate than model_edges."
        )

    @staticmethod
    def __clip_model_to_satellite_range(model_edges, satellite_edges):
        """
        We want to account for the case when the GEOS-Chem surface
        is above the satellite surface (altitude wise) or the GEOS-Chem
        top is below the satellite top.. We do this by adjusting the
        GEOS-Chem surface pressure up to the TROPOMI surface pressure
        """
        # # hannah's parallelized implementation
        # # need to double check this is same as GOSAT method (it should be, but GOSAT skips more layers)
        # idx_bottom = np.less(GC_edges[:, 0], sat_edges[:, 0])
        # idx_top = np.greater(GC_edges[:, -1], sat_edges[:, -1])
        # GC_edges[idx_bottom, 0] = sat_edges[idx_bottom, 0]
        # GC_edges[idx_top, -1] = sat_edges[idx_top, -1]
        # return None

    @staticmethod
    def __get_interpolation_map(model_edges, satellite_edges):
        """
        Hannah's GC_to_sat_levels function
        Redistributes *and integrates* GEOS-Chem layers to satellite layers.
        Equivalent to W * M_in in Keppens et al. (2019) eq. X
        DOUBLE CHECK this is actually W * M_in and not M_out * W
        """
        # todo: DOUBLE CHECK this is actually W * M_in and not M_out * W
        # Define matrices with "low" and "high" pressure values for each layer.
        # shape: nobs x n_model_levels - 1 x n_satellite_levels - 1
        model_low = model_edges[:, 1:][:, :, None]
        model_high = model_edges[:, :-1][:, :, None]
        satellite_low = satellite_edges[:, 1:][:, None, :]
        satellite_high = satellite_edges[:, :-1][:, None, :]

        # Get the indices where the GC-to-satellite mapping, which is
        # a nobs x ngc x nsat matrix, is non-zero
        # # todo: is it non-zero for GOSAT too?
        idx = np.less_equal(satellite_low, model_high) & np.greater_equal(
            satellite_high, model_low
        )

        # Find the fraction of each GC level that contributes to each
        # TROPOMI level. We should first divide (to normalize) and then
        # multiply (to apply the map to the column) by the GC pressure
        # difference, but we exclude this (since it's the same as x1).
        model_to_satellite = np.minimum(satellite_high, model_high) - np.maximum(
            satellite_low, model_low
        )
        model_to_satellite[~idx] = 0

        return model_to_satellite

    @staticmethod
    def __get_centers_to_edges_map(satellite_edges):
        """
        equivalent to M_out* in Keppens et al. (2019).
        Skip if you want result on layers/centers/partial columns.
        """
        # todo: Need to make sure you can apply all the a diagonal matrices at once.
        edges_to_centers = np.zeros_like(satellite_edges)
        edges_to_centers[:, 0] = satellite_edges[:, 0]
        edges_to_centers[:, -1] = satellite_edges[:, -1]
        edges_to_centers[:, 1:-1] = satellite_edges[:, :-1] - satellite_edges[:, 1:]
        centers_to_edges = 1 / edges_to_centers  # invert diagonal matrices
        return centers_to_edges

    def interpolate(self):
        """
        Interpolate GEOS-Chem methane to satellite edges OR centers.

        Turns out neither of us use dry air for anything b/c it's neglibible for interpolation.
            Dry air only matters for the pressure weighting.
        """
        clipped_model_edges = self.__clip_model_to_satellite_range(
            model_edges=self.model_edges, satellite_edges=self.satellite_edges
        )
        model_to_satellite = self.__get_interpolation_map(
            model_edges=clipped_model_edges, satellite_edges=self.satellite_edges
        )
        if self.interpolate_to_centers_or_edges == "centers":
            centers_to_edges = self.__get_centers_to_edges_map(
                satellite_edges=self.satellite_edges
            )
        else:
            centers_to_edges = None  # centers_to_edges = np.ones_like(<dims>)

        # Now map the GC CH4 to the satellite levels
        # todo: add centers to edges
        model_column = None  # need to write this
        # model_column = (model_to_satellite * self.methane_ch4_layers[:, :, None]).sum(
        #     axis=1
        # ) / model_to_satellite.sum(axis=1)
        # interpolate model to satellite grid

        # todo: process in chunks of 1 million?

        return model_column
