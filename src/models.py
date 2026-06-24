from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class SearchConfig:
    origin: str
    destination: str
    target_months: List[str]
    cabin_classes: List[str]
    adults: int = 2
    infants_on_lap: int = 1

@dataclass
class APIKeys:
    serpapi_key: Optional[str] = None
    duffel_token: Optional[str] = None
    seats_aero_key: Optional[str] = None

@dataclass
class FlightOffer:
    source: str              # "amadeus", "duffel", "serpapi_google"
    price_eur: float         # Normalized to EUR
    price_original: float    # Original currency
    currency_original: str   # Original currency code
    origin: str              # IATA
    destination: str         # IATA
    departure_date: str      # ISO date
    departure_time: str      # HH:MM
    arrival_time: str        # HH:MM
    duration_minutes: int
    stops: int
    airlines: List[str]
    flight_numbers: List[str]
    fare_basis: Optional[str]   # From GDS sources — key for mistake fare detection
    booking_class: Optional[str]
    cabin: str
    point_of_sale: str       # Country used for PoS
    booking_url: str         # Direct deep link
    booking_method: str      # "GET" or "POST"
    booking_post_data: Optional[str]
    raw_data: Dict[str, Any] # Full API response for debugging
    anomaly_score: int = 0
    anomaly_reasons: List[str] = field(default_factory=list)
    
    # Award Arbitrage Fields
    is_award_mapped: bool = False
    award_program: Optional[str] = None
    award_miles: Optional[int] = None
    award_taxes_original: Optional[float] = None
    award_taxes_currency: Optional[str] = None
    award_taxes_eur: Optional[float] = None
    transfer_partners: List[str] = field(default_factory=list)
    award_search_url: Optional[str] = None
