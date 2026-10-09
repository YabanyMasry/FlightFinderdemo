"""Orchestrator: wire region expansion -> phase1 -> phase2 and report results."""
from __future__ import annotations

import dataclasses
import logging

from .amadeus_client import AmadeusClient
from .cache import Cache
from .config import Settings, load_settings
from .mock_client import MockClient
from .models import Itinerary, SearchRequest
from .travelpayouts_client import TravelpayoutsClient
from . import phase1_scan, phase2_verify, regions

log = logging.getLogger("flightfinder")


@dataclasses.dataclass
class SearchOutcome:
    provider: str
    origins: list[str]
    destinations: list[str]
    candidate_count: int
    itineraries: list[Itinerary]


def make_client(settings: Settings, cache: Cache | None):
    """Provider factory — the single place that decides which provider to use."""
    if settings.provider == "mock":
        return MockClient(settings, cache=cache)
    if settings.provider == "travelpayouts":
        return TravelpayoutsClient(settings, cache=cache)
    return AmadeusClient(settings, cache=cache)


def run_search(
    req: SearchRequest,
    top_n: int = 15,
    date_pairs_per_candidate: int = 1,
    provider: str | None = None,
) -> SearchOutcome:
    settings = load_settings()
    if provider:  # per-request override (UI/CLI)
        settings = dataclasses.replace(settings, provider=provider.strip().lower())

    cache = Cache(settings.cache_path, settings.cache_ttl_hours)
    client = make_client(settings, cache)

    try:
        # 0. Expand region/city names into IATA codes.
        req.origins = regions.expand_terms(req.origins, client)
        req.destinations = regions.expand_terms(req.destinations, client)
        log.info("Provider: %s", settings.provider)
        log.info("Origins: %s", req.origins)
        log.info("Destinations: %s", req.destinations or "(discover anywhere)")

        # 1. Broad scan.
        candidates = phase1_scan.scan(client, req)

        # 2. Narrow verification.
        itineraries = phase2_verify.verify(
            client, req, candidates,
            top_n=top_n, date_pairs_per_candidate=date_pairs_per_candidate,
        ) if candidates else []

        return SearchOutcome(
            provider=settings.provider,
            origins=req.origins,
            destinations=req.destinations,
            candidate_count=len(candidates),
            itineraries=itineraries,
        )
    finally:
        cache.close()


def find_cheapest(
    req: SearchRequest,
    top_n: int = 15,
    date_pairs_per_candidate: int = 1,
    provider: str | None = None,
) -> list[Itinerary]:
    """Convenience wrapper returning just the ranked itineraries."""
    return run_search(req, top_n, date_pairs_per_candidate, provider).itineraries


def format_results(itineraries: list[Itinerary]) -> str:
    if not itineraries:
        return "No verified itineraries found."
    lines = ["", "=" * 64, "RANKED ITINERARIES (cheapest first)", "=" * 64]
    for i, it in enumerate(itineraries, 1):
        flag = "  <-- CHEAPEST" if i == 1 else ""
        stay = f"{it.stay_nights}n" if it.stay_nights is not None else "-"
        lines.append(
            f"{i:>2}. {it.price:>8.2f} {it.currency}  "
            f"{it.origin}->{it.destination}  "
            f"{it.departure_date} -> {it.return_date or 'one-way'}  "
            f"({stay}, {it.carrier or '??'}){flag}"
        )
    lines.append("=" * 64)
    return "\n".join(lines)
