import requests
import time
from datetime import datetime, timedelta
from typing import List, Optional
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource

class AmadeusSource(FlightSource):
    def __init__(self):
        self.token: Optional[str] = None
        self.token_expiry: float = 0.0

    def name(self) -> str:
        return "amadeus"

    def _get_token(self, keys: APIKeys) -> Optional[str]:
        if not keys.amadeus_client_id or not keys.amadeus_client_secret:
            return None
            
        if self.token and time.time() < self.token_expiry:
            return self.token
            
        url = "https://api.amadeus.com/v1/security/oauth2/token" # use prod
        data = {
            "grant_type": "client_credentials",
            "client_id": keys.amadeus_client_id,
            "client_secret": keys.amadeus_client_secret
        }
        
        try:
            resp = requests.post(url, data=data)
            if resp.status_code == 200:
                body = resp.json()
                self.token = body.get("access_token")
                # Buffer 60 seconds
                self.token_expiry = time.time() + body.get("expires_in", 1800) - 60
                return self.token
            else:
                print(f"Amadeus auth failed: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            print(f"Amadeus auth error: {e}")
            return None

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        token = self._get_token(keys)
        if not token:
            print("Amadeus credentials missing or auth failed.")
            return []

        try:
            start_dt = datetime.strptime(config.date_from, "%Y-%m-%d")
            end_dt = datetime.strptime(config.date_to, "%Y-%m-%d")
        except ValueError:
            return []

        offers = []
        delta = (end_dt - start_dt).days
        if delta < 0: delta = 0
        
        # Determine step size to limit searches
        target_searches = 5 
        step = max(1, delta // target_searches)
        current_dt = start_dt

        headers = {"Authorization": f"Bearer {token}"}

        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            print(f"Amadeus: Checking {date_str}...")
            
            # Construct POST payload for more advanced filtering
            # 2 Adults, 1 Infant on lap
            payload = {
                "currencyCode": "EUR",
                "originDestinations": [
                    {
                        "id": "1",
                        "originLocationCode": config.origin,
                        "destinationLocationCode": config.destination,
                        "departureDateTimeRange": { "date": date_str }
                    }
                ],
                "travelers": [],
                "sources": ["GDS"],
                "searchCriteria": {
                    "flightFilters": {
                        "cabinRestrictions": [
                            {
                                "cabin": config.cabin_class,
                                "coverage": "MOST_SEGMENTS",
                                "originDestinationIds": ["1"]
                            }
                        ]
                    }
                }
            }
            
            # Add travelers
            tid = 1
            for _ in range(config.adults):
                payload["travelers"].append({"id": str(tid), "travelerType": "ADULT"})
                tid += 1
            
            # Infants on lap need to be associated with an adult
            assoc_id = 1
            for _ in range(config.infants_on_lap):
                payload["travelers"].append({"id": str(tid), "travelerType": "HELD_INFANT", "associatedAdultId": str(assoc_id)})
                tid += 1
                assoc_id = min(assoc_id + 1, config.adults) # Associate with next adult if possible

            url = "https://api.amadeus.com/v2/shopping/flight-offers"
            
            try:
                resp = requests.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    for offer in data:
                        parsed = self._parse_offer(offer, date_str, config)
                        if parsed:
                            offers.append(parsed)
                else:
                    print(f"Amadeus search failed: {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"Amadeus search error: {e}")
                
            current_dt += timedelta(days=step)
            if step == 0: break

        return offers

    def _parse_offer(self, offer: dict, date_str: str, config: SearchConfig) -> Optional[FlightOffer]:
        try:
            price_total = float(offer.get("price", {}).get("total", "99999"))
            currency = offer.get("price", {}).get("currency", "EUR")
            
            itineraries = offer.get("itineraries", [])
            if not itineraries: return None
            
            segments = itineraries[0].get("segments", [])
            if not segments: return None
            
            airlines = list(set([seg.get("carrierCode", "Unknown") for seg in segments]))
            flight_numbers = [seg.get("number", "Unknown") for seg in segments]
            
            duration_iso = itineraries[0].get("duration", "PT0H0M")
            # Parse PT8H30M format roughly
            dur_mins = 0
            if "H" in duration_iso:
                h_part = duration_iso.split("H")[0].replace("PT", "")
                if h_part.isdigit(): dur_mins += int(h_part) * 60
            if "M" in duration_iso:
                m_part = duration_iso.split("M")[0].split("H")[-1].replace("PT", "")
                if m_part.isdigit(): dur_mins += int(m_part)
                
            local_dep = segments[0].get("departure", {}).get("at", "TBD").split("T")[-1][:5]
            local_arr = segments[-1].get("arrival", {}).get("at", "TBD").split("T")[-1][:5]
            
            # Get fare basis and booking class from first traveler, first segment
            fare_basis = None
            booking_class = None
            traveler_pricings = offer.get("travelerPricings", [])
            if traveler_pricings:
                seg_details = traveler_pricings[0].get("fareDetailsBySegment", [])
                if seg_details:
                    fare_basis = seg_details[0].get("fareBasis")
                    booking_class = seg_details[0].get("class")
                    
            return FlightOffer(
                source=self.name(),
                price_eur=price_total, # Assuming EUR since we requested EUR
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
                point_of_sale="Amadeus Global",
                booking_url="#", # Amadeus doesn't provide direct consumer deep links
                booking_method="GET",
                booking_post_data=None,
                raw_data=offer
            )
        except Exception:
            return None
