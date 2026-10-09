"""Shared data structures passed between phases.

Provider-neutral on purpose: phase1 emits Candidates, phase2 consumes them and
emits Itineraries. Swapping Amadeus for another provider only means re-implementing
the scan/verify functions to produce these same shapes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SearchRequest:
    """Everything the user asked for."""
    origins: list[str]              # IATA codes, e.g. ["LON", "MAD"]
    destinations: list[str]         # IATA codes; empty => "discover anywhere" (Phase 1 inspiration)
    earliest_departure: str         # "YYYY-MM-DD"
    latest_departure: str           # "YYYY-MM-DD"
    min_stay: int                   # nights
    max_stay: int                   # nights
    adults: int = 1
    currency: str = "EUR"
    non_stop: bool = False


@dataclass
class Candidate:
    """A rough, Phase-1 lead worth verifying. Price is approximate."""
    origin: str
    destination: str
    departure_date: str             # "YYYY-MM-DD"
    return_date: Optional[str]      # "YYYY-MM-DD" (round trip)
    approx_price: float
    currency: str
    source: str                     # which phase-1 endpoint produced it

    def key(self) -> tuple:
        return (self.origin, self.destination, self.departure_date, self.return_date)


@dataclass
class Itinerary:
    """A verified, Phase-2 priced result."""
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str]
    price: float
    currency: str
    stay_nights: Optional[int]
    carrier: str = ""
    raw: dict = field(default_factory=dict)   # full offer for later inspection
