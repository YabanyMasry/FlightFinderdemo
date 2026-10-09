#!/usr/bin/env python3
"""CLI entry point for FlightFinder.

Examples
--------
# Known origins and destinations, 4-10 night stay, flexible Aug window:
python run_scan.py \
    --origins LON,MAD \
    --destinations BCN,ROM,LIS \
    --earliest 2026-08-01 --latest 2026-08-20 \
    --min-stay 4 --max-stay 10

# "Discover anywhere" from London (Phase 1 inspiration mode):
python run_scan.py --origins LON --earliest 2026-08-01 --latest 2026-08-20 \
    --min-stay 4 --max-stay 10
"""
from __future__ import annotations

import argparse
import logging
import sys

from flightfinder.main import find_cheapest, format_results
from flightfinder.models import SearchRequest


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Find the globally cheapest flight via a two-phase funnel.")
    p.add_argument("--origins", required=True,
                   help="Comma-separated IATA codes, cities, or regions (e.g. 'LON,MAD' or 'UK').")
    p.add_argument("--destinations", default="",
                   help="Comma-separated IATA codes/cities. Empty => discover anywhere.")
    p.add_argument("--earliest", required=True, help="Earliest departure date YYYY-MM-DD.")
    p.add_argument("--latest", required=True, help="Latest departure date YYYY-MM-DD.")
    p.add_argument("--min-stay", type=int, required=True, help="Minimum stay in nights.")
    p.add_argument("--max-stay", type=int, required=True, help="Maximum stay in nights.")
    p.add_argument("--adults", type=int, default=1)
    p.add_argument("--currency", default="EUR")
    p.add_argument("--non-stop", action="store_true", help="Non-stop flights only.")
    p.add_argument("--provider", choices=["travelpayouts", "amadeus", "mock"], default=None,
                   help="Override provider. 'mock' = offline demo data, no credentials needed.")
    p.add_argument("--top-n", type=int, default=15, help="How many Phase-1 leads to verify in Phase 2.")
    p.add_argument("--pairs-per-candidate", type=int, default=1,
                   help="How many date pairs to verify per candidate (more = more API calls).")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    req = SearchRequest(
        origins=[s for s in args.origins.split(",") if s.strip()],
        destinations=[s for s in args.destinations.split(",") if s.strip()],
        earliest_departure=args.earliest,
        latest_departure=args.latest,
        min_stay=args.min_stay,
        max_stay=args.max_stay,
        adults=args.adults,
        currency=args.currency,
        non_stop=args.non_stop,
    )

    try:
        itineraries = find_cheapest(
            req, top_n=args.top_n, date_pairs_per_candidate=args.pairs_per_candidate,
            provider=args.provider,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(format_results(itineraries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
