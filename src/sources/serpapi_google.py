import time
from datetime import datetime, timedelta
from typing import List
from serpapi import GoogleSearch
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource
from ..config import GEO_LOCATIONS

class SerpApiGoogleSource(FlightSource):
    def name(self) -> str:
        return "serpapi_google"

    def _map_cabin_class(self, c_class: str) -> str:
        c = c_class.upper()
        if c == "ECONOMY": return "1"
        if c == "PREMIUM_ECONOMY": return "2"
        if c == "BUSINESS": return "3"
        if c == "FIRST": return "4"
        return "3"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        if not keys.serpapi_key:
            print("SerpApi key not provided.")
            return []

        try:
            start_dt = datetime.strptime(config.date_from, "%Y-%m-%d")
            end_dt = datetime.strptime(config.date_to, "%Y-%m-%d")
        except ValueError:
            print("Invalid dates provided to SerpApiGoogleSource")
            return []

        offers = []
        delta = (end_dt - start_dt).days
        if delta < 0: delta = 0
        
        # Determine step size to limit searches
        target_searches_per_geo = 3 # keep API calls low for testing
        num_geos = 3 # top 3 geos
        step = max(1, delta // target_searches_per_geo)

        active_geos = GEO_LOCATIONS[:num_geos]
        current_dt = start_dt

        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            for geo in active_geos:
                offers.extend(self._search_geo(date_str, geo, config, keys))
            current_dt += timedelta(days=step)
            if step == 0: break

        return offers

    def _search_geo(self, date_str: str, geo: dict, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        print(f"SerpApi: Checking {date_str} disguised from {geo['name']} (Geo: {geo['gl']})...")
        params = {
            "engine": "google_flights",
            "departure_id": config.origin,
            "arrival_id": config.destination,
            "outbound_date": date_str,
            "type": "2", # one-way
            "travel_class": self._map_cabin_class(config.cabin_class),
            "adults": str(config.adults),
            "infants_on_lap": str(config.infants_on_lap),
            "gl": geo["gl"],
            "hl": "en",
            "currency": geo["currency"], # Query in local currency
            "api_key": keys.serpapi_key,
            "deep_search": "true" # CRITICAL for accurate pricing
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            best_flights = results.get("best_flights", [])
            other_flights = results.get("other_flights", [])
            all_options = best_flights + other_flights
            
            parsed_flights = []
            
            for flight in all_options:
                price = flight.get("price")
                if not price: continue
                
                legs = flight.get("flights", [])
                if not legs: continue
                
                airlines = list(set([leg.get("airline", "Unknown") for leg in legs]))
                flight_numbers = [leg.get("flight_number", "Unknown") for leg in legs]
                
                try:
                    price_val = float(price)
                except:
                    price_val = 99999.0
                    
                total_duration = flight.get("total_duration", 0)
                
                local_dep = legs[0].get("departure_airport", {}).get("time", "TBD").split(" ")[0] if legs else "TBD"
                local_arr = legs[-1].get("arrival_airport", {}).get("time", "TBD").split(" ")[0] if legs else "TBD"
                
                # Capture the SerpApi-provided Google Flights search URL which HAS all filters applied
                # as a fallback if we don't resolve the token later.
                gf_url = results.get("search_metadata", {}).get("google_flights_url")
                fallback_url = gf_url if gf_url else f"https://www.google.com/travel/flights?q=Flights%20to%20{config.destination}%20from%20{config.origin}%20on%20{date_str}%20one-way"
                
                parsed_flights.append(FlightOffer(
                    source=self.name(),
                    price_eur=price_val, # Will be normalized later
                    price_original=price_val,
                    currency_original=geo["currency"],
                    origin=config.origin,
                    destination=config.destination,
                    departure_date=date_str,
                    departure_time=local_dep,
                    arrival_time=local_arr,
                    duration_minutes=total_duration,
                    stops=len(legs) - 1,
                    airlines=airlines,
                    flight_numbers=flight_numbers,
                    fare_basis=None,
                    booking_class=None,
                    cabin=config.cabin_class,
                    point_of_sale=geo['name'],
                    booking_url=fallback_url,
                    booking_method="GET",
                    booking_post_data=None,
                    raw_data={"booking_token": flight.get("booking_token")}
                ))


            return parsed_flights

        except Exception as e:
            print(f"SerpApi Error for {date_str} in {geo['name']}: {e}")
            return []

    @staticmethod
    def resolve_booking_link(offer: FlightOffer, api_key: str):
        token = offer.raw_data.get("booking_token")
        if not token: return
        
        try:
            params = {
                "engine": "google_flights",
                "booking_token": token,
                "api_key": api_key
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            options = results.get("booking_options", [])
            if options:
                # Get the first direct airline link or OTA
                req = options[0].get("booking_request", {})
                offer.booking_url = req.get("url", offer.booking_url)
                offer.booking_method = "POST" if req.get("post_data") else "GET"
                offer.booking_post_data = req.get("post_data")
        except Exception as e:
            print(f"Error resolving booking link: {e}")
