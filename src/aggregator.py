from typing import List
from .models import FlightOffer, SearchConfig, APIKeys
from .sources.base import FlightSource
from .currency import CurrencyConverter
from .anomaly import AnomalyDetector
from .history import HistoryDB
from .filtering import OfferFilter

class Aggregator:
    def __init__(self, sources: List[FlightSource], db: HistoryDB):
        self.sources = sources
        self.currency_conv = CurrencyConverter()
        self.anomaly = AnomalyDetector(db)
        self.db = db

    def _map_awards(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        """Legacy function removed. Award mapping is now handled directly by Seats.aero source."""
        return offers

    def run(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        all_offers = []
        
        for source in self.sources:
            print(f"--- Running source: {source.name()} ---")
            try:
                offers = source.search(config, keys)
                all_offers.extend(offers)
            except Exception as e:
                print(f"Source {source.name()} failed: {e}")
            
        if not all_offers:
            return []

        # 1. Normalize currency
        for offer in all_offers:
            if offer.is_award_mapped and offer.award_taxes_original is not None:
                try:
                    offer.award_taxes_eur = self.currency_conv.to_eur(offer.award_taxes_original, offer.award_taxes_currency)
                except ValueError as e:
                    print(e)
                    offer.award_taxes_eur = offer.award_taxes_original # fallback
            else:
                try:
                    offer.price_eur = self.currency_conv.to_eur(offer.price_original, offer.currency_original)
                except ValueError as e:
                    print(e)

        # 1.5 Safety Guardrails & Passenger Math
        all_offers = OfferFilter.filter_and_validate(all_offers, config)

        if not all_offers:
            return []

        # 2. Deduplicate
        deduped = self._deduplicate(all_offers)
        
        # 3. Anomaly Detection
        self.anomaly.analyze(deduped)
        
        # Apply Predictive Award Mapping
        deduped = self._map_awards(deduped)
        
        # 4. Save to history
        self.db.save_offers(deduped)
        
        # 5. Sort by normalized price
        def sort_key(offer):
            if offer.is_award_mapped:
                # Sort primarily by miles, then taxes
                return (0, offer.award_miles or 0, offer.award_taxes_eur or 0.0)
            else:
                # Cash flights come after award flights
                return (1, offer.price_eur, 0.0)

        deduped.sort(key=sort_key)
        
        return deduped

    def _deduplicate(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        seen = {}
        for offer in offers:
            # Unique identifier for a flight
            fnums = "-".join(sorted([str(fn) for fn in offer.flight_numbers])) if offer.flight_numbers else "N/A"
            airlines = "-".join(sorted(offer.airlines)) if offer.airlines else "N/A"
            award_prog = offer.award_program or "cash"
            uid = f"{offer.departure_date}_{offer.origin}_{offer.destination}_{offer.cabin}_{airlines}_{fnums}_{award_prog}_{offer.price_eur:.2f}"
            
            if uid not in seen:
                seen[uid] = offer
            else:
                # Keep the cheapest one (which might mean a different PoS or source)
                existing = seen[uid]
                if offer.price_eur < existing.price_eur:
                    seen[uid] = offer
                    
        return list(seen.values())
