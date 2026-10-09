"""Bundled airport/city dataset for instant, offline autocomplete.

Used by the /api/locations typeahead so the UI can suggest cities on every
keystroke without hitting (and rate-limiting) the Amadeus API. Codes are IATA
city metacodes (e.g. LON, NYC, TYO) where a metro area has several airports,
plus major individual airports — all valid inputs to the Amadeus endpoints.
"""
from __future__ import annotations

# (iata, city, name, country)
_RAW: list[tuple[str, str, str, str]] = [
    # --- United Kingdom / Ireland ---
    ("LON", "London", "London (all airports)", "United Kingdom"),
    ("LHR", "London", "Heathrow", "United Kingdom"),
    ("LGW", "London", "Gatwick", "United Kingdom"),
    ("STN", "London", "Stansted", "United Kingdom"),
    ("MAN", "Manchester", "Manchester", "United Kingdom"),
    ("EDI", "Edinburgh", "Edinburgh", "United Kingdom"),
    ("GLA", "Glasgow", "Glasgow", "United Kingdom"),
    ("BHX", "Birmingham", "Birmingham", "United Kingdom"),
    ("DUB", "Dublin", "Dublin", "Ireland"),
    # --- France ---
    ("PAR", "Paris", "Paris (all airports)", "France"),
    ("CDG", "Paris", "Charles de Gaulle", "France"),
    ("ORY", "Paris", "Orly", "France"),
    ("NCE", "Nice", "Cote d'Azur", "France"),
    ("MRS", "Marseille", "Marseille Provence", "France"),
    ("LYS", "Lyon", "Saint-Exupery", "France"),
    ("TLS", "Toulouse", "Toulouse-Blagnac", "France"),
    ("BOD", "Bordeaux", "Bordeaux-Merignac", "France"),
    # --- Spain ---
    ("MAD", "Madrid", "Adolfo Suarez Barajas", "Spain"),
    ("BCN", "Barcelona", "El Prat", "Spain"),
    ("AGP", "Malaga", "Costa del Sol", "Spain"),
    ("PMI", "Palma", "Palma de Mallorca", "Spain"),
    ("VLC", "Valencia", "Valencia", "Spain"),
    ("SVQ", "Seville", "Seville", "Spain"),
    ("BIO", "Bilbao", "Bilbao", "Spain"),
    ("TFS", "Tenerife", "Tenerife South", "Spain"),
    ("LPA", "Gran Canaria", "Gran Canaria", "Spain"),
    ("IBZ", "Ibiza", "Ibiza", "Spain"),
    # --- Portugal ---
    ("LIS", "Lisbon", "Humberto Delgado", "Portugal"),
    ("OPO", "Porto", "Francisco Sa Carneiro", "Portugal"),
    ("FAO", "Faro", "Faro", "Portugal"),
    ("FNC", "Funchal", "Madeira", "Portugal"),
    # --- Italy ---
    ("ROM", "Rome", "Rome (all airports)", "Italy"),
    ("FCO", "Rome", "Fiumicino", "Italy"),
    ("MIL", "Milan", "Milan (all airports)", "Italy"),
    ("MXP", "Milan", "Malpensa", "Italy"),
    ("BGY", "Milan", "Bergamo", "Italy"),
    ("VCE", "Venice", "Marco Polo", "Italy"),
    ("NAP", "Naples", "Naples", "Italy"),
    ("FLR", "Florence", "Florence", "Italy"),
    ("CTA", "Catania", "Catania", "Italy"),
    # --- Germany / Central Europe ---
    ("BER", "Berlin", "Brandenburg", "Germany"),
    ("MUC", "Munich", "Munich", "Germany"),
    ("FRA", "Frankfurt", "Frankfurt", "Germany"),
    ("HAM", "Hamburg", "Hamburg", "Germany"),
    ("DUS", "Dusseldorf", "Dusseldorf", "Germany"),
    ("CGN", "Cologne", "Cologne Bonn", "Germany"),
    ("STR", "Stuttgart", "Stuttgart", "Germany"),
    ("AMS", "Amsterdam", "Schiphol", "Netherlands"),
    ("BRU", "Brussels", "Brussels", "Belgium"),
    ("ZRH", "Zurich", "Zurich", "Switzerland"),
    ("GVA", "Geneva", "Geneva", "Switzerland"),
    ("VIE", "Vienna", "Vienna", "Austria"),
    ("PRG", "Prague", "Vaclav Havel", "Czechia"),
    ("BUD", "Budapest", "Ferenc Liszt", "Hungary"),
    ("WAW", "Warsaw", "Chopin", "Poland"),
    ("KRK", "Krakow", "John Paul II", "Poland"),
    # --- Nordics / Baltics ---
    ("CPH", "Copenhagen", "Kastrup", "Denmark"),
    ("OSL", "Oslo", "Gardermoen", "Norway"),
    ("ARN", "Stockholm", "Arlanda", "Sweden"),
    ("HEL", "Helsinki", "Vantaa", "Finland"),
    ("KEF", "Reykjavik", "Keflavik", "Iceland"),
    ("RIX", "Riga", "Riga", "Latvia"),
    ("TLL", "Tallinn", "Tallinn", "Estonia"),
    ("VNO", "Vilnius", "Vilnius", "Lithuania"),
    # --- Southeast Europe / Turkey ---
    ("ATH", "Athens", "Eleftherios Venizelos", "Greece"),
    ("HER", "Heraklion", "Heraklion", "Greece"),
    ("JTR", "Santorini", "Santorini", "Greece"),
    ("IST", "Istanbul", "Istanbul", "Turkey"),
    ("SAW", "Istanbul", "Sabiha Gokcen", "Turkey"),
    ("AYT", "Antalya", "Antalya", "Turkey"),
    ("SPU", "Split", "Split", "Croatia"),
    ("DBV", "Dubrovnik", "Dubrovnik", "Croatia"),
    ("ZAG", "Zagreb", "Zagreb", "Croatia"),
    ("OTP", "Bucharest", "Henri Coanda", "Romania"),
    ("SOF", "Sofia", "Sofia", "Bulgaria"),
    ("BEG", "Belgrade", "Nikola Tesla", "Serbia"),
    # --- North America ---
    ("NYC", "New York", "New York (all airports)", "United States"),
    ("JFK", "New York", "John F. Kennedy", "United States"),
    ("EWR", "Newark", "Newark Liberty", "United States"),
    ("LGA", "New York", "LaGuardia", "United States"),
    ("LAX", "Los Angeles", "Los Angeles Intl", "United States"),
    ("SFO", "San Francisco", "San Francisco Intl", "United States"),
    ("ORD", "Chicago", "O'Hare", "United States"),
    ("MIA", "Miami", "Miami Intl", "United States"),
    ("BOS", "Boston", "Logan", "United States"),
    ("WAS", "Washington", "Washington (all airports)", "United States"),
    ("SEA", "Seattle", "Seattle-Tacoma", "United States"),
    ("ATL", "Atlanta", "Hartsfield-Jackson", "United States"),
    ("DFW", "Dallas", "Dallas/Fort Worth", "United States"),
    ("DEN", "Denver", "Denver Intl", "United States"),
    ("LAS", "Las Vegas", "Harry Reid", "United States"),
    ("MCO", "Orlando", "Orlando Intl", "United States"),
    ("IAH", "Houston", "George Bush", "United States"),
    ("PHX", "Phoenix", "Sky Harbor", "United States"),
    ("YYZ", "Toronto", "Pearson", "Canada"),
    ("YVR", "Vancouver", "Vancouver Intl", "Canada"),
    ("YUL", "Montreal", "Trudeau", "Canada"),
    ("MEX", "Mexico City", "Benito Juarez", "Mexico"),
    ("CUN", "Cancun", "Cancun Intl", "Mexico"),
    # --- South America ---
    ("GRU", "Sao Paulo", "Guarulhos", "Brazil"),
    ("GIG", "Rio de Janeiro", "Galeao", "Brazil"),
    ("EZE", "Buenos Aires", "Ezeiza", "Argentina"),
    ("SCL", "Santiago", "Arturo Merino Benitez", "Chile"),
    ("LIM", "Lima", "Jorge Chavez", "Peru"),
    ("BOG", "Bogota", "El Dorado", "Colombia"),
    # --- Middle East / Africa ---
    ("DXB", "Dubai", "Dubai Intl", "United Arab Emirates"),
    ("AUH", "Abu Dhabi", "Zayed Intl", "United Arab Emirates"),
    ("DOH", "Doha", "Hamad Intl", "Qatar"),
    ("TLV", "Tel Aviv", "Ben Gurion", "Israel"),
    ("CAI", "Cairo", "Cairo Intl", "Egypt"),
    ("CMN", "Casablanca", "Mohammed V", "Morocco"),
    ("RAK", "Marrakesh", "Menara", "Morocco"),
    ("JNB", "Johannesburg", "OR Tambo", "South Africa"),
    ("CPT", "Cape Town", "Cape Town Intl", "South Africa"),
    ("NBO", "Nairobi", "Jomo Kenyatta", "Kenya"),
    # --- Asia / Pacific ---
    ("TYO", "Tokyo", "Tokyo (all airports)", "Japan"),
    ("HND", "Tokyo", "Haneda", "Japan"),
    ("NRT", "Tokyo", "Narita", "Japan"),
    ("OSA", "Osaka", "Osaka (all airports)", "Japan"),
    ("KIX", "Osaka", "Kansai", "Japan"),
    ("ICN", "Seoul", "Incheon", "South Korea"),
    ("PEK", "Beijing", "Capital", "China"),
    ("PVG", "Shanghai", "Pudong", "China"),
    ("HKG", "Hong Kong", "Hong Kong Intl", "Hong Kong"),
    ("TPE", "Taipei", "Taoyuan", "Taiwan"),
    ("BKK", "Bangkok", "Suvarnabhumi", "Thailand"),
    ("SIN", "Singapore", "Changi", "Singapore"),
    ("KUL", "Kuala Lumpur", "KLIA", "Malaysia"),
    ("DEL", "Delhi", "Indira Gandhi", "India"),
    ("BOM", "Mumbai", "Chhatrapati Shivaji", "India"),
    ("DPS", "Bali", "Ngurah Rai", "Indonesia"),
    ("CGK", "Jakarta", "Soekarno-Hatta", "Indonesia"),
    ("MNL", "Manila", "Ninoy Aquino", "Philippines"),
    ("SYD", "Sydney", "Kingsford Smith", "Australia"),
    ("MEL", "Melbourne", "Tullamarine", "Australia"),
    ("BNE", "Brisbane", "Brisbane", "Australia"),
    ("AKL", "Auckland", "Auckland", "New Zealand"),
]

AIRPORTS: list[dict] = [
    {"iata": i, "city": c, "name": n, "country": co} for (i, c, n, co) in _RAW
]


def search(query: str, limit: int = 8) -> list[dict]:
    """Rank airports/cities matching `query` by IATA code, city, name, or country."""
    q = query.strip().lower()
    if not q:
        return []
    scored: list[tuple[int, int, dict]] = []
    for idx, a in enumerate(AIRPORTS):
        iata, city, name, country = (
            a["iata"].lower(), a["city"].lower(), a["name"].lower(), a["country"].lower()
        )
        if iata == q:
            score = 0
        elif iata.startswith(q):
            score = 1
        elif city.startswith(q):
            score = 2
        elif q in city or q in name:
            score = 3
        elif country.startswith(q) or q in country:
            score = 4
        else:
            continue
        scored.append((score, idx, a))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [a for _, _, a in scored[:limit]]


def get(code: str) -> dict | None:
    code = code.strip().upper()
    for a in AIRPORTS:
        if a["iata"] == code:
            return a
    return None
