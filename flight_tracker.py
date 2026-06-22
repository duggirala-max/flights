import os
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from duffel_api import Duffel

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

def fetch_flights_for_date(date_str, client):
    print(f"Checking {date_str} on Duffel...")
    try:
        # We query explicitly for 2 Adults and 1 Infant (lap)
        offer_request = client.offer_requests.create() \
            .passengers([{"type": "adult"}, {"type": "adult"}, {"type": "infant_without_seat"}]) \
            .slices([{"origin": ORIGIN, "destination": DESTINATION, "departure_date": date_str}]) \
            .cabin_class(CABIN_CLASS) \
            .execute()
            
        flights = []
        for offer in offer_request.offers:
            # We want single ticket with checked baggage, Duffel handles this.
            slice = offer.slices[0]
            segments = slice.segments
            
            departure_dt = datetime.fromisoformat(segments[0].departing_at)
            arrival_dt = datetime.fromisoformat(segments[-1].arriving_at)
            
            airlines = list(set([seg.marketing_carrier.name for seg in segments]))
            
            flights.append({
                "price": float(offer.total_amount),
                "flyFrom": ORIGIN,
                "flyTo": DESTINATION,
                "departure_date": departure_dt.strftime("%a, %b %d, %Y"),
                "local_departure": departure_dt.strftime("%H:%M"),
                "local_arrival": arrival_dt.strftime("%H:%M"),
                "duration": format_duration(slice.duration),
                "airlines": airlines,
                "route_count": len(segments),
                "deep_link": f"https://www.google.com/flights?q=flights+from+{ORIGIN}+to+{DESTINATION}+on+{date_str}" 
            })
            
        return flights
    except Exception as e:
        print(f"Error fetching for {date_str}: {e}")
        return []

def fetch_flights():
    if not DUFFEL_API_KEY:
        print("Error: DUFFEL_API_KEY environment variable not set.")
        return []
        
    client = Duffel(access_token=DUFFEL_API_KEY)
    
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
        daily_flights = fetch_flights_for_date(date_str, client)
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
