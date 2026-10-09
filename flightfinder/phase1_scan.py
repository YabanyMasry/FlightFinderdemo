"""Phase 1 - broad, cheap scan.

Goal: cover the whole origin x destination x date space in as FEW priced calls as
possible, producing rough Candidates ranked by approximate price.

Two modes, chosen automatically:
  * destinations given  -> Flight Cheapest Date Search per (origin x destination):
                           O(origins x destinations) calls, each covering the
                           entire date range + stay-length window at once.
  * destinations empty  -> Flight Inspiration Search per origin: O(origins) calls,
                           each returning the cheapest destinations from that origin.
"""
from __future__ import annotations

import logging

from .errors import ProviderAuthError, ProviderError
from .models import Candidate, SearchRequest

log = logging.getLogger("flightfinder.phase1")


def scan(client, req: SearchRequest) -> list[Candidate]:
    duration = f"{req.min_stay},{req.max_stay}"
    date_range = f"{req.earliest_departure},{req.latest_departure}"

    if req.destinations:
        candidates = _scan_known_routes(client, req, duration, date_range)
    else:
        candidates = _scan_inspiration(client, req, duration)

    candidates.sort(key=lambda c: c.approx_price)
    log.info("Phase 1 complete: %d candidates found.", len(candidates))
    for i, c in enumerate(candidates[:10], 1):
        log.info("  #%d  %s->%s  %s..%s  ~%.0f %s",
                 i, c.origin, c.destination, c.departure_date,
                 c.return_date, c.approx_price, c.currency)
    return candidates


def _scan_known_routes(client, req, duration, date_range) -> list[Candidate]:
    out: list[Candidate] = []
    total = len(req.origins) * len(req.destinations)
    n = 0
    for origin in req.origins:
        for dest in req.destinations:
            n += 1
            if origin == dest:
                continue
            log.info("Phase 1 [%d/%d] cheapest-dates %s->%s", n, total, origin, dest)
            try:
                data = client.flight_dates(
                    origin=origin, destination=dest,
                    departure_date=date_range, duration=duration,
                    non_stop=req.non_stop,
                )
            except ProviderAuthError:
                raise  # fatal: don't mistake bad credentials for "no data"
            except ProviderError as exc:
                log.warning("  no data for %s->%s (%s)", origin, dest, exc)
                continue
            out.extend(_parse_flight_dates(data, origin, dest, req.currency))
    return out


def _scan_inspiration(client, req, duration) -> list[Candidate]:
    out: list[Candidate] = []
    for i, origin in enumerate(req.origins, 1):
        log.info("Phase 1 [%d/%d] inspiration from %s", i, len(req.origins), origin)
        try:
            data = client.flight_inspiration(
                origin=origin,
                # date range "earliest,latest" — providers that can honor it (mock,
                # travelpayouts) constrain results; Amadeus accepts a range too.
                departure_date=f"{req.earliest_departure},{req.latest_departure}",
                duration=duration,
            )
        except ProviderAuthError:
            raise  # fatal: surface credential problems instead of swallowing them
        except ProviderError as exc:
            log.warning("  no inspiration data from %s (%s)", origin, exc)
            continue
        out.extend(_parse_inspiration(data, origin, req.currency))
    return out


def _parse_flight_dates(data, origin, dest, currency) -> list[Candidate]:
    out = []
    for item in data.get("data", []):
        price = _price(item)
        if price is None:
            continue
        out.append(Candidate(
            origin=item.get("origin", origin),
            destination=item.get("destination", dest),
            departure_date=item.get("departureDate", ""),
            return_date=item.get("returnDate"),
            approx_price=price,
            currency=data.get("meta", {}).get("currency", currency),
            source="flight_dates",
        ))
    return out


def _parse_inspiration(data, origin, currency) -> list[Candidate]:
    out = []
    for item in data.get("data", []):
        price = _price(item)
        if price is None:
            continue
        out.append(Candidate(
            origin=item.get("origin", origin),
            destination=item.get("destination", ""),
            departure_date=item.get("departureDate", ""),
            return_date=item.get("returnDate"),
            approx_price=price,
            currency=data.get("meta", {}).get("currency", currency),
            source="flight_inspiration",
        ))
    return out


def _price(item) -> float | None:
    p = item.get("price", {})
    val = p.get("total") or p.get("grandTotal")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None
