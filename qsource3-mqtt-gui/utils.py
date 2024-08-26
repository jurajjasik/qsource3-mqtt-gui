def verify_calib_points(calib_points):
    """
    Verify if the given calib_points is a list of number pairs.

    Parameters:
    calib_points (list): A list of number pairs in the format [[x1, y1], [x2, y2], ...]

    Raises:
    TypeError: If calib_points is not a list, or if any pair is not a list of length 2, or if any element in the pair is not a number.

    """
    if not isinstance(calib_points, list):
        raise TypeError("calib_points must be a list of number pairs.")
    for pair in calib_points:
        if not isinstance(pair, list) or len(pair) != 2:
            raise TypeError("calib_points must be a list of number pairs.")
        if not isinstance(pair[0], (int, float)) or not isinstance(
            pair[1], (int, float)
        ):
            raise TypeError("calib_points must be a list of number pairs.")


def check_mass_range(value):
    if value not in [0, 1, 2]:
        raise ValueError(f"Invalid mass_range value {value}. Must be 0, 1, or 2.")


def check_mz(value):
    if not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"Invalid mz value {value}. Must be a non-negative number.")


def check_dc_offset(value):
    if not isinstance(value, (int, float)):
        raise ValueError(f"Invalid dc_offset value {value}. Must be a number.")


def check_dc_on(value):
    if not isinstance(value, bool):
        raise ValueError(f"Invalid dc_on value {value}. Must be a boolean.")


def check_rod_polarity_positive(value):
    if not isinstance(value, bool):
        raise ValueError(
            f"Invalid rod_polarity_positive value {value}. Must be a boolean."
        )


def check_calib_points_mz(value):
    try:
        verify_calib_points(value)
    except TypeError as e:
        raise ValueError(f"Invalid calib_points_mz value {value}. {e}")


def check_calib_points_resolution(value):
    try:
        verify_calib_points(value)
    except TypeError as e:
        raise ValueError(f"Invalid calib_points_resolution value {value}. {e}")
