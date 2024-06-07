import numpy as np


class VerticalGrid:
    """
    Can be used independently to interpolate, or used inside functions
    in operators.py.

    model_conc_at_layers: nobs x n_model_edges-1,
                          units: concentration-type (ppb, vmr, etc.)
    satellite_edges:      nobs x n_satellite_edges
                       units: pressure
    model_edges:       nobs x n_model_edges
                       units: pressure
    """

    def __init__(
        self,
        model_conc_at_layers,
        model_edges,
        satellite_edges,
        interpolate_to_centers_or_edges,
    ):
        self.model_conc_at_layers = model_conc_at_layers
        self.model_edges = model_edges
        self.satellite_edges = satellite_edges
        self.interpolate_to_centers_or_edges = interpolate_to_centers_or_edges

        self.__expand_profile_dims()
        self.__check_input_structure()

        self.n_obs = self.model_conc_at_layers.shape[0]
        self.n_satellite_edges = self.satellite_edges.shape[1]
        self.n_model_edges = self.model_edges.shape[1]

    def __expand_profile_dims(self):
        """
        If profiles have only one observation,
        expand to a 2D array with dims (n_obs x n_model_edges) where n_obs=1.
        """
        if self.model_conc_at_layers.ndim == 1:
            self.model_conc_at_layers = np.expand_dims(
                self.model_conc_at_layers, axis=0
            )
        if self.model_edges.ndim == 1:
            self.model_edges = np.expand_dims(self.model_edges, axis=0)
        if self.satellite_edges.ndim == 1:
            self.satellite_edges = np.expand_dims(self.satellite_edges, axis=0)

    def __check_input_structure(self):
        assert (
            self.model_conc_at_layers.ndim == 2
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
            == self.model_conc_at_layers.shape[0]
        ), (
            f"GEOS-Chem and satellite must have the same number of observations. "
            f"model_ch4_layers nobs = {self.model_conc_at_layers.shape[0]} "
            f"model_edges nobs = {self.model_edges.shape[0]} "
            f"satellite_edges nobs = {self.satellite_edges.shape[0]} "
        )
        assert self.model_conc_at_layers.shape[1] + 1 == self.model_edges.shape[1], (
            "GEOS-Chem has mismatched vertical coordinates. "
            "model_ch4_layers should have one less vertical coordinate than model_edges."
        )

    def expand_model_to_satellite_range(self):
        """
        We want to account for the case when the GEOS-Chem surface
        is above the satellite surface (altitude wise) or the GEOS-Chem
        top is below the satellite top. We do this by adjusting the
        GEOS-Chem surface pressure up to the satellite surface pressure
        """
        idx_bottom = np.less(self.model_edges[:, 0], self.satellite_edges[:, 0])
        idx_top = np.greater(self.model_edges[:, -1], self.satellite_edges[:, -1])

        expanded_model_edges = self.model_edges.copy()
        expanded_model_edges[idx_bottom, 0] = self.satellite_edges[idx_bottom, 0]
        expanded_model_edges[idx_top, -1] = self.satellite_edges[idx_top, -1]
        return expanded_model_edges

    @staticmethod
    def get_interpolation_map(model_edges, satellite_edges):
        """
        Gets an interpolation map which converts from
        GEOS-Chem concentrations at pressure centers to satellite partial columns.

        interpolation_map is equivalent to W * M_in in Keppens et al. (2019) eq. 14,
        and has dimension (nobs x ngc x nsat)
        """

        # Define matrices with "low" and "high" pressure values for each layer.
        # shape: nobs x n_model_levels - 1 x n_satellite_levels - 1
        model_low = model_edges[:, 1:][:, :, None]
        model_high = model_edges[:, :-1][:, :, None]

        satellite_low = satellite_edges[:, 1:][:, None, :]
        satellite_high = satellite_edges[:, :-1][:, None, :]

        interpolation_map = np.minimum(satellite_high, model_high) - np.maximum(
            satellite_low, model_low
        )
        layers_do_not_intersect = ~(
            np.less_equal(satellite_low, model_high)
            & np.greater_equal(satellite_high, model_low)
        )
        interpolation_map[layers_do_not_intersect] = 0

        return interpolation_map

    def get_hprime_satellite_edges(self):
        """
        Equivalent to hprime in equation 11 of of Keppens et al. (2019).

        Creates n_satellite_edges+1 hprime levels with n_satellite_edges layers.

        We interpolate to these layers instead of the actual layers, which ensures we
        have full rank when we invert to satellite edges.
        """
        hprime_edges = np.full((self.n_obs, self.n_satellite_edges + 1), 0.0)
        hprime_edges[:, 1:-1] = 0.5 * (
            self.satellite_edges[:, :-1] + self.satellite_edges[:, 1:]
        )
        hprime_edges[:, 0] = self.satellite_edges[:, 0]
        hprime_edges[:, -1] = self.satellite_edges[:, -1]
        return hprime_edges

    def interpolate(self):
        """
        Interpolate GEOS-Chem methane to satellite edges OR centers.
        """
        expanded_model_edges = self.expand_model_to_satellite_range()

        if self.interpolate_to_centers_or_edges == "centers":
            interpolation_map = self.get_interpolation_map(
                model_edges=expanded_model_edges, satellite_edges=self.satellite_edges
            )
            partial_column_to_conc = 1 / np.abs(np.diff(self.satellite_edges))  # M_out*

        elif self.interpolate_to_centers_or_edges == "edges":
            hprime_satellite_edges = self.get_hprime_satellite_edges()
            interpolation_map = self.get_interpolation_map(
                model_edges=expanded_model_edges, satellite_edges=hprime_satellite_edges
            )  # interpolates model to hprime satellite layers
            partial_column_to_conc = 1 / np.abs(
                np.diff(hprime_satellite_edges)
            )  # M_out*

        else:
            raise ValueError(
                f"interpolate_to_centers_or_edges must be 'centers' or 'edges', not {self.interpolate_to_centers_or_edges}"
            )

        satellite_partial_columns = (
            interpolation_map * self.model_conc_at_layers[:, :, None]
        ).sum(
            axis=1
        )  # matrix multiplication across nobs model concentration vectors
        satellite_conc = partial_column_to_conc * satellite_partial_columns

        return satellite_conc
