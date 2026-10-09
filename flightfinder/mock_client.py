"""Offline mock provider — drop-in for AmadeusClient.

Returns Amadeus-shaped JSON with deterministic, plausible prices so the entire
two-phase funnel + UI can run with NO credentials and NO network. Prices are seeded
from the route/dates, so results are stable across runs (and the "cheapest" is
reproducible). Phase-2 offers deliberately differ slightly from Phase-1 estimates
to demonstrate why verification matters.
"""
from __future__ import annotations

import hashlib
import logging
import random
import time
from datetime import date, timedelta

log = logging.getLogger("flightfinder.mock")

_INSPIRATION_POOL = [
    # Europe
    "BCN", "ROM", "LIS", "ATH", "PRG", "BUD", "OPO", "VIE",
    "CPH", "DUB", "AMS", "MXP", "FCO", "NCE", "PMI", "TFS",
    "MAD", "BER", "CDG", "LHR", "FRA", "MUC", "ZRH", "GVA",
    "WAW", "HEL", "OSL", "ARN", "BRU", "KBP", "OTP", "SOF",
    "BEG", "ZAG", "LJU", "SJJ", "TGD", "SKP", "TIA", "TBS",
    "EDI", "GLA", "MAN", "BHX", "BOD", "LYS", "MRS", "TLS",
    "AGP", "ALC", "BIO", "SVQ", "VLC", "NAP", "VCE", "BGY",
    "HAM", "DUS", "CGN", "STR", "KRK", "GDN", "WRO", "POZ",
    "KEF", "BGO", "TRD", "SVG", "GOT", "MMX", "AAR", "BLL",
    "RIX", "TLL", "VNO", "KUN", "VNO", "MSQ", "KIV", "IEV",
    "LWO", "ODS", "HRK", "DOK", "SIP", "SIP", "SIP", "SIP",
    # Middle East & Africa
    "DXB", "IST", "CAI", "JED", "RUH", "DOH", "CMN", "TUN",
    "SAW", "AYT", "ADB", "ESB", "AMM", "BEY", "TLV", "MCT",
    "BAH", "KWI", "SHJ", "DMM", "MED", "SLL", "RAK", "AGA",
    "FEZ", "TNG", "RBA", "NDR", "OVD", "BJA", "CZL", "AAE",
    "ALG", "ORN", "TLM", "CPT", "JNB", "DUR", "NBO", "MBA",
    "ADD", "LOS", "ABV", "ACC", "DKR", "ABJ", "LFW", "COO",
    # Americas
    "JFK", "LAX", "SFO", "ORD", "MIA", "YYZ", "YVR", "MEX",
    "GRU", "EZE", "BOG", "LIM", "SCL", "SYD", "MEL", "AKL",
    "EWR", "LGA", "BOS", "WAS", "IAD", "DCA", "BWI", "PHL",
    "ATL", "CLT", "MCO", "TPA", "FLL", "MIA", "RSW", "PBI",
    "DFW", "IAH", "AUS", "SAT", "DEN", "PHX", "LAS", "SAN",
    "SEA", "PDX", "SLC", "HNL", "OGG", "ANC", "YUL", "YOW",
    "YEG", "YYC", "YWG", "YHZ", "YQB", "CUN", "GDL", "MTY",
    "PTY", "SJO", "GUA", "SAL", "MGA", "TGU", "BZE", "SDQ",
    "PUJ", "STI", "SJU", "BQN", "STT", "STX", "HAV", "NAS",
    "GIG", "CNF", "BSB", "SSA", "REC", "FOR", "BEL", "MAO",
    "VCP", "CWB", "POA", "FLN", "VVI", "LPB", "CBB", "SRZ",
    "UIO", "GYE", "CUE", "MEC", "BOG", "MDE", "CLO", "CTG",
    "BAQ", "SMR", "PEI", "BGA", "CUC", "LET", "CCS", "MAR",
    # Asia & Pacific
    "NRT", "HND", "ICN", "PEK", "PVG", "HKG", "TPE", "SIN",
    "BKK", "KUL", "CGK", "SGN", "MNL", "DEL", "BOM", "BLR",
    "KIX", "ITM", "NGO", "FUK", "CTS", "OKA", "KOJ", "HIJ",
    "GMP", "CJU", "PUS", "TAE", "CJJ", "KWJ", "RSU", "MWX",
    "SHA", "CAN", "SZX", "CTU", "CKG", "KMG", "XIY", "HGH",
    "XMN", "CSX", "WUH", "CGO", "NKG", "TSN", "URC", "HRB",
    "KHH", "RMQ", "TNN", "MFM", "KLO", "CEB", "DVO", "ILO",
    "BDO", "DPS", "SUB", "KNO", "UPG", "YIA", "SRG", "PNK",
    "BPN", "MDC", "AMQ", "DJJ", "SOQ", "TIM", "NBX", "WMX",
    "HAN", "DAD", "CXR", "PQC", "VCA", "VII", "UIH", "THD",
    "VTE", "LPQ", "PKZ", "REP", "PNH", "KOS", "RGN", "MDL",
    "CCU", "MAA", "HYD", "PNQ", "AMD", "CCJ", "COK", "TRV",
    "BNE", "PER", "ADL", "CBR", "HBA", "DRW", "CNS", "OOL",
    "WLG", "CHC", "ZQN", "DUD", "NAN", "SUV", "APW", "TBU",
    "NOU", "PPT", "BOB", "MOZ", "GUM", "SPN", "ROR", "TKK",
]

_KNOWN_LOCATIONS = {
    # Europe
    "london": ["LHR", "LGW", "STN", "LTN", "LCY", "SEN"],
    "paris": ["CDG", "ORY", "BVA"],
    "madrid": ["MAD"],
    "barcelona": ["BCN"],
    "rome": ["FCO", "CIA"],
    "lisbon": ["LIS"],
    "berlin": ["BER"],
    "amsterdam": ["AMS"],
    "milan": ["MXP", "LIN", "BGY"],
    "frankfurt": ["FRA", "HHN"],
    "munich": ["MUC", "FMM"],
    "moscow": ["SVO", "DME", "VKO"],
    "istanbul": ["IST", "SAW"],
    "stockholm": ["ARN", "BMA", "NYO"],
    "oslo": ["OSL", "TRF"],
    "copenhagen": ["CPH"],
    "dublin": ["DUB"],
    "vienna": ["VIE"],
    "prague": ["PRG"],
    "budapest": ["BUD"],
    "warsaw": ["WAW", "WMI"],
    "athens": ["ATH"],
    "brussels": ["BRU", "CRL"],
    "geneva": ["GVA"],
    "zurich": ["ZRH"],
    
    # North America
    "new york": ["JFK", "EWR", "LGA"],
    "los angeles": ["LAX", "BUR", "LGB", "SNA", "ONT"],
    "san francisco": ["SFO", "OAK", "SJC"],
    "chicago": ["ORD", "MDW"],
    "washington": ["IAD", "DCA", "BWI"],
    "miami": ["MIA", "FLL", "PBI"],
    "dallas": ["DFW", "DAL"],
    "houston": ["IAH", "HOU"],
    "boston": ["BOS"],
    "toronto": ["YYZ", "YTZ"],
    "montreal": ["YUL", "YHU"],
    "vancouver": ["YVR"],
    "mexico city": ["MEX", "NLU"],
    
    # South America
    "sao paulo": ["GRU", "CGH", "VCP"],
    "rio de janeiro": ["GIG", "SDU"],
    "buenos aires": ["EZE", "AEP", "EPA"],
    "santiago": ["SCL"],
    "lima": ["LIM"],
    "bogota": ["BOG"],
    
    # Asia / Pacific
    "tokyo": ["HND", "NRT"],
    "osaka": ["KIX", "ITM", "UKB"],
    "seoul": ["ICN", "GMP"],
    "beijing": ["PEK", "PKX"],
    "shanghai": ["PVG", "SHA"],
    "taipei": ["TPE", "TSA"],
    "hong kong": ["HKG"],
    "bangkok": ["BKK", "DMK"],
    "kuala lumpur": ["KUL", "SZB"],
    "singapore": ["SIN"],
    "jakarta": ["CGK", "HLP"],
    "manila": ["MNL", "CRK"],
    "delhi": ["DEL"],
    "mumbai": ["BOM"],
    "sydney": ["SYD"],
    "melbourne": ["MEL", "AVV", "MEB"],
    "brisbane": ["BNE"],
    "auckland": ["AKL"],
    
    # Middle East / Africa
    "dubai": ["DXB", "DWC"],
    "abu dhabi": ["AUH"],
    "doha": ["DOH"],
    "cairo": ["CAI"],
    "tel aviv": ["TLV"],
    "johannesburg": ["JNB", "HLA"],
    "cape town": ["CPT"],
    "nairobi": ["NBO", "WIL"]
}


class MockClient:
    """Mirrors AmadeusClient's typed helpers; the phase modules can't tell the difference."""

    def __init__(self, settings, cache=None):
        self.s = settings
        self.cache = cache  # accepted for signature parity; mock is instant

    # ---- helpers --------------------------------------------------------
    @staticmethod
    def _rng(*parts) -> random.Random:
        seed = int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest(), 16)
        return random.Random(seed)

    def _rough_price(self, origin, dest, dep, ret) -> float:
        rng = self._rng("rough", origin, dest, dep, ret)
        route_base = 55 + (sum(ord(c) for c in origin + dest) % 60)   # ~55-115
        return round(route_base + rng.randint(0, 170) + (35 if ret else 0), 2)

    @staticmethod
    def _sample_dates(date_range: str | None, duration: str | None, n: int, rng):
        """Pick up to n departure dates in the range, each with a stay in [min,max]."""
        if date_range and "," in date_range:
            start_s, end_s = date_range.split(",", 1)
        else:
            start_s = end_s = (date_range or date.today().isoformat())
        try:
            start, end = date.fromisoformat(start_s), date.fromisoformat(end_s)
        except ValueError:
            start = end = date.today()
        span = max((end - start).days, 0)

        min_stay, max_stay = 3, 7
        if duration and "," in duration:
            try:
                min_stay, max_stay = (int(x) for x in duration.split(",", 1))
            except ValueError:
                pass

        out = []
        for _ in range(n):
            dep = start + timedelta(days=rng.randint(0, span) if span else 0)
            ret = dep + timedelta(days=rng.randint(min_stay, max(min_stay, max_stay)))
            out.append((dep.isoformat(), ret.isoformat()))
        return out

    # ---- typed endpoint helpers (mirror AmadeusClient) ------------------
    def flight_inspiration(self, origin, departure_date=None, duration=None, max_price=None):
        log.info("MOCK inspiration from %s", origin)
        time.sleep(self.s.request_delay)
        rng = self._rng("insp", origin, departure_date)
        pool = [d for d in _INSPIRATION_POOL if d != origin]
        rng.shuffle(pool)
        data = []
        for dest in pool[:80]:
            dep, ret = self._sample_dates(departure_date, duration, 1, self._rng(origin, dest))[0]
            data.append({
                "type": "flight-destination", "origin": origin, "destination": dest,
                "departureDate": dep, "returnDate": ret,
                "price": {"total": f"{self._rough_price(origin, dest, dep, ret):.2f}"},
            })
        return {"data": data, "meta": {"currency": "EUR"}}

    def flight_dates(self, origin, destination, departure_date=None, duration=None,
                     non_stop=None, max_price=None):
        log.info("MOCK cheapest-dates %s->%s", origin, destination)
        time.sleep(self.s.request_delay)
        rng = self._rng("dates", origin, destination, departure_date)
        data = []
        for dep, ret in self._sample_dates(departure_date, duration, 4, rng):
            data.append({
                "type": "flight-date", "origin": origin, "destination": destination,
                "departureDate": dep, "returnDate": ret,
                "price": {"total": f"{self._rough_price(origin, destination, dep, ret):.2f}"},
            })
        return {"data": data, "meta": {"currency": "EUR"}}

    def flight_offers(self, origin, destination, departure_date, return_date,
                      adults=1, currency="EUR", non_stop=False, max_results=5):
        log.info("MOCK offers %s->%s %s..%s", origin, destination, departure_date, return_date)
        time.sleep(self.s.request_delay)
        rough = self._rough_price(origin, destination, departure_date, return_date)
        rng = self._rng("offer", origin, destination, departure_date, return_date)
        carriers = ["IB", "BA", "FR", "U2", "LH", "AF", "VY"]
        data = []
        for _ in range(min(max_results, 3)):
            verified = round(rough * rng.uniform(0.92, 1.14) * adults, 2)
            data.append({
                "type": "flight-offer",
                "price": {"grandTotal": f"{verified:.2f}", "currency": currency},
                "itineraries": [{"segments": [{"carrierCode": rng.choice(carriers)}]}],
            })
        return {"data": data}

    def search_locations(self, keyword, sub_type="CITY,AIRPORT"):
        codes = _KNOWN_LOCATIONS.get(keyword.lower(), [keyword[:3].upper()])
        return {"data": [{"iataCode": c} for c in codes]}
