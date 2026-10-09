# FlightFinder

Find the **globally cheapest flight** across a large search space
(one departure × many arrivals × departure dates × return dates)
**without brute-forcing** every priced API call.

It uses a **two-phase funnel** behind a **swappable provider interface**:

| Phase | What it does | Cost |
|-------|--------------|------|
| **1. Broad scan** | Bulk "explore" endpoints scan the whole destination × date space in few calls; rank rough candidates by price. | cheap |
| **2. Narrow verify** | Re-price only the top-N candidates, honoring exact min/max stay; return the verified cheapest. | expensive |

## Providers

Choose with `FF_PROVIDER` (or the dropdown in the UI / `--provider` on the CLI):

| Provider | Free? | Data | Notes |
|----------|-------|------|-------|
| **`travelpayouts`** | ✅ free (affiliate token) | cached prices | **Recommended.** `prices/cheap` (cheapest round trip per route per month) drives both phases; `city-directions` discovers destinations for "anywhere", then re-queried through the constrained path. |
| **`mock`** | ✅ no signup | deterministic demo | Runs the whole funnel + UI offline. Great for development. |
| **`amadeus`** | ⚠️ deprecated | live | **Self-service portal decommissions 2026-07-17** — existing keys stop working; new signups paused. Kept for reference only. |

> Adding another provider = one new module exposing `flight_inspiration` /
> `flight_dates` / `flight_offers` / `search_locations` that returns the shared
> dict shapes. Nothing else changes.

## Quick start (mock — zero setup)

```bash
python -m venv .venv
.venv\Scripts\activate            # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

python app.py                      # open http://127.0.0.1:8000  (UI defaults to Mock)
```

In the UI: type a **departure** city (autocomplete → pick one), type **destinations**
and pick to add chips (or leave blank to *discover anywhere*), set dates + stay,
hit **Search cheapest**.

## Using real data (Travelpayouts)

1. Sign up at <https://www.travelpayouts.com/developers/api> and create an **API token** (free).
2. `cp .env.example .env` and set:
   ```
   FF_PROVIDER=travelpayouts
   TRAVELPAYOUTS_TOKEN=your_token_here
   ```
3. Restart `python app.py` and pick **Travelpayouts** in the provider dropdown.

Travelpayouts prices are *cached* (not live-bookable), so Phase 2 returns the best
cached price for the exact dates rather than a live re-quote — fine for "find the
cheapest", and it keeps the whole funnel free.

## CLI

```bash
# Mock (no keys):
python run_scan.py --provider mock --origins LON --destinations BCN,ROM,LIS \
    --earliest 2026-08-01 --latest 2026-08-20 --min-stay 4 --max-stay 10

# Discover anywhere (Phase 1 inspiration mode): omit --destinations
python run_scan.py --provider mock --origins LON \
    --earliest 2026-08-01 --latest 2026-08-20 --min-stay 4 --max-stay 10
```

## HTTP API

- `GET  /`               — web UI
- `GET  /api/locations?q=lon` — airport/city autocomplete (bundled, offline)
- `GET  /api/health`     — provider + whether credentials are present
- `POST /api/search`     — run the funnel, returns ranked JSON

## Project layout

```
flightfinder/
  config.py             # env / .env settings (provider selection)
  errors.py             # provider-neutral ProviderError / ProviderAuthError
  models.py             # SearchRequest, Candidate, Itinerary  (shared shapes)
  cache.py              # SQLite response cache (TTL)
  airports.py           # bundled airport dataset for autocomplete / region expansion
  regions.py            # expand city/region names -> IATA codes
  amadeus_client.py     # provider: Amadeus (deprecated)
  travelpayouts_client.py # provider: Travelpayouts/Aviasales  <- default real provider
  mock_client.py        # provider: offline demo data
  phase1_scan.py        # broad scan -> ranked Candidates
  phase2_verify.py      # verify top-N -> priced Itineraries
  main.py               # provider factory + orchestrator + formatting
app.py                  # FastAPI backend + static UI
static/index.html       # single-page UI (autocomplete, chips, results)
run_scan.py             # CLI
```

## Tuning (cost vs. coverage)

- `--top-n` — how many Phase-1 leads get verified (default 15).
- `--pairs-per-candidate` — date pairs verified per candidate (default 1).
- `FF_REQUEST_DELAY` — seconds between calls; raise if you hit rate limits.
- `FF_CACHE_TTL_HOURS` — repeated scans within this window reuse cached responses.
