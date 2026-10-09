"""Phase 2 - narrow, expensive verification.

Take only the top-N Phase-1 candidates and run real Flight Offers Search on each.
For each candidate we generate valid (departure, return) date pairs that satisfy
the exact min/max stay window, but cap how many pairs we verify per candidate so
the funnel stays cheap.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from .errors import ProviderAuthError, ProviderError
from .models import Candidate, Itinerary, SearchRequest

log = logging.getLogger("flightfinder.phase2")


def verify(
    client,
    req: SearchRequest,
    candidates: list[Candidate],
    top_n: int = 15,
    date_pairs_per_candidate: int = 1,
) -> list[Itinerary]:
    """Verify the top_n candidates. Returns itineraries sorted cheapest-first."""
    shortlist = candidates[:top_n]
    log.info("Phase 2: verifying top %d of %d candidates.", len(shortlist), len(candidates))

    results: list[Itinerary] = []
    seen_pairs: set[tuple] = set()

    for i, c in enumerate(shortlist, 1):
        pairs = _date_pairs_for(c, req, date_pairs_per_candidate)
        for dep, ret in pairs:
            sig = (c.origin, c.destination, dep, ret)
            if sig in seen_pairs:
                continue
            seen_pairs.add(sig)

            log.info("Phase 2 [%d/%d] verify %s->%s %s..%s",
                     i, len(shortlist), c.origin, c.destination, dep, ret)
            try:
                data = client.flight_offers(
                    origin=c.origin, destination=c.destination,
                    departure_date=dep, return_date=ret,
                    adults=req.adults, currency=req.currency,
                    non_stop=req.non_stop, max_results=3,
                )
            except ProviderAuthError:
                raise  # fatal: surface credential problems instead of swallowing them
            except ProviderError as exc:
                log.warning("  no offers for %s->%s %s..%s (%s)",
                            c.origin, c.destination, dep, ret, exc)
                continue

            it = _cheapest_offer(data, c, dep, ret)
            if it:
                results.append(it)
                log.info("  verified %.2f %s", it.price, it.currency)

    results.sort(key=lambda x: x.price)
    log.info("Phase 2 complete: %d verified itineraries.", len(results))
    return results


def _date_pairs_for(c: Candidate, req: SearchRequest, limit: int) -> list[tuple[str, str | None]]:
    """Valid (dep, ret) pairs honoring the min/max stay window.

    Phase 1 already hands us a good (departure, return) suggestion. We start with
    that, then optionally widen to a few neighboring stay lengths up to `limit`.
    """
    dep_iso = c.departure_date
    if not dep_iso:
        return []
    try:
        dep = date.fromisoformat(dep_iso)
    except ValueError:
        return []

    # Round trip: build candidate returns from the stay window.
    pairs: list[tuple[str, str | None]] = []
    if c.return_date:
        pairs.append((dep_iso, c.return_date))

    for nights in range(req.min_stay, req.max_stay + 1):
        ret = (dep + timedelta(days=nights)).isoformat()
        pair = (dep_iso, ret)
        if pair not in pairs:
            pairs.append(pair)
        if len(pairs) >= limit:
            break

    return pairs[:limit] if limit else pairs


def _cheapest_offer(data, c: Candidate, dep: str, ret: str | None) -> Itinerary | None:
    offers = data.get("data", [])
    if not offers:
        return None
    best = min(offers, key=lambda o: float(o["price"]["grandTotal"]))
    carrier = ""
    try:
        carrier = best["itineraries"][0]["segments"][0]["carrierCode"]
    except (KeyError, IndexError):
        pass

    stay = None
    if ret:
        try:
            stay = (date.fromisoformat(ret) - date.fromisoformat(dep)).days
        except ValueError:
            stay = None

    return Itinerary(
        origin=c.origin,
        destination=c.destination,
        departure_date=dep,
        return_date=ret,
        price=float(best["price"]["grandTotal"]),
        currency=best["price"].get("currency", c.currency),
        stay_nights=stay,
        carrier=carrier,
        raw=best,
    )
