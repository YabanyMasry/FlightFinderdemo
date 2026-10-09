#!/usr/bin/env python3
"""FastAPI backend + static UI for FlightFinder.

Run:
    python app.py
    # or: uvicorn app:app --reload
Then open http://127.0.0.1:8000
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from flightfinder import airports
from flightfinder.errors import ProviderError
from flightfinder.config import load_settings
from flightfinder.main import run_search
from flightfinder.models import SearchRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

STATIC_DIR = Path(__file__).parent / "static"
app = FastAPI(title="FlightFinder", version="0.1.0")


class SearchBody(BaseModel):
    origin: str = Field(..., examples=["LON"])           # single departure
    destinations: str = Field("", examples=["BCN,ROM,LIS"])
    earliest: str = Field(..., examples=["2026-08-01"])
    latest: str = Field(..., examples=["2026-08-20"])
    min_stay: int = Field(..., ge=0)
    max_stay: int = Field(..., ge=0)
    adults: int = Field(1, ge=1, le=9)
    currency: str = "EUR"
    non_stop: bool = False
    top_n: int = Field(15, ge=1, le=50)
    pairs_per_candidate: int = Field(1, ge=1, le=10)
    provider: str = Field("mock", pattern="^(travelpayouts|amadeus|mock)$")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/locations")
def locations(q: str = "", limit: int = 8):
    """Typeahead source for the UI: match cities/airports to IATA codes (bundled, offline)."""
    results = airports.search(q, limit=limit)
    return [
        {"iata": a["iata"], "city": a["city"], "name": a["name"], "country": a["country"]}
        for a in results
    ]


@app.get("/api/health")
def health():
    s = load_settings()
    return {
        "status": "ok",
        "default_provider": s.provider,
        "amadeus_credentials_present": bool(s.api_key and s.api_secret),
    }


@app.post("/api/search")
def search(body: SearchBody):
    if body.min_stay > body.max_stay:
        return JSONResponse(status_code=400, content={"error": "min_stay cannot exceed max_stay."})
    if body.earliest > body.latest:
        return JSONResponse(status_code=400, content={"error": "earliest date is after latest date."})
    if not body.origin.strip():
        return JSONResponse(status_code=400, content={"error": "A departure location is required."})

    req = SearchRequest(
        origins=[body.origin.strip()],
        destinations=[s for s in body.destinations.split(",") if s.strip()],
        earliest_departure=body.earliest,
        latest_departure=body.latest,
        min_stay=body.min_stay,
        max_stay=body.max_stay,
        adults=body.adults,
        currency=body.currency,
        non_stop=body.non_stop,
    )

    try:
        # Force mock provider for Vercel deployment demo
        body.provider = "mock"
        outcome = run_search(
            req, top_n=body.top_n,
            date_pairs_per_candidate=body.pairs_per_candidate,
            provider=body.provider,
        )
    except ProviderError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:  # noqa: BLE001 - surface any provider error to the UI
        logging.exception("search failed")
        return JSONResponse(status_code=500, content={"error": str(exc)})

    items = [
        {
            "rank": i,
            "cheapest": i == 1,
            "origin": it.origin,
            "destination": it.destination,
            "departure_date": it.departure_date,
            "return_date": it.return_date,
            "stay_nights": it.stay_nights,
            "price": it.price,
            "currency": it.currency,
            "carrier": it.carrier,
        }
        for i, it in enumerate(outcome.itineraries, 1)
    ]
    return {
        "provider": outcome.provider,
        "origins": outcome.origins,
        "destinations": outcome.destinations,
        "candidate_count": outcome.candidate_count,
        "verified_count": len(items),
        "itineraries": items,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
