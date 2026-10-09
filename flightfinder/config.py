"""Configuration loaded from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional; env vars may be set another way
    pass


@dataclass(frozen=True)
class Settings:
    provider: str            # "travelpayouts" | "amadeus" | "mock"
    api_key: str
    api_secret: str
    base_url: str
    travelpayouts_token: str
    travelpayouts_base_url: str
    request_delay: float
    cache_ttl_hours: int
    cache_path: str


def load_settings() -> Settings:
    """Load settings. Credentials are NOT required up front; the Amadeus client
    validates them only when it actually authenticates, so the mock provider can
    run with no .env at all."""
    return Settings(
        provider=os.getenv("FF_PROVIDER", "amadeus").strip().lower(),
        api_key=os.getenv("AMADEUS_API_KEY", "").strip(),
        api_secret=os.getenv("AMADEUS_API_SECRET", "").strip(),
        base_url=os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com").rstrip("/"),
        travelpayouts_token=os.getenv("TRAVELPAYOUTS_TOKEN", "").strip(),
        travelpayouts_base_url=os.getenv(
            "TRAVELPAYOUTS_BASE_URL", "https://api.travelpayouts.com").rstrip("/"),
        request_delay=float(os.getenv("FF_REQUEST_DELAY", "0.25")),
        cache_ttl_hours=int(os.getenv("FF_CACHE_TTL_HOURS", "3")),
        cache_path=os.getenv("FF_CACHE_PATH", "cache.sqlite"),
    )
