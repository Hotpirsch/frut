"""
frut_calculator.py – Core logic for computing the FRUT index.

The FRUT index (frutidx) measures "driving fun" by counting and weighting
the corners in a route.  A higher frutidx means more curves / sharper turns.

Algorithm
---------
1.  For every consecutive pair of route *sections* (polyline segments) compute
    the **absolute bearing difference** (0–180 °).
2.  The **frutidx of a section** is the *average* of the bearing differences to
    its leading section and its following section.
    - The first section only has a following section → its frutidx equals that
      single bearing difference.
    - The last section only has a leading section → its frutidx equals that
      single bearing difference.

Terminology
-----------
- *coordinate* : (latitude, longitude) tuple, decimal degrees.
- *section*    : the straight line between two consecutive coordinates.
- *bearing*    : direction of travel along a section, in degrees [0, 360).
"""

from __future__ import annotations

import math
from typing import List, Tuple

Coordinate = Tuple[float, float]  # (lat, lon)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the initial bearing (forward azimuth) from point 1 to point 2.

    The result is in degrees on the range [0, 360).
    """
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlon_r = math.radians(lon2 - lon1)

    x = math.sin(dlon_r) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360.0) % 360.0


def absolute_bearing_difference(b1: float, b2: float) -> float:
    """Return the smallest absolute angular difference between two bearings.

    The result is in degrees on the range [0, 180].
    """
    diff = abs(b1 - b2) % 360.0
    return min(diff, 360.0 - diff)


# ---------------------------------------------------------------------------
# Section (segment) helpers
# ---------------------------------------------------------------------------


def section_bearings(coordinates: List[Coordinate]) -> List[float]:
    """Return the bearing for each section (consecutive coordinate pair)."""
    bearings: List[float] = []
    for i in range(len(coordinates) - 1):
        lat1, lon1 = coordinates[i]
        lat2, lon2 = coordinates[i + 1]
        # Skip degenerate sections (same point)
        if (lat1, lon1) == (lat2, lon2):
            bearings.append(bearings[-1] if bearings else 0.0)
        else:
            bearings.append(calculate_bearing(lat1, lon1, lat2, lon2))
    return bearings


def adjacent_bearing_differences(bearings: List[float]) -> List[float]:
    """Return the absolute bearing difference for each adjacent section pair.

    ``diffs[i]`` is the bearing difference between section *i* and section *i+1*.
    The resulting list has ``len(bearings) - 1`` elements.
    """
    return [
        absolute_bearing_difference(bearings[i], bearings[i + 1])
        for i in range(len(bearings) - 1)
    ]


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------


def calculate_frut_idx(coordinates: List[Coordinate]) -> Tuple[List[float], float]:
    """Compute the frutidx for every section and the total frutidx of a route.

    Parameters
    ----------
    coordinates:
        Ordered list of ``(lat, lon)`` waypoints that define the route.
        At least two coordinates are required to form a section.

    Returns
    -------
    section_frut_idx:
        A list of frutidx values, one per section (len = len(coordinates) - 1).
    total_frut_idx:
        The sum of all per-section frutidx values.  Use this to compare routes.
    """
    num_coords = len(coordinates)

    if num_coords < 2:
        return [], 0.0

    if num_coords == 2:
        # Single section → no adjacent sections → no bearing differences.
        return [0.0], 0.0

    bearings = section_bearings(coordinates)
    n = len(bearings)  # == num_coords - 1 == number of sections

    diffs = adjacent_bearing_differences(bearings)  # len == n - 1

    section_frut: List[float] = []
    for i in range(n):
        if n == 1:
            section_frut.append(0.0)
        elif i == 0:
            # Only a following difference is available.
            section_frut.append(diffs[0])
        elif i == n - 1:
            # Only a leading difference is available.
            section_frut.append(diffs[-1])
        else:
            # Average of leading and following bearing differences.
            section_frut.append((diffs[i - 1] + diffs[i]) / 2.0)

    total = sum(section_frut)
    return section_frut, total


def frut_score(total_frut_idx: float, distance_m: float, weight: float = 1.0) -> float:
    """Combine frutidx and distance into a single optimisation score.

    A higher score is *better* (more fun per metre).

    Parameters
    ----------
    total_frut_idx:
        Sum of per-section frutidx values for the route.
    distance_m:
        Route length in metres.
    weight:
        Relative importance of curviness vs. distance (default 1.0).
        Increasing this value favours curvier routes even if they are longer.
    """
    if distance_m <= 0:
        return 0.0
    # Normalise to "degrees of curvature per kilometre" then scale by weight.
    return weight * (total_frut_idx / (distance_m / 1000.0))
