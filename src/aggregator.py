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
        """Maps cash flights to expected Award Program costs (Predictive Award Arbitrage)"""
        star_alliance = ["LH", "AI", "LX", "OS", "SN", "TK", "UA", "AC", "SQ"]
        oneworld = ["BA", "QR", "AY", "IB", "AA", "CX", "QF"]
        skyteam = ["AF", "KL", "DL", "SV"]

        for offer in offers:
            # Detect primary alliance
            alliance = None
            if any(a in star_alliance for a in offer.airlines):
                alliance = "Star Alliance"
                offer.award_program = "Air Canada Aeroplan"
                offer.award_miles = 60000 if offer.cabin.lower() == "business" else 40000
                offer.award_taxes_eur = 110.0
                offer.transfer_partners = ["Amex", "Chase", "Capital One"]
                offer.award_search_url = "https://www.aircanada.com/aeroplan/redeem/"
                offer.is_award_mapped = True
            elif any(a in oneworld for a in offer.airlines):
                alliance = "Oneworld"
                offer.award_program = "Qatar Privilege Club / BA Executive Club"
                offer.award_miles = 55000 if offer.cabin.lower() == "business" else 35000
                offer.award_taxes_eur = 180.0
                offer.transfer_partners = ["Amex", "Citi"]
                offer.award_search_url = "https://www.qatarairways.com/en/Privilege-Club/book-award-flight.html"
                offer.is_award_mapped = True
            elif any(a in skyteam for a in offer.airlines):
                alliance = "SkyTeam"
                offer.award_program = "Air France/KLM Flying Blue"
                offer.award_miles = 70000 if offer.cabin.lower() == "business" else 30000
                offer.award_taxes_eur = 250.0
                offer.transfer_partners = ["Amex", "Chase", "Citi", "Capital One"]
                offer.award_search_url = "https://www.airfrance.com/en/flyingblue/spend-miles/reward-tickets"
                offer.is_award_mapped = True

        return offers

    def run(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        all_offers = []
        
        for source in self.sources:
            print(f"--- Running source: {source.name()} ---")
            offers = source.search(config, keys)
            all_offers.extend(offers)
            
        if not all_offers:
            return []

        # 1. Normalize currency
        for offer in all_offers:
            offer.price_eur = self.currency_conv.to_eur(offer.price_original, offer.currency_original)

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
        deduped.sort(key=lambda x: x.price_eur)
        
        return deduped

    def _deduplicate(self, offers: List[FlightOffer]) -> List[FlightOffer]:
        seen = {}
        for offer in offers:
            # Unique identifier for a flight
            # Convert to str to prevent TypeError if a flight number is None
            fnums = "-".join(sorted([str(fn) for fn in offer.flight_numbers]))
            uid = f"{offer.departure_date}_{offer.departure_time}_{fnums}"
            
            if uid not in seen:
                seen[uid] = offer
            else:
                # Keep the cheapest one (which might mean a different PoS or source)
                existing = seen[uid]
                if offer.price_eur < existing.price_eur:
                    seen[uid] = offer
                    
        return list(seen.values())
