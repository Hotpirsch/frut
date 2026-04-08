"""
app.py – FastAPI application exposing the frut route optimisation API.

Endpoints
---------
GET /api/routes
    Query parameters:
      - start_lat  (float, required)
      - start_lon  (float, required)
      - end_lat    (float, required)
      - end_lon    (float, required)
      - weight     (float, optional, default 1.0)

    Returns a JSON array of routes, sorted by frut_score descending.

GET /health
    Simple liveness probe.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from mangum import Mangum

from routing import fetch_routes

app = FastAPI(
    title="frut – Fun Route Optimizer",
    description=(
        "Find the most enjoyable driving route between two locations "
        "by combining shortest-path routing with a curviness index (frutidx)."
    ),
    version="1.0.0",
)

# Allow the frontend (served from a different origin) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> Dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/api/routes", response_model=List[Dict[str, Any]])
async def get_routes(
    start_lat: float = Query(..., description="Start latitude in decimal degrees"),
    start_lon: float = Query(..., description="Start longitude in decimal degrees"),
    end_lat: float = Query(..., description="End latitude in decimal degrees"),
    end_lon: float = Query(..., description="End longitude in decimal degrees"),
    weight: float = Query(
        1.0,
        ge=0.0,
        description=(
            "Curviness weight (≥ 0). Higher values favour curvy routes "
            "even when they are longer."
        ),
    ),
) -> List[Dict[str, Any]]:
    """Return alternative routes scored by distance and curviness (frutidx)."""
    for name, value in (
        ("start_lat", start_lat),
        ("end_lat", end_lat),
    ):
        if not (-90.0 <= value <= 90.0):
            raise HTTPException(
                status_code=422,
                detail=f"{name} must be between -90 and 90, got {value}",
            )
    for name, value in (
        ("start_lon", start_lon),
        ("end_lon", end_lon),
    ):
        if not (-180.0 <= value <= 180.0):
            raise HTTPException(
                status_code=422,
                detail=f"{name} must be between -180 and 180, got {value}",
            )

    try:
        routes = await fetch_routes(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            weight=weight,
        )
    except Exception as exc:  # pragma: no cover – network errors
        raise HTTPException(
            status_code=502,
            detail=f"Routing service error: {exc}",
        ) from exc

    return routes


# AWS Lambda handler (Mangum wraps the ASGI app).
handler = Mangum(app, lifespan="off")
