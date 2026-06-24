from typing import List
from .models import FlightOffer, SearchConfig

class OfferFilter:
    @staticmethod
    def filter_and_validate(offers: List[FlightOffer], config: SearchConfig) -> List[FlightOffer]:
        valid_offers = []
        
        for offer in offers:
            # 1. Family Safety Guardrails
            # No split ticketing or extremely long multi-leg stops with an infant
            if offer.stops > 2:
                # We reject flights with more than 2 stops for family safety
                offer.anomaly_reasons.append(f"Rejected: {offer.stops} stops is too many for an infant.")
                continue
                
            # If we had origin-arbitrage, we'd block distant ones here, 
            # but we only use Duffel (direct) and FlyerTalk (flexible origin) now.
            if offer.source == "duffel" and offer.origin != config.origin:
                continue

            # 2. (Cabin enforcement removed to allow Economy and Premium Economy)

            # 3. Passenger Count Normalization (for Duffel mostly)
            # Duffel returns the total price. We calculate per_adult for transparent UI display.
            # 2 Adults + 1 Infant ~ 2.1 "Adult Equivalent" portions of base fare
            # For simplicity in UI, we will just use division to get a Per Adult average.
            
            # Since FlyerTalk deals are usually "Per Person", and Duffel is "Total",
            # we distinguish them here.
            total_passengers = config.adults + (1 if config.infants_on_lap > 0 else 0)
            adult_equivalents = config.adults + (0.1 if config.infants_on_lap > 0 else 0)

            if offer.source == "flyertalk_error_fares":
                # Forum prices are almost always Per Adult. We calculate total.
                offer.raw_data["price_per_adult"] = offer.price_eur
                offer.price_eur = offer.price_eur * adult_equivalents
            else:
                # Duffel prices are Total. We calculate per adult.
                offer.raw_data["price_per_adult"] = offer.price_eur / adult_equivalents

            valid_offers.append(offer)
            
        return valid_offers
