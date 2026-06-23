import urllib.request
import xml.etree.ElementTree as ET
from typing import List
from ..models import SearchConfig, APIKeys, FlightOffer
from .base import FlightSource
import re

class FlyerTalkScraper(FlightSource):
    def name(self) -> str:
        return "flyertalk_error_fares"

    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        offers = []
        # Premium Fare Deals often appear in Mileage Run Deals (Forum 372)
        url = "https://www.flyertalk.com/forum/external.php?type=RSS2&forumids=372"
        
        print(f"FlyerTalk Scraper: Fetching RSS from {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            
            for item in root.findall('./channel/item'):
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                # Check if it's a business class deal (simple heuristic)
                if not any(kw in title.upper() for kw in ["BIZ", "BUSINESS", "FIRST", "J", "F ", "PREMIUM"]):
                    continue
                
                # Extract the price from the title using regex
                price_match = re.search(r"(\$|€|£)\s*(\d{3,4})|(\d{3,4})\s*(EUR|USD|GBP)", title.upper())
                price_val = 0.0
                currency = "EUR"
                if price_match:
                    try:
                        price_val = float(price_match.group(2) or price_match.group(3))
                        if "$" in title: currency = "USD"
                        elif "£" in title: currency = "GBP"
                    except:
                        pass
                else:
                    continue # Skip if no clear price found in title
                    
                offers.append(FlightOffer(
                    source=self.name(),
                    price_eur=price_val, # Assume 1:1 for simplicity; aggregator will normalize
                    price_original=price_val,
                    currency_original=currency,
                    origin="VAR",
                    destination="VAR",
                    departure_date="See Thread",
                    departure_time="TBD",
                    arrival_time="TBD",
                    duration_minutes=0,
                    stops=0,
                    airlines=["Forum Deal"],
                    flight_numbers=["TBD"],
                    fare_basis="ERROR_FARE",
                    booking_class="Business",
                    cabin="business",
                    point_of_sale="Global",
                    booking_url=link,
                    booking_method="GET",
                    booking_post_data=None,
                    raw_data={"title": title}
                ))
        except Exception as e:
            print(f"FlyerTalk Scraper Error: {e}")
            
        return offers
