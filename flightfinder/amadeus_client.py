"""Amadeus REST client: OAuth2 token management + rate-limit-friendly GET.

This is the only module that knows about Amadeus HTTP details. The phase modules
call the typed helper methods (flight_inspiration / flight_dates / flight_offers)
so a future provider swap is localized here.
"""
from __future__ import annotations

import logging
import time

import requests

from .cache import Cache
from .config import Settings
from .errors import ProviderAuthError, ProviderError

log = logging.getLogger("flightfinder.amadeus")


class AmadeusError(ProviderError):
    """Any Amadeus API failure (often just 'no data for this route' in the sandbox)."""


class AmadeusAuthError(AmadeusError, ProviderAuthError):
    """Missing credentials or rejected OAuth — fatal, should not be swallowed per-route."""


class AmadeusClient:
    def __init__(self, settings: Settings, cache: Cache | None = None):
        self.s = settings
        self.cache = cache
        self.session = requests.Session()
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._last_call: float = 0.0

    # ---- auth -----------------------------------------------------------
    def _token_valid(self) -> bool:
        return self._token is not None and time.time() < self._token_expiry - 30

    def _authenticate(self) -> None:
        if self._token_valid():
            return
        if not self.s.api_key or not self.s.api_secret:
            raise AmadeusAuthError(
                "Missing AMADEUS_API_KEY / AMADEUS_API_SECRET. Copy .env.example to "
                ".env and fill in your credentials, or use the mock provider "
                "(FF_PROVIDER=mock) to try the app with demo data."
            )
        url = f"{self.s.base_url}/v1/security/oauth2/token"
        log.info("Authenticating with Amadeus (%s)...", self.s.base_url)
        resp = self.session.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.s.api_key,
                "client_secret": self.s.api_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise AmadeusAuthError(f"Auth failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 1799))
        log.info("Authenticated; token valid for ~%ss", data.get("expires_in"))

    # ---- low-level GET with cache + throttle + retry --------------------
    def get(self, path: str, params: dict) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        url = f"{self.s.base_url}{path}"

        cache_key = None
        if self.cache:
            cache_key = Cache.make_key("GET", url, params)
            hit = self.cache.get(cache_key)
            if hit is not None:
                log.info("CACHE HIT  %s %s", path, _short(params))
                return hit

        self._authenticate()
        self._throttle()

        for attempt in range(1, 5):
            log.info("API  CALL  %s %s", path, _short(params))
            resp = self.session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30,
            )
            self._last_call = time.time()

            if resp.status_code == 200:
                body = resp.json()
                if self.cache and cache_key:
                    self.cache.set(cache_key, body)
                return body

            if resp.status_code == 429:  # rate limited -> exponential backoff
                wait = min(2 ** attempt, 16)
                log.warning("429 rate limited; backing off %ss (attempt %d)", wait, attempt)
                time.sleep(wait)
                continue

            if resp.status_code in (500, 503):  # transient server error
                wait = min(2 ** attempt, 16)
                log.warning("%d server error; retrying in %ss", resp.status_code, wait)
                time.sleep(wait)
                continue

            # 400/404 etc. are usually "no data for this query" in the sandbox.
            raise AmadeusError(f"GET {path} [{resp.status_code}]: {resp.text}")

        raise AmadeusError(f"GET {path} failed after retries (rate limit / server).")

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self.s.request_delay:
            time.sleep(self.s.request_delay - elapsed)

    # ---- typed endpoint helpers ----------------------------------------
    def flight_inspiration(
        self, origin: str, departure_date: str | None = None,
        duration: str | None = None, max_price: int | None = None,
    ) -> dict:
        """Flight Inspiration Search: one origin -> cheapest price to MANY destinations.
        `duration` may be "min,max" nights to constrain stay length.
        """
        return self.get(
            "/v1/shopping/flight-destinations",
            {"origin": origin, "departureDate": departure_date,
             "duration": duration, "maxPrice": max_price},
        )

    def flight_dates(
        self, origin: str, destination: str, departure_date: str | None = None,
        duration: str | None = None, non_stop: bool | None = None,
        max_price: int | None = None,
    ) -> dict:
        """Flight Cheapest Date Search: one route -> cheapest price across a DATE RANGE.
        `departure_date` may be "YYYY-MM-DD,YYYY-MM-DD" range; `duration` = "min,max".
        """
        return self.get(
            "/v1/shopping/flight-dates",
            {"origin": origin, "destination": destination,
             "departureDate": departure_date, "duration": duration,
             "nonStop": _bool(non_stop), "maxPrice": max_price},
        )

    def flight_offers(
        self, origin: str, destination: str, departure_date: str,
        return_date: str | None, adults: int = 1, currency: str = "EUR",
        non_stop: bool = False, max_results: int = 5,
    ) -> dict:
        """Flight Offers Search: real, bookable priced offers for an exact route+dates."""
        return self.get(
            "/v2/shopping/flight-offers",
            {"originLocationCode": origin, "destinationLocationCode": destination,
             "departureDate": departure_date, "returnDate": return_date,
             "adults": adults, "currencyCode": currency,
             "nonStop": _bool(non_stop), "max": max_results},
        )

    def search_locations(self, keyword: str, sub_type: str = "CITY,AIRPORT") -> dict:
        """Airport & City Search: expand a keyword (e.g. "London") into IATA codes."""
        return self.get(
            "/v1/reference-data/locations",
            {"keyword": keyword, "subType": sub_type, "page[limit]": 10},
        )


def _bool(v: bool | None):
    if v is None:
        return None
    return "true" if v else "false"


def _short(params: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in params.items())
