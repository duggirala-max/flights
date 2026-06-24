import requests
import json
from datetime import datetime
from typing import List, Optional
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource

class SeatsAeroSource(FlightSource):
    def __init__(self):
        self.programs = ["aeroplan", "lifemiles", "united"]

    def name(self) -> str:
        return "seats_aero"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        print("Seats.aero: Searching for Award Flights...")
        offers = []
        
        if not keys.seats_aero_key:
            print("Seats.aero Error: Missing SEATS_AERO_KEY")
            return offers

        # The API requires pro_ prefixed key
        key = keys.seats_aero_key if keys.seats_aero_key.startswith("pro_") else f"pro_{keys.seats_aero_key}"
        
        headers = {
            "Partner-Authorization": key,
            "Accept": "application/json"
        }

        url = "https://seats.aero/partnerapi/search"

        # Map our generic cabin class to seats.aero format
        cabin_mapping = {
            "business": "business",
            "economy": "economy",
            "first": "first",
            "premium economy": "premium"
        }
        cabin = cabin_mapping.get(config.cabin_class.lower(), "business")

        for program in self.programs:
            print(f"Seats.aero: Querying {program}...")
            params = {
                "origin": config.origin,
                "destination": config.destination,
                "cabin": cabin,
                "source": program,
                "start_date": config.date_from,
                "end_date": config.date_to
            }

            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", data) if isinstance(data, dict) else data
                    
                    if not items:
                        continue
                        
                    for item in items:
                        parsed = self._parse_offer(item, program, config)
                        if parsed:
                            offers.append(parsed)
                else:
                    print(f"Seats.aero API error for {program}: {resp.status_code} - {resp.text}")
                    
            except Exception as e:
                print(f"Seats.aero exception for {program}: {str(e)}")

        return offers

    def _parse_offer(self, item: dict, program: str, config: SearchConfig) -> Optional[FlightOffer]:
        try:
            # Determine cost based on cabin
            miles_key = "YMileageCost"
            if config.cabin_class.lower() == "business":
                miles_key = "JMileageCost"
            elif config.cabin_class.lower() == "first":
                miles_key = "FMileageCost"
            elif config.cabin_class.lower() in ["premium economy", "premium_economy"]:
                miles_key = "WMileageCost"
                
            miles = item.get(miles_key)
            if not miles or str(miles) == "0":
                return None # Seat not actually available in this cabin
                
            miles = int(miles)

            # Filter out bad dynamic-pricing deals
            max_miles = 100000 if config.cabin_class.lower() == "business" else 60000
            if miles > max_miles:
                return None # Drop expensive dynamic tickets
            
            # Extract basic flight info
            date_str = item.get("Date", config.date_from)
            route = item.get("Route", {})
            origin = route.get("OriginAirport", config.origin)
            dest = route.get("DestinationAirport", config.destination)
            airlines = item.get("Airlines", "")
            
            # Calculate estimated EUR cost for purchasing miles
            # Conservative estimate: €15 per 1,000 miles during typical sales + ~€100 baseline taxes
            estimated_miles_cost = (miles / 1000.0) * 15.0
            estimated_taxes = 100.0
            total_estimated_eur = estimated_miles_cost + estimated_taxes
            
            # Direct deep link structure based on program
            booking_url = "#"
            if program == "aeroplan":
                booking_url = "https://www.aircanada.com/aeroplan/redeem/"
                transfer_partners = ["Amex", "Chase", "Capital One"]
            elif program == "lifemiles":
                booking_url = "https://www.lifemiles.com/fly/find-flights"
                transfer_partners = ["Amex", "Capital One", "Citi"]
            elif program == "united":
                booking_url = "https://www.united.com/en/us/book-flight/united-one-way"
                transfer_partners = ["Chase"]
            else:
                transfer_partners = []

            # Seats.aero doesn't give us exact duration or times in the basic search endpoint,
            # we just know the seat exists on that day.
            
            # We multiply miles and cost by the number of adults
            total_adult_miles = miles * config.adults
            total_adult_eur = total_estimated_eur * config.adults
            
            # Infants on lap are generally ~10% of adult cash fare or a flat fee on awards.
            # We'll add a conservative flat €150 for the infant.
            infant_fee = 150.0 * config.infants_on_lap
            
            final_price = total_adult_eur + infant_fee

            return FlightOffer(
                source=self.name(),
                price_eur=final_price,
                price_original=final_price,
                currency_original="EUR",
                origin=origin,
                destination=dest,
                departure_date=date_str,
                departure_time="TBD", # Not provided in basic search
                arrival_time="TBD",
                duration_minutes=0,
                stops=0 if item.get("Direct") else 1,
                airlines=airlines.split(",") if airlines else [],
                flight_numbers=[],
                fare_basis=None,
                booking_class=None,
                cabin=config.cabin_class,
                point_of_sale="Global",
                booking_url=booking_url,
                booking_method="GET",
                booking_post_data=None,
                raw_data=item,
                
                # Award specific fields
                is_award_mapped=True,
                award_program=program.capitalize(),
                award_miles=total_adult_miles,
                award_taxes_eur=estimated_taxes * config.adults + infant_fee,
                transfer_partners=transfer_partners,
                award_search_url=booking_url
            )
        except Exception as e:
            print(f"Error parsing offer: {e}")
            return None
