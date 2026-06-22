import sqlite3
import os
from datetime import datetime
from typing import List, Optional
from .models import FlightOffer

class HistoryDB:
    def __init__(self, db_path: str = "data/price_history.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route TEXT,
                departure_date TEXT,
                cabin TEXT,
                price_eur REAL,
                source TEXT,
                point_of_sale TEXT,
                flight_numbers TEXT,
                fare_basis TEXT,
                observed_at TEXT
            )
        ''')
        self.conn.commit()

    def save_offers(self, offers: List[FlightOffer]):
        cursor = self.conn.cursor()
        now = datetime.utcnow().isoformat()
        
        records = []
        for o in offers:
            route = f"{o.origin}-{o.destination}"
            flight_nums = ",".join(o.flight_numbers)
            records.append((
                route, o.departure_date, o.cabin, o.price_eur, 
                o.source, o.point_of_sale, flight_nums, o.fare_basis, now
            ))
            
        cursor.executemany('''
            INSERT INTO price_history 
            (route, departure_date, cabin, price_eur, source, point_of_sale, flight_numbers, fare_basis, observed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        self.conn.commit()

    def get_median_price(self, route: str, cabin: str, lookback_days: int = 30) -> Optional[float]:
        cursor = self.conn.cursor()
        # In SQLite, we can approximate median by sorting and getting middle element, 
        # but for simplicity let's just get average or basic median calculation
        cursor.execute('''
            SELECT price_eur FROM price_history 
            WHERE route = ? AND cabin = ? AND date(observed_at) >= date('now', ?)
            ORDER BY price_eur
        ''', (route, cabin, f'-{lookback_days} days'))
        
        prices = [row[0] for row in cursor.fetchall()]
        if not prices:
            return None
            
        n = len(prices)
        if n % 2 == 1:
            return prices[n//2]
        else:
            return sum(prices[n//2 - 1:n//2 + 1]) / 2.0
