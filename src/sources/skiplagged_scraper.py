from typing import List
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource
from curl_cffi import requests
from datetime import datetime, timedelta

class SkiplaggedScraper(FlightSource):
    def name(self) -> str:
        return "skiplagged"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        print("Skiplagged Scraper: Searching Hidden City Fares...")
        offers = []
        
        # Skiplagged URL format
        url = f"https://skiplagged.com/api/search.php?from={config.origin}&to={config.destination}&depart={config.date_from}&return=&sort=cost"
        if config.cabin_class.lower() == "business":
            url += "&cabin=business"
            
        try:
            resp = requests.get(url, impersonate="chrome110", timeout=30)
            if resp.status_code != 200:
                print(f"Skiplagged Scraper Error: HTTP {resp.status_code}")
                return offers
                
            data = resp.json()
            flights_dict = data.get("flights", {})
            
            # Usually 'depart' is a list of [flight_durations, ?, flight_key, booking_token]
            departures = data.get("depart", [])
            for dep in departures[:10]: # Top 10
                if len(dep) >= 4:
                    flight_key = dep[3]
                    flight_data = flights_dict.get(flight_key)
                    if flight_data and len(flight_data) >= 2:
                        segments = flight_data[0]
                        price_cents = flight_data[1]
                        price = price_cents / 100.0
                        
                        airlines = []
                        fnums = []
                        for seg in segments:
                            flight_str = seg[0] # e.g. "LH1234"
                            airline_code = flight_str[:2]
                            airlines.append(airline_code)
                            fnums.append(flight_str)
                            
                        # Direct Deep link to skiplagged search pre-filled
                        deep_link = f"https://skiplagged.com/flights/{config.origin}/{config.destination}/{config.date_from}?cabin={config.cabin_class.lower()}"
                        
                        offers.append(FlightOffer(
                            source=self.name(),
                            price_eur=float(price),
                            price_original=float(price),
                            currency_original="USD", # skiplagged defaults to USD usually
                            origin=config.origin,
                            destination=config.destination,
                            departure_date=config.date_from,
                            departure_time="00:00",
                            arrival_time="00:00",
                            duration_minutes=0,
                            stops=len(segments) - 1,
                            airlines=list(set(airlines)),
                            flight_numbers=fnums,
                            fare_basis=None,
                            booking_class=None,
                            cabin=config.cabin_class,
                            point_of_sale="US",
                            booking_url=deep_link,
                            booking_method="GET",
                            booking_post_data=None,
                            raw_data={}
                        ))
        except Exception as e:
            print(f"Skiplagged Scraper Error: {e}")
            
        return offers
