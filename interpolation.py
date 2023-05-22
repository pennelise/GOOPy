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

        assert (
            self.model_edges.shape[0] == self.satellite_edges.shape[0]
        ), f"GEOS-Chem and satellite must have the same number of observations. "
        f"GEOS-Chem nobs = {self.model_edges.shape[0]} "
        f"Satellite nobs = {self.satellite_edges.shape[0]} "

        assert np.all(
            np.diff(self.model_edges) < 0
        ), "GEOS-Chem pressure levels must be in descending order."
        assert np.all(
            np.diff(self.satellite_edges) < 0
        ), "Satellite pressure levels must be in descending order."

    def __get_interpolation_map(self):
        """
        Hannah's GC_to_sat_levels function
        equivalent to W * M_in in Keppens et al. (2019)
        """
        # # Define vectors that give the "low" and "high" pressure
        # # values for each GEOS-Chem and satellite layer.
        # GC_lo = GC_edges[:, 1:][:, :, None]
        # GC_hi = GC_edges[:, :-1][:, :, None]
        # sat_lo = sat_edges[:, 1:][:, None, :]
        # sat_hi = sat_edges[:, :-1][:, None, :]

        # # Get the indices where the GC-to-satellite mapping, which is
        # # a nobs x ngc x nsat matrix, is non-zero
        # idx = np.less_equal(sat_lo, GC_hi) & np.greater_equal(sat_hi, GC_lo)

        # # Find the fraction of each GC level that contributes to each
        # # TROPOMI level. We should first divide (to normalize) and then
        # # multiply (to apply the map to the column) by the GC pressure
        # # difference, but we exclude this (since it's the same as x1).
        # GC_to_sat = np.minimum(sat_hi, GC_hi) - np.maximum(sat_lo, GC_lo)
        # GC_to_sat[~idx] = 0

        # # Now map the GC CH4 to the satellite levels
        # GC_on_sat = (GC_to_sat * GC_CH4[:, :, None]).sum(axis=1)
        # GC_on_sat = GC_on_sat / GC_to_sat.sum(axis=1)
        return None

    def __centers_to_edges(self):
        """
        equivalent to M_out* in Keppens et al. (2019).
        Skip if you want result on layers/centers/partial columns.
        """
        return None

    # optional step if you have edges

    @staticmethod
    def __clip_model_to_satellite_range(model_edges, satellite_edges):
        """
        We want to account for the case when the GEOS-Chem surface
        is above the satellite surface (altitude wise) or the GEOS-Chem
        top is below the satellite top.. We do this by adjusting the
        GEOS-Chem surface pressure up to the TROPOMI surface pressure
        """
        # hannah's parallelized implementation
        # idx_bottom = np.less(GC_edges[:, 0], sat_edges[:, 0])
        # idx_top = np.greater(GC_edges[:, -1], sat_edges[:, -1])
        # GC_edges[idx_bottom, 0] = sat_edges[idx_bottom, 0]
        # GC_edges[idx_top, -1] = sat_edges[idx_top, -1]
        # return None

    def interpolate(self):
        model_edges = self.__clip_model_to_satellite_range(
            model_edges=self.model_edges, satellite_edges=self.satellite_edges
        )
        self.__get_interpolation_map()
        if self.interpolate_to_centers_or_edges == "centers":
            self.__centers_to_edges()
        return None
        # interpolate model to satellite grid
        # all observations at once (in chunks of 1 million?)
        # turns out neither of us use dry air for anything b/c it's neglibible

    def get_pressure_weight(self):
        return None
        # calculate pressure weight from GEOS-Chem (optional)
