from typing import List
from .models import FlightOffer
from .history import HistoryDB

class AnomalyDetector:
    def __init__(self, db: HistoryDB):
        self.db = db

    def analyze(self, offers: List[FlightOffer]):
        # Group offers by route
        routes = set(f"{o.origin}-{o.destination}" for o in offers)
        medians = {}
        
        for r in routes:
            parts = r.split("-")
            # Assume cabin is consistent in this run, or check per offer
            # For simplicity, we fetch median for the first cabin we see
            cabin = offers[0].cabin if offers else "BUSINESS"
            m = self.db.get_median_price(r, cabin)
            if m is not None:
                medians[r] = m

        for offer in offers:
            route = f"{offer.origin}-{offer.destination}"
            median = medians.get(route)
            
            # Rule 1: Price significantly below median
            if median and offer.price_eur < median * 0.6: # 40% below median
                offer.anomaly_score += 50
                offer.anomaly_reasons.append(f"Price is >40% below historical median (€{median:.0f})")

            # Rule 2: Suspicious Fare Basis / Cabin mismatch
            if offer.cabin.upper() == "BUSINESS" and offer.fare_basis:
                first_char = offer.fare_basis[0].upper()
                # Typical economy booking classes: Y, B, M, H, Q, K, L, V, S, N, O, T
                # If a business ticket has an economy fare basis, it's a huge red flag for mistake fare
                if first_char in ['Y', 'K', 'L', 'T', 'V', 'S']:
                    offer.anomaly_score += 40
                    offer.anomaly_reasons.append(f"Business class with Economy fare basis ({offer.fare_basis})")

            # Cap score at 100
            offer.anomaly_score = min(100, offer.anomaly_score)
