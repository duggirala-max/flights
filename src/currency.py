import requests
import xml.etree.ElementTree as ET
from typing import Dict

class CurrencyConverter:
    def __init__(self):
        self.rates: Dict[str, float] = {"EUR": 1.0}
        self._fetch_rates()

    def _fetch_rates(self):
        # Fetch ECB daily reference rates
        url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                # Parse XML: namespaces can be tricky, so we search by tag ending
                for cube in root.iter():
                    if 'currency' in cube.attrib and 'rate' in cube.attrib:
                        currency = cube.attrib['currency']
                        rate = float(cube.attrib['rate'])
                        self.rates[currency] = rate
        except Exception as e:
            print(f"Failed to fetch currency rates: {e}")
            # Fallback approximate rates (mid-2026)
            fallback = {
                "INR": 90.0,
                "BRL": 5.5,
                "VND": 27000.0,
                "ZAR": 20.0,
                "TRY": 35.0,
                "USD": 1.1,
                "GBP": 0.85
            }
            self.rates.update(fallback)

    def to_eur(self, amount: float, currency: str) -> float:
        currency = currency.upper()
        if currency == "EUR":
            return amount
        if currency in self.rates:
            return amount / self.rates[currency]
        raise ValueError(f"Unknown currency: {currency}")
