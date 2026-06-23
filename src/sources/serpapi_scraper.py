import urllib.parse
from typing import List
from curl_cffi import requests
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource

class SerpApiScraper(FlightSource):
    def name(self) -> str:
        return "serpapi_google"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        print("SerpApi Scraper: Searching Google Flights (Strict Business Class)...")
        offers = []
        if not keys.serpapi_key:
            print("SerpApi Scraper Error: Missing SERPAPI_KEY")
            return offers

        # Google Flights via SerpApi mappings:
        # travel_class: 1=Economy, 2=Premium Economy, 3=Business, 4=First
        # adults: number of adults
        # infants_in_seat / infants_on_lap
        
        cabin_mapping = {
            "economy": 1,
            "premium economy": 2,
            "premium_economy": 2,
            "business": 3,
            "first": 4
        }
        travel_class = cabin_mapping.get(config.cabin_class.lower(), 3) # default business

        params = {
            "engine": "google_flights",
            "departure_id": config.origin,
            "arrival_id": config.destination,
            "outbound_date": config.date_from,
            "currency": "EUR",
            "hl": "en",
            "gl": "de", # PoS Germany
            "type": 2, # 2 = One-way
            "travel_class": travel_class,
            "adults": config.adults,
            "infants_on_lap": config.infants_on_lap,
            "api_key": keys.serpapi_key
        }

        url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)

        try:
            resp = requests.get(url, impersonate="chrome110", timeout=60)
            if resp.status_code != 200:
                print(f"SerpApi Error: HTTP {resp.status_code}")
                return offers

            data = resp.json()
            best_flights = data.get("best_flights", [])
            other_flights = data.get("other_flights", [])
            
            all_flights_raw = best_flights + other_flights
            
            for f in all_flights_raw:
                flights_arr = f.get("flights", [])
                if not flights_arr:
                    continue
                    
                price = f.get("price", 0)
                if not price:
                    continue
                    
                # Ensure the price is a float
                try:
                    price_eur = float(price)
                except ValueError:
                    continue

                airlines = []
                fnums = []
                for seg in flights_arr:
                    airline = seg.get("airline", "")
                    flight_num = seg.get("flight_number", "")
                    if airline:
                        airlines.append(airline)
                    if airline and flight_num:
                        fnums.append(f"{airline}{flight_num}")

                # To be absolutely sure, SerpApi provides the exact shareable link in the response sometimes under 'search_metadata.google_flights_url'
                share_link = data.get("search_metadata", {}).get("google_flights_url", "https://www.google.com/flights")

                # Extract time formats: "2026-08-01 17:35" -> "17:35"
                dep_time_raw = flights_arr[0].get("departure_airport", {}).get("time", "00:00")
                dep_time = dep_time_raw.split(" ")[1] if len(dep_time_raw) > 10 else "00:00"
                
                arr_time_raw = flights_arr[-1].get("arrival_airport", {}).get("time", "00:00")
                arr_time = arr_time_raw.split(" ")[1] if len(arr_time_raw) > 10 else "00:00"

                offers.append(FlightOffer(
                    source=self.name(),
                    price_eur=price_eur,
                    price_original=price_eur,
                    currency_original="EUR",
                    origin=config.origin,
                    destination=config.destination,
                    departure_date=config.date_from,
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    duration_minutes=f.get("total_duration", 0),
                    stops=len(flights_arr) - 1,
                    airlines=list(set(airlines)),
                    flight_numbers=fnums,
                    fare_basis=None,
                    booking_class=None,
                    cabin=config.cabin_class,
                    point_of_sale="DE",
                    booking_url=share_link,
                    booking_method="GET",
                    booking_post_data=None,
                    raw_data=f
                ))
                
        except Exception as e:
            print(f"SerpApi Error: {e}")

        return offers
