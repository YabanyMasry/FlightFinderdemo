"""Provider-neutral error hierarchy.

The phase modules catch these, not provider-specific classes, so any provider
(Amadeus, Travelpayouts, mock, …) can signal "no data" vs. "fatal auth problem"
the same way.
"""
from __future__ import annotations


class ProviderError(RuntimeError):
    """Any provider/API failure — often just 'no data for this route/date'."""


class ProviderAuthError(ProviderError):
    """Missing or rejected credentials — fatal; must not be swallowed per-route."""
