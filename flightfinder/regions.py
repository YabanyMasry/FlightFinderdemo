"""Expand user-friendly region/city names into IATA codes.

Two strategies, in order:
1. A small static map for common shorthands (offline, zero API cost).
2. Amadeus Airport & City Search for anything else (one cheap reference call,
   cached like everything else).

Pass already-valid 3-letter IATA codes straight through.
"""
from __future__ import annotations

import logging
import re

from .amadeus_client import AmadeusClient

log = logging.getLogger("flightfinder.regions")

# Common shorthands -> representative IATA city/metro codes.
STATIC_REGIONS: dict[str, list[str]] = {
    "london": ["LON"],            # LON = all London airports (LHR/LGW/STN/LTN/...)
    "paris": ["PAR"],
    "new york": ["NYC"],
    "nyc": ["NYC"],
    "tokyo": ["TYO"],
    "milan": ["MIL"],
    "uk": ["LON", "MAN", "EDI", "BHX"],
    "spain": ["MAD", "BCN", "AGP", "VLC"],
    "italy": ["ROM", "MIL", "VCE", "NAP"],
    "germany": ["BER", "MUC", "FRA", "HAM"],
}

_IATA_RE = re.compile(r"^[A-Z]{3}$")


def expand_terms(terms: list[str], client: AmadeusClient | None = None) -> list[str]:
    """Turn a mixed list of IATA codes / city names / regions into unique IATA codes."""
    out: list[str] = []
    for term in terms:
        t = term.strip()
        if not t:
            continue
        if _IATA_RE.match(t.upper()) and t.upper() == t:
            out.append(t)  # already an explicit code like "LHR"
            continue
        key = t.lower()
        if key in STATIC_REGIONS:
            out.extend(STATIC_REGIONS[key])
            continue
        if client is not None:
            out.extend(_lookup_via_api(client, t))
        else:
            log.warning("No mapping for %r and no API client provided; skipping.", t)
    # de-dupe, preserve order
    seen, unique = set(), []
    for code in out:
        if code not in seen:
            seen.add(code)
            unique.append(code)
    return unique


def _lookup_via_api(client: AmadeusClient, keyword: str) -> list[str]:
    try:
        data = client.search_locations(keyword)
    except Exception as exc:  # noqa: BLE001 - reference lookup is best-effort
        log.warning("Location lookup failed for %r: %s", keyword, exc)
        return []
    codes = [d["iataCode"] for d in data.get("data", []) if d.get("iataCode")]
    if codes:
        log.info("Expanded %r -> %s", keyword, codes[:3])
    return codes[:3]  # cap: top few matches per keyword
