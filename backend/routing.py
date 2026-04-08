"""
routing.py – Fetch alternative routes from the OSRM HTTP API and score them.

The OSRM public demo server (router.project-osrm.org) is used by default.
Set the environment variable OSRM_BASE_URL to point at a self-hosted instance.

OSRM route response reference:
  http://project-osrm.org/docs/v5.24.0/api/#route-service
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from frut_calculator import calculate_frut_idx, frut_score

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")

# Maximum number of alternative routes to request from OSRM.
MAX_ALTERNATIVES = 3

# Default curviness weight when scoring routes.
DEFAULT_WEIGHT = 1.0


# ---------------------------------------------------------------------------
# OSRM helpers
# ---------------------------------------------------------------------------


def _osrm_route_url(lon1: float, lat1: float, lon2: float, lat2: float) -> str:
    """Build the OSRM route URL for two coordinates."""
    return (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?alternatives={MAX_ALTERNATIVES}"
        f"&geometries=geojson"
        f"&overview=full"
        f"&steps=false"
    )


def _extract_coordinates(geometry: Dict[str, Any]) -> List[List[float]]:
    """Return [[lon, lat], ...] coordinate list from a GeoJSON LineString."""
    return geometry.get("coordinates", [])


def _osrm_coords_to_latlon(coords: List[List[float]]) -> List[tuple]:
    """Convert OSRM [lon, lat] pairs to (lat, lon) tuples used internally."""
    return [(c[1], c[0]) for c in coords]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch_routes(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    weight: float = DEFAULT_WEIGHT,
    osrm_client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """Fetch routes from OSRM, calculate frutidx and return scored routes.

    Parameters
    ----------
    start_lat, start_lon : float
        Start coordinates in decimal degrees.
    end_lat, end_lon : float
        End coordinates in decimal degrees.
    weight : float
        Curviness weight passed to :func:`frut_score`.
    osrm_client : httpx.AsyncClient, optional
        Inject a pre-configured client (useful for testing).

    Returns
    -------
    list of dict
        Routes sorted by descending frut_score.  Each dict contains:

        - ``geometry``       – GeoJSON LineString with the route geometry.
        - ``distance_m``     – Route distance in metres.
        - ``duration_s``     – Estimated travel time in seconds.
        - ``total_frut_idx`` – Sum of per-section frutidx values.
        - ``frut_score``     – Optimisation score (higher = more fun).
        - ``section_frut_idx`` – Per-section frutidx values.
    """
    url = _osrm_route_url(start_lon, start_lat, end_lon, end_lat)

    close_client = osrm_client is None
    if osrm_client is None:
        osrm_client = httpx.AsyncClient(timeout=15.0)

    try:
        response = await osrm_client.get(url)
        response.raise_for_status()
        data = response.json()
    finally:
        if close_client:
            await osrm_client.aclose()

    routes_raw = data.get("routes", [])

    results: List[Dict[str, Any]] = []
    for route in routes_raw:
        geometry = route.get("geometry", {})
        raw_coords = _extract_coordinates(geometry)
        latlon_coords = _osrm_coords_to_latlon(raw_coords)

        distance_m: float = route.get("distance", 0.0)
        duration_s: float = route.get("duration", 0.0)

        section_frut, total_frut = calculate_frut_idx(latlon_coords)
        score = frut_score(total_frut, distance_m, weight)

        results.append(
            {
                "geometry": geometry,
                "distance_m": distance_m,
                "duration_s": duration_s,
                "total_frut_idx": total_frut,
                "frut_score": score,
                "section_frut_idx": section_frut,
            }
        )

    # Sort by frut_score descending (most fun first).
    results.sort(key=lambda r: r["frut_score"], reverse=True)
    return results
