import requests
from typing import List
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource
import re

class OTADeepLinker(FlightSource):
    def name(self) -> str:
        return "ota_deep_linker"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        if not keys.serpapi_key:
            print("OTA Deep Linker: Missing SerpApi Key")
            return []

        print("OTA Deep Linker: Searching hidden Consolidator fares...")
        offers = []
            
        params = {
            "engine": "google_flights",
            "departure_id": config.origin,
            "arrival_id": config.destination,
            "outbound_date": config.date_from,
            "currency": "EUR",
            "hl": "en",
            "gl": "de", # Point of sale Germany
            "type": "2", # one-way
            "adults": config.adults,
            "infants_in_seat": config.infants_on_lap, 
            "travel_class": "2" if config.cabin_class.lower() == "business" else "1",
            "api_key": keys.serpapi_key
        }

        try:
            resp = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
            data = resp.json()
            
            raw_flights = data.get("best_flights", []) + data.get("other_flights", [])
            
            for flight in raw_flights[:10]: # Top 10 deals
                price = flight.get("price", 99999)
                airlines = []
                fnums = []
                for idx, leg in enumerate(flight.get("flights", [])):
                    airlines.append(leg.get("airline", "Unknown"))
                    fn = leg.get('flight_number', '')
                    fnums.append(f"{leg.get('airline', '')} {fn}" if fn else "Unknown")
                    
                token = flight.get("booking_token")
                deep_link = ""
                
                if token:
                    print(f"OTA Deep Linker: Resolving checkout cart for {price} EUR...")
                    res_params = {
                        "engine": "google_flights",
                        "booking_token": token,
                        "api_key": keys.serpapi_key
                    }
                    r2 = requests.get("https://serpapi.com/search.json", params=res_params, timeout=30)
                    options = r2.json().get("booking_options", [])
                    if options:
                        # Grab the first available booking option URL (usually the airline or cheapest OTA)
                        deep_link = options[0].get("url", "")
                        
                if not deep_link:
                    deep_link = flight.get("google_flights_url", "")
                
                # The aggregator handles deduplication and history
                offers.append(FlightOffer(
                    source=self.name(),
                    price_eur=float(price),
                    price_original=float(price),
                    currency_original="EUR",
                    origin=config.origin,
                    destination=config.destination,
                    departure_date=config.date_from,
                    departure_time="00:00",
                    arrival_time="00:00",
                    duration_minutes=flight.get("total_duration", 0),
                    stops=len(flight.get("flights", [])) - 1,
                    airlines=list(set(airlines)),
                    flight_numbers=fnums,
                    fare_basis=None,
                    booking_class=None,
                    cabin=config.cabin_class,
                    point_of_sale="DE",
                    booking_url=deep_link,
                    booking_method="GET",
                    booking_post_data=None,
                    raw_data={}
                ))
                
        except Exception as e:
            print(f"OTA Deep Linker Error: {e}")

        return offers
