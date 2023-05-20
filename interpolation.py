class VerticalGrid:
    """
    Can be used independently to interpolate, or used inside functions 
    in operators.py. 
    """
    def __init__(self, gc_df, satellite_levels, centers_or_edges):
        # set satellite edges or centers
        self.__check_input_structure()
        # dim(satellite_levels) = nobs x nlevels

    def __check_input_structure(self):
        # check format for inputs are acceptable (e.g. levels are in ascending order)
        pass

    def __get_interpolation_map(self):
        return None
        # Hannah's GC_to_sat_levels function

    def __centers_to_edges(self):
        return None
        # extra step not needed in all cases

    def __handle_edge_cases(self):
        return None
        # handle edge cases (e.g. extrapolation)

    def interpolate(self):
        self.__get_interpolation_map()
        self.__centers_to_edges()
        self.__handle_edge_cases()
        return None
        # interpolate model to satellite grid
        # all observations at once (in chunks of 1 million?)
        # I plan to use dry air if it's not too cumbersome

    def get_pressure_weight(self):
        return None
        # calculate pressure weight from GEOS-Chem (optional)
