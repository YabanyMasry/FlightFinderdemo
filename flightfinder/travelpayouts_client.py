"""Travelpayouts (Aviasales) Data API provider — free replacement for Amadeus.

Mirrors the typed helpers the phase modules call (flight_inspiration /
flight_dates / flight_offers / search_locations) and ADAPTS Travelpayouts JSON
into the same Amadeus-shaped dicts, so phase1_scan and phase2_verify need no
changes. Endpoint mapping:

  flight_dates      -> /v1/prices/cheap  (cheapest round trip per month, real dates)
  flight_inspiration-> /v1/city-directions (cheapest from a city to anywhere)
  flight_offers     -> /v1/prices/cheap  (re-read & price the exact candidate date)

Note: month-matrix returns one-way fares (empty return_date) and calendar returns a
sparse rolling window, so prices/cheap (cheapest round trip per route per month) is
the reliable backbone for both phases here.

Note: Travelpayouts prices are *cached* (not live-bookable). Phase 2 therefore
returns the best cached price for the exact dates rather than a live re-quote.
Get a free token at https://www.travelpayouts.com/developers/api.
"""
from __future__ import annotations

import logging
import time
from datetime import date

import requests

from .cache import Cache
from .config import Settings
from .errors import ProviderAuthError, ProviderError
from . import airports

log = logging.getLogger("flightfinder.travelpayouts")

DEFAULT_CURRENCY = "eur"  # Travelpayouts expects lowercase currency codes


class TravelpayoutsClient:
    def __init__(self, settings: Settings, cache: Cache | None = None):
        self.s = settings
        self.cache = cache
        self.session = requests.Session()
        self._last_call = 0.0

    # ---- low-level GET: cache + throttle + retry ------------------------
    def _get(self, path: str, params: dict) -> dict:
        if not self.s.travelpayouts_token:
            raise ProviderAuthError(
                "Missing TRAVELPAYOUTS_TOKEN. Get a free token at "
                "https://www.travelpayouts.com/developers/api and set it in .env, "
                "or use FF_PROVIDER=mock for offline demo data."
            )
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{self.s.travelpayouts_base_url}{path}"

        cache_key = None
        if self.cache:
            cache_key = Cache.make_key("GET", url, params)  # token deliberately excluded
            hit = self.cache.get(cache_key)
            if hit is not None:
                log.info("CACHE HIT  %s %s", path, _short(params))
                return hit

        self._throttle()
        for attempt in range(1, 5):
            log.info("API  CALL  %s %s", path, _short(params))
            resp = self.session.get(
                url, params=params,
                headers={"X-Access-Token": self.s.travelpayouts_token,
                         "Accept": "application/json"},
                timeout=30,
            )
            self._last_call = time.time()

            if resp.status_code == 200:
                body = resp.json()
                if not body.get("success", True):
                    raise ProviderError(f"{path}: API error {body.get('error')}")
                if self.cache and cache_key:
                    self.cache.set(cache_key, body)
                return body
            if resp.status_code in (401, 403):
                raise ProviderAuthError(
                    f"Travelpayouts auth failed [{resp.status_code}] — check TRAVELPAYOUTS_TOKEN."
                )
            if resp.status_code == 429:
                wait = min(2 ** attempt, 16)
                log.warning("429 rate limited; backing off %ss (attempt %d)", wait, attempt)
                time.sleep(wait)
                continue
            if resp.status_code in (500, 503):
                wait = min(2 ** attempt, 16)
                log.warning("%d server error; retrying in %ss", resp.status_code, wait)
                time.sleep(wait)
                continue
            raise ProviderError(f"GET {path} [{resp.status_code}]: {resp.text[:200]}")

        raise ProviderError(f"GET {path} failed after retries.")

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self.s.request_delay:
            time.sleep(self.s.request_delay - elapsed)

    # ---- typed helpers (Amadeus-shaped output) --------------------------
    def flight_dates(self, origin, destination, departure_date=None, duration=None,
                     non_stop=None, max_price=None):
        """Cheapest round trip per month for a route, filtered to range + stay window.

        /v1/prices/cheap returns the cheapest round trip (by number of stops, keyed
        "0"/"1"/"2") departing in a given month, with real depart/return dates.
        """
        earliest, latest = _split_range(departure_date)
        min_stay, max_stay = _split_duration(duration)
        rows: list[dict] = []
        for month in _months_between(earliest, latest):
            body = self._get("/v1/prices/cheap", {
                "origin": origin, "destination": destination,
                "depart_date": month[:7], "currency": DEFAULT_CURRENCY,
            })
            dest_map = body.get("data", {}).get(destination, {})
            for stops, item in dest_map.items():
                if non_stop and stops != "0":   # key "0" == non-stop
                    continue
                dep = _date(item.get("departure_at"))
                ret = _date(item.get("return_at"))
                price = item.get("price")
                if dep is None or ret is None or price is None:
                    continue
                if (earliest and dep < earliest) or (latest and dep > latest):
                    continue
                if not (min_stay <= (ret - dep).days <= max_stay):
                    continue
                rows.append({
                    "origin": origin, "destination": destination,
                    "departureDate": dep.isoformat(), "returnDate": ret.isoformat(),
                    "price": {"total": str(price)},
                })
        return {"data": rows, "meta": {"currency": DEFAULT_CURRENCY}}

    INSPIRATION_FANOUT = 10  # how many discovered destinations to constrain-check

    def flight_inspiration(self, origin, departure_date=None, duration=None, max_price=None):
        """Discover-anywhere: city-directions finds the cheapest destinations, then we
        re-query the top ones through flight_dates so results honor the caller's date
        range + stay window (city-directions alone returns arbitrary uncached dates)."""
        body = self._get("/v1/city-directions", {"origin": origin, "currency": DEFAULT_CURRENCY})
        by_price = sorted(
            ((d, it) for d, it in body.get("data", {}).items() if it.get("price") is not None),
            key=lambda kv: kv[1]["price"],
        )
        rows: list[dict] = []
        for dest, _ in by_price[: self.INSPIRATION_FANOUT]:
            sub = self.flight_dates(origin, dest, departure_date=departure_date, duration=duration)
            rows.extend(sub.get("data", []))
        return {"data": rows, "meta": {"currency": DEFAULT_CURRENCY}}

    def flight_offers(self, origin, destination, departure_date, return_date,
                      adults=1, currency="EUR", non_stop=False, max_results=5):
        """Phase-2 verify: re-read the cheapest round trip for the candidate's month
        and price the exact departure date (full-date queries return no cached data,
        so we query by month and match the day, falling back to the month's cheapest).
        """
        cur = (currency or DEFAULT_CURRENCY).lower()
        body = self._get("/v1/prices/cheap", {
            "origin": origin, "destination": destination,
            "depart_date": (departure_date or "")[:7], "currency": cur,
        })
        dest_map = body.get("data", {}).get(destination, {})
        exact = cheapest = None
        for stops, item in dest_map.items():
            if non_stop and stops != "0":
                continue
            price = item.get("price")
            if price is None:
                continue
            if cheapest is None or price < cheapest["price"]:
                cheapest = item
            if (item.get("departure_at") or "")[:10] == departure_date:
                exact = item
        chosen = exact or cheapest
        if chosen is None:
            return {"data": []}
        return {"data": [{
            "price": {"grandTotal": f"{float(chosen['price']) * adults:.2f}", "currency": cur},
            "itineraries": [{"segments": [{"carrierCode": chosen.get("airline", "")}]}],
        }]}

    def search_locations(self, keyword, sub_type="CITY,AIRPORT"):
        """Resolve a city/region keyword to IATA codes using the bundled dataset."""
        return {"data": [{"iataCode": a["iata"]} for a in airports.search(keyword, limit=3)]}


# ---- helpers ------------------------------------------------------------
def _date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _split_range(s):
    if not s:
        return None, None
    if "," in s:
        a, b = s.split(",", 1)
        return _date(a), _date(b)
    d = _date(s)
    return d, d


def _split_duration(s):
    if s and "," in s:
        try:
            a, b = s.split(",", 1)
            return int(a), int(b)
        except ValueError:
            pass
    return 0, 3650


def _months_between(start, end):
    """First-of-month markers from start's month through end's month (inclusive)."""
    if start is None:
        start = date.today()
    if end is None:
        end = start
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month) and len(out) <= 13:
        out.append(f"{y:04d}-{m:02d}-01")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def _short(params: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in params.items())
