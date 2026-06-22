import os
import requests
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader

DUFFEL_API_KEY = os.environ.get("DUFFEL_API_KEY")
DATE_FROM = os.environ.get("DATE_FROM", "2026-07-01")
DATE_TO = os.environ.get("DATE_TO", "2026-08-31")
CABIN_CLASS = os.environ.get("CABIN_CLASS", "business").lower()
ORIGIN = os.environ.get("ORIGIN", "FRA")
DESTINATION = os.environ.get("DESTINATION", "HYD")

def format_duration(duration_str):
    # Duffel duration format: "PT14H30M" (ISO 8601)
    if not duration_str: return ""
    s = duration_str.replace('PT', '')
    s = s.replace('H', 'h ')
    s = s.replace('M', 'm')
    return s.strip()

def fetch_flights_for_date(date_str):
    print(f"Checking {date_str} on Duffel...")
    
    url = "https://api.duffel.com/air/offer_requests"
    headers = {
        "Authorization": f"Bearer {DUFFEL_API_KEY}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "data": {
            "passengers": [
                {"type": "adult"},
                {"type": "adult"},
                {"type": "infant_without_seat"}
            ],
            "slices": [
                {
                    "origin": ORIGIN,
                    "destination": DESTINATION,
                    "departure_date": date_str
                }
            ],
            "cabin_class": CABIN_CLASS
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200 and response.status_code != 201:
            print(f"Error fetching for {date_str}: {response.text}")
            return []
            
        data = response.json().get("data", {})
        offers = data.get("offers", [])
            
        flights = []
        for offer in offers:
            slice_data = offer.get("slices", [])[0]
            segments = slice_data.get("segments", [])
            
            if not segments:
                continue
                
            departure_dt = datetime.fromisoformat(segments[0]["departing_at"].replace("Z", "+00:00"))
            arrival_dt = datetime.fromisoformat(segments[-1]["arriving_at"].replace("Z", "+00:00"))
            
            airlines = list(set([seg.get("marketing_carrier", {}).get("name", "Unknown") for seg in segments]))
            
            flights.append({
                "price": float(offer.get("total_amount", 0)),
                "flyFrom": ORIGIN,
                "flyTo": DESTINATION,
                "departure_date": departure_dt.strftime("%a, %b %d, %Y"),
                "local_departure": departure_dt.strftime("%H:%M"),
                "local_arrival": arrival_dt.strftime("%H:%M"),
                "duration": format_duration(slice_data.get("duration", "")),
                "airlines": airlines,
                "route_count": len(segments),
                "deep_link": f"https://www.google.com/flights?q=flights+from+{ORIGIN}+to+{DESTINATION}+on+{date_str}" 
            })
            
        return flights
    except Exception as e:
        print(f"Exception fetching for {date_str}: {e}")
        return []

def fetch_flights():
    if not DUFFEL_API_KEY:
        print("Error: DUFFEL_API_KEY environment variable not set.")
        return []
        
    try:
        start_dt = datetime.strptime(DATE_FROM, "%Y-%m-%d")
        end_dt = datetime.strptime(DATE_TO, "%Y-%m-%d")
    except:
        start_dt = datetime.strptime("2026-07-01", "%Y-%m-%d")
        end_dt = datetime.strptime("2026-07-05", "%Y-%m-%d")
        
    delta = (end_dt - start_dt).days
    if delta < 0: delta = 0
    step = max(1, delta // 7)
    
    all_flights = []
    print(f"Sweeping NDC flights from {ORIGIN} to {DESTINATION} between {DATE_FROM} and {DATE_TO} in {CABIN_CLASS} class...")
    
    current_dt = start_dt
    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        daily_flights = fetch_flights_for_date(date_str)
        all_flights.extend(daily_flights)
        current_dt += timedelta(days=step)
        if step == 0: break
        
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
        cabin_class=CABIN_CLASS.capitalize(),
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
            f.write(f"## Top NDC Deals ({ORIGIN} ➔ {DESTINATION} | {CABIN_CLASS.capitalize()})\n\n")
            f.write("| Date | Departure | Price | Airlines | Duration |\n")
            f.write("|------|-----------|-------|----------|----------|\n")
            for fl in flights[:5]:
                f.write(f"| {fl['departure_date']} | {fl['local_departure']} | €{fl['price']} | {', '.join(fl['airlines'])} | {fl['duration']} |\n")
            f.write("\n> View the full dashboard on GitHub Pages for the lowest 20 options!\n")

if __name__ == "__main__":
    flights = fetch_flights()
    generate_html(flights)
