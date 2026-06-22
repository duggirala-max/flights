import os
import requests
import json
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader

API_KEY = os.environ.get("AMADEUS_API_KEY")
API_SECRET = os.environ.get("AMADEUS_API_SECRET")
DATE_FROM = os.environ.get("DATE_FROM", "2026-07-01")
DATE_TO = os.environ.get("DATE_TO", "2026-08-31")
CABIN_CLASS = os.environ.get("CABIN_CLASS", "BUSINESS") # or ECONOMY
ORIGIN = os.environ.get("ORIGIN", "FRA")
DESTINATION = os.environ.get("DESTINATION", "HYD")

def get_amadeus_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": API_SECRET
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def format_duration(pt_string):
    # Amadeus returns duration like PT14H30M
    s = pt_string.replace('PT', '')
    s = s.replace('H', 'h ')
    s = s.replace('M', 'm')
    return s.strip()

def fetch_flights_for_date(date_str, token):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": ORIGIN,
        "destinationLocationCode": DESTINATION,
        "departureDate": date_str,
        "adults": 2,
        "infants": 1,
        "travelClass": CABIN_CLASS.upper(),
        "currencyCode": "EUR",
        "max": 10
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return []
        data = response.json()
        
        flights = []
        for offer in data.get("data", []):
            itinerary = offer["itineraries"][0]
            segments = itinerary["segments"]
            
            departure = segments[0]["departure"]["at"]
            arrival = segments[-1]["arrival"]["at"]
            duration = itinerary.get("duration", "")
            
            airlines = list(set([seg["carrierCode"] for seg in segments]))
            price = float(offer["price"]["total"])
            
            dep_dt = datetime.fromisoformat(departure)
            arr_dt = datetime.fromisoformat(arrival)
            
            flights.append({
                "price": price,
                "flyFrom": ORIGIN,
                "flyTo": DESTINATION,
                "departure_date": dep_dt.strftime("%a, %b %d, %Y"),
                "local_departure": dep_dt.strftime("%H:%M"),
                "local_arrival": arr_dt.strftime("%H:%M"),
                "duration": format_duration(duration),
                "airlines": airlines,
                "route_count": len(segments),
                "deep_link": "https://www.google.com/flights?q=flights+from+" + ORIGIN + "+to+" + DESTINATION + "+on+" + date_str # Amadeus test doesn't give deep links natively, so we fallback to a search link
            })
        return flights
    except Exception as e:
        print(f"Error fetching flights for {date_str}: {e}")
        return []

def fetch_flights():
    if not API_KEY or not API_SECRET:
        print("Error: AMADEUS_API_KEY or AMADEUS_API_SECRET environment variables not set.")
        return []
        
    try:
        token = get_amadeus_token()
    except Exception as e:
        print(f"Error getting Amadeus token: {e}")
        return []
    
    # We will sample 5 different dates evenly spread across the date range to avoid hitting API limits too fast
    try:
        start_dt = datetime.strptime(DATE_FROM, "%Y-%m-%d")
        end_dt = datetime.strptime(DATE_TO, "%Y-%m-%d")
    except:
        start_dt = datetime.strptime("2026-07-01", "%Y-%m-%d")
        end_dt = datetime.strptime("2026-07-05", "%Y-%m-%d")
        
    delta = (end_dt - start_dt).days
    if delta < 0: delta = 0
    
    # Check max 7 dates to keep the GitHub action fast and within rate limits
    step = max(1, delta // 7)
    
    all_flights = []
    print(f"Sweeping flights from {ORIGIN} to {DESTINATION} between {DATE_FROM} and {DATE_TO} in {CABIN_CLASS} class...")
    
    current_dt = start_dt
    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        print(f"Checking {date_str}...")
        daily_flights = fetch_flights_for_date(date_str, token)
        all_flights.extend(daily_flights)
        current_dt += timedelta(days=step)
        if step == 0: break
        
    # Sort by price and get top 20
    all_flights.sort(key=lambda x: x["price"])
    return all_flights[:20]

def generate_html(flights):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('template.html')
    
    html_out = template.render(
        origin=ORIGIN,
        destination=DESTINATION,
        date_from=DATE_FROM,
        date_to=DATE_TO,
        cabin_class=CABIN_CLASS,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        flights=flights
    )
    
    os.makedirs('output', exist_ok=True)
    with open('output/index.html', 'w', encoding='utf-8') as f:
        f.write(html_out)
    
    print("Dashboard generated at output/index.html")
    
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path and flights:
        with open(summary_path, 'a', encoding='utf-8') as f:
            f.write(f"## Top Flight Deals ({ORIGIN} ➔ {DESTINATION} | {CABIN_CLASS})\n\n")
            f.write("| Date | Departure | Price | Airlines | Duration |\n")
            f.write("|------|-----------|-------|----------|----------|\n")
            for fl in flights[:5]:
                f.write(f"| {fl['departure_date']} | {fl['local_departure']} | €{fl['price']} | {', '.join(fl['airlines'])} | {fl['duration']} |\n")
            f.write("\n> The results have been deployed to your GitHub Pages dashboard!\n")

if __name__ == "__main__":
    flights = fetch_flights()
    generate_html(flights)
