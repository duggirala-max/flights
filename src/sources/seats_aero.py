import requests
import json
import calendar
from datetime import datetime
from typing import List, Optional
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource

class SeatsAeroSource(FlightSource):
    def __init__(self):
        # We process all programs returned by Seats.aero
        pass

    def name(self) -> str:
        return "seats_aero"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        print(f"Seats.aero: Searching for Award Flights for months: {config.target_months}")
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

        for month_str in config.target_months:
            try:
                year, month = map(int, month_str.split('-'))
                last_day = calendar.monthrange(year, month)[1]
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day}"
            except Exception as e:
                print(f"Invalid month format: {month_str} ({e})")
                continue

            print(f"Seats.aero: Querying {start_date} to {end_date}...")
            params = {
                "origin_airport": config.origin,
                "destination_airport": config.destination,
                "start_date": start_date,
                "end_date": end_date,
                "take": 1000,
                "order_by": "lowest_mileage"
            }

            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", data) if isinstance(data, dict) else data
                    
                    if not items:
                        print(f"Seats.aero: Found 0 items for {month_str}")
                        continue
                        
                    for item in items:
                        program = str(item.get("Source", "unknown")).lower()
                        parsed = self._parse_offer(item, program, config)
                        if parsed:
                            offers.append(parsed)
                else:
                    print(f"Seats.aero API error for {month_str}: {resp.status_code} - {resp.text}")
                    
            except Exception as e:
                print(f"Seats.aero exception for {month_str}: {str(e)}")

        return offers

    def _parse_offer(self, item: dict, program: str, config: SearchConfig) -> Optional[FlightOffer]:
        try:
            # Determine cost and keys based on cabin
            miles_key = "YMileageCost"
            taxes_key = "YTotalTaxes"
            airlines_key = "YAirlines"
            cabin_letter = "Y"
            
            if config.cabin_class.lower() == "business":
                miles_key = "JMileageCost"
                taxes_key = "JTotalTaxes"
                airlines_key = "JAirlines"
                cabin_letter = "J"
            elif config.cabin_class.lower() == "first":
                miles_key = "FMileageCost"
                taxes_key = "FTotalTaxes"
                airlines_key = "FAirlines"
                cabin_letter = "F"
            elif config.cabin_class.lower() in ["premium economy", "premium_economy"]:
                miles_key = "WMileageCost"
                taxes_key = "WTotalTaxes"
                airlines_key = "WAirlines"
                cabin_letter = "W"
                
            miles = item.get(miles_key)
            if not miles or str(miles) == "0":
                return None # Seat not actually available in this cabin
                
            miles = int(miles)

            # Filter out bad dynamic-pricing deals
            max_miles = 100000 if config.cabin_class.lower() == "business" else 60000
            if miles > max_miles:
                return None # Drop expensive dynamic tickets
            
            # Extract basic flight info
            date_str = item.get("Date", "Unknown Date")
            route = item.get("Route", {})
            origin = route.get("OriginAirport", config.origin)
            dest = route.get("DestinationAirport", config.destination)
            airlines = item.get(airlines_key, "")
            
            # Calculate estimated EUR cost for purchasing miles
            # Conservative estimate: €15 per 1,000 miles during typical sales
            estimated_miles_cost = (miles / 1000.0) * 15.0
            
            # Extract true taxes from Seats.aero API (usually given in integer cents/pence)
            raw_taxes = int(item.get(taxes_key, 10000))
            tax_currency = item.get("TaxesCurrency", "USD")
            
            # Basic static conversion for taxes (Assume USD/GBP are roughly parity to EUR for simple UI display)
            # 10000 raw = 100.00
            estimated_taxes = float(raw_taxes) / 100.0
            total_estimated_eur = estimated_miles_cost + estimated_taxes
            
            # Direct deep link structure based on program
            booking_url = f"https://seats.aero/search?source={program}" # Fallback
            transfer_partners = []
            
            if program == "aeroplan":
                booking_url = "https://www.aircanada.com/en-ca/aeroplan"
                transfer_partners = ["Amex", "Chase", "Capital One"]
            elif program == "lifemiles":
                booking_url = "https://www.lifemiles.com/fly/find-flights"
                transfer_partners = ["Amex", "Capital One", "Citi"]
            elif program == "united":
                booking_url = "https://www.united.com/en/us/book-flight/united-one-way"
                transfer_partners = ["Chase", "Bilt"]
            elif program == "lufthansa":
                booking_url = "https://www.miles-and-more.com/"
                transfer_partners = ["Marriott"]
            elif program == "american":
                booking_url = "https://www.aa.com/booking/find-flights?searchType=Award"
                transfer_partners = ["Bilt", "Marriott"]
            elif program == "flyingblue":
                booking_url = "https://www.airfrance.us/en/search/flights"
                transfer_partners = ["Amex", "Chase", "Capital One", "Citi", "Bilt"]
            elif program == "virginatlantic":
                booking_url = "https://www.virginatlantic.com/"
                transfer_partners = ["Amex", "Chase", "Capital One", "Citi", "Bilt"]
            elif program == "qantas":
                booking_url = "https://www.qantas.com/"
                transfer_partners = ["Amex", "Capital One", "Citi"]
            elif program == "delta":
                booking_url = "https://www.delta.com/flight-search/book-a-flight"
                transfer_partners = ["Amex"]
            else:
                transfer_partners = ["Varies"]

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
