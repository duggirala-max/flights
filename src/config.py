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
    target_month_str = os.environ.get("TARGET_MONTH", "2026-08")
    try:
        year, month = map(int, target_month_str.split('-'))
        last_day = calendar.monthrange(year, month)[1]
        date_from = f"{year}-{month:02d}-01"
        date_to = f"{year}-{month:02d}-{last_day}"
    except Exception:
        date_from = "2026-08-01"
        date_to = "2026-08-31"

    return SearchConfig(
        origin=os.environ.get("ORIGIN", "FRA"),
        destination=os.environ.get("DESTINATION", "HYD"),
        date_from=date_from,
        date_to=date_to,
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
