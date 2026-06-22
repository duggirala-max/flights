import requests
from datetime import datetime, timedelta
from typing import List, Optional
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource

class DuffelSource(FlightSource):
    def name(self) -> str:
        return "duffel"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        if not keys.duffel_token:
            print("Duffel token not provided.")
            return []

        try:
            start_dt = datetime.strptime(config.date_from, "%Y-%m-%d")
            end_dt = datetime.strptime(config.date_to, "%Y-%m-%d")
        except ValueError:
            return []

        offers = []
        delta = (end_dt - start_dt).days
        if delta < 0: delta = 0
        
        target_searches = 5
        step = max(1, delta // target_searches)
        current_dt = start_dt

        headers = {
            "Authorization": f"Bearer {keys.duffel_token}",
            "Duffel-Version": "v1",
            "Content-Type": "application/json"
        }

        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            print(f"Duffel: Checking {date_str}...")
            
            payload = {
                "data": {
                    "slices": [
                        {
                            "origin": config.origin,
                            "destination": config.destination,
                            "departure_date": date_str
                        }
                    ],
                    "passengers": [],
                    "cabin_class": config.cabin_class.lower()
                }
            }
            
            # Add passengers. Duffel expects adult, child, infant_without_seat
            for _ in range(config.adults):
                payload["data"]["passengers"].append({"type": "adult"})
            for _ in range(config.infants_on_lap):
                payload["data"]["passengers"].append({"type": "infant_without_seat"})

            url = "https://api.duffel.com/air/offer_requests"
            
            try:
                # 1. Create Offer Request
                resp = requests.post(url, headers=headers, json=payload)
                if resp.status_code in [200, 201]:
                    data = resp.json().get("data", {})
                    # Offer request returns initial offers
                    for offer in data.get("offers", []):
                        parsed = self._parse_offer(offer, date_str, config)
                        if parsed:
                            offers.append(parsed)
                else:
                    print(f"Duffel search failed: {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"Duffel search error: {e}")
                
            current_dt += timedelta(days=step)
            if step == 0: break

        return offers

    def _parse_offer(self, offer: dict, date_str: str, config: SearchConfig) -> Optional[FlightOffer]:
        try:
            price_total = float(offer.get("total_amount", "99999"))
            currency = offer.get("total_currency", "EUR")
            
            slices = offer.get("slices", [])
            if not slices: return None
            
            segments = slices[0].get("segments", [])
            if not segments: return None
            
            airlines = list(set([seg.get("operating_carrier", {}).get("iata_code", "Unknown") for seg in segments if seg.get("operating_carrier")]))
            flight_numbers = [seg.get("operating_carrier_flight_number", "Unknown") for seg in segments]
            
            # Parse duration from ISO 8601 string
            duration_iso = slices[0].get("duration", "PT0H0M")
            dur_mins = 0
            if "H" in duration_iso:
                h_part = duration_iso.split("H")[0].replace("PT", "")
                if h_part.isdigit(): dur_mins += int(h_part) * 60
            if "M" in duration_iso:
                m_part = duration_iso.split("M")[0].split("H")[-1].replace("PT", "")
                if m_part.isdigit(): dur_mins += int(m_part)
                
            local_dep = segments[0].get("departing_at", "TBD").split("T")[-1][:5]
            local_arr = segments[-1].get("arriving_at", "TBD").split("T")[-1][:5]
            
            # Fare basis and booking class from first passenger, first segment
            fare_basis = None
            booking_class = None
            passengers = segments[0].get("passengers", [])
            if passengers:
                fare_basis = passengers[0].get("fare_basis_code")
                booking_class = passengers[0].get("cabin_class_marketing_name") or passengers[0].get("cabin_class")
                
            # Duffel returns actual bookable offers. We can link to our own mock UI or say "API Booking"
            return FlightOffer(
                source=self.name(),
                price_eur=price_total, # We will normalize later
                price_original=price_total,
                currency_original=currency,
                origin=config.origin,
                destination=config.destination,
                departure_date=date_str,
                departure_time=local_dep,
                arrival_time=local_arr,
                duration_minutes=dur_mins,
                stops=len(segments) - 1,
                airlines=airlines,
                flight_numbers=flight_numbers,
                fare_basis=fare_basis,
                booking_class=booking_class,
                cabin=config.cabin_class,
                point_of_sale="Duffel Global",
                booking_url="#", # Actual booking requires Duffel Create Order API
                booking_method="GET",
                booking_post_data=None,
                raw_data=offer
            )
        except Exception:
            return None
