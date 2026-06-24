import os
import calendar
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
    months_str = os.environ.get("TARGET_MONTHS", "2026-08")
    months = [m.strip() for m in months_str.split(",") if m.strip()]
    if not months:
        months = ["2026-08"]

    return SearchConfig(
        origin=os.environ.get("ORIGIN", "FRA"),
        destination=os.environ.get("DESTINATION", "HYD"),
        target_months=months,
        cabin_class=os.environ.get("CABIN_CLASS", "BUSINESS").upper(),
        adults=int(os.environ.get("ADULTS", "2")),
        infants_on_lap=int(os.environ.get("INFANTS_ON_LAP", "1"))
    )

def load_api_keys() -> APIKeys:
    return APIKeys(
        serpapi_key=os.environ.get("SERPAPI_KEY"),
        duffel_token=os.environ.get("DUFFEL_TOKEN"),
        seats_aero_key=os.environ.get("SEATS_AERO_KEY")
    )
