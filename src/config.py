import os
from .models import SearchConfig, APIKeys

GEO_LOCATIONS = [
    {"gl": "de", "name": "Germany", "currency": "EUR"},
    {"gl": "in", "name": "India", "currency": "INR"},
    {"gl": "br", "name": "Brazil", "currency": "BRL"},
    {"gl": "vn", "name": "Vietnam", "currency": "VND"},
    {"gl": "za", "name": "South Africa", "currency": "ZAR"},
    {"gl": "tr", "name": "Turkey", "currency": "TRY"}
]

def load_config() -> SearchConfig:
    return SearchConfig(
        origin=os.environ.get("ORIGIN", "FRA"),
        destination=os.environ.get("DESTINATION", "HYD"),
        date_from=os.environ.get("DATE_FROM", "2026-07-01"),
        date_to=os.environ.get("DATE_TO", "2026-08-31"),
        cabin_class=os.environ.get("CABIN_CLASS", "BUSINESS").upper(),
        adults=int(os.environ.get("ADULTS", "2")),
        infants_on_lap=int(os.environ.get("INFANTS_ON_LAP", "1"))
    )

def load_api_keys() -> APIKeys:
    return APIKeys(
        serpapi_key=os.environ.get("SERPAPI_KEY"),
        amadeus_client_id=os.environ.get("AMADEUS_CLIENT_ID"),
        amadeus_client_secret=os.environ.get("AMADEUS_CLIENT_SECRET"),
        duffel_token=os.environ.get("DUFFEL_TOKEN")
    )
