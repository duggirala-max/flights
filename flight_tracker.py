import os
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from serpapi import GoogleSearch

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
DATE_FROM = os.environ.get("DATE_FROM", "2026-07-01")
DATE_TO = os.environ.get("DATE_TO", "2026-08-31")
CABIN_CLASS = os.environ.get("CABIN_CLASS", "BUSINESS").upper()
ORIGIN = os.environ.get("ORIGIN", "FRA")
DESTINATION = os.environ.get("DESTINATION", "HYD")

# The hacker matrix: Sweeping Point of Sale (PoS) to exploit Geo-Arbitrage
# We keep the currency as EUR so we can easily compare apples to apples,
# but we trick Google into thinking the searcher is in these countries.
GEO_LOCATIONS = [
    {"gl": "de", "name": "Germany"},
    {"gl": "in", "name": "India"},
    {"gl": "br", "name": "Brazil"},
    {"gl": "vn", "name": "Vietnam"},
    {"gl": "za", "name": "South Africa"},
    {"gl": "tr", "name": "Turkey"}
]

def map_cabin_class(c_class):
    c = c_class.upper()
    if c == "ECONOMY": return "1"
    if c == "PREMIUM_ECONOMY": return "2"
    if c == "BUSINESS": return "3"
    if c == "FIRST": return "4"
    return "3" # Default Business

def fetch_flights_for_geo(date_str, geo):
    print(f"Checking {date_str} disguised from {geo['name']} (Geo: {geo['gl']})...")
    
    params = {
      "engine": "google_flights",
      "departure_id": ORIGIN,
      "arrival_id": DESTINATION,
      "outbound_date": date_str,
      "type": "2", # 2 = One-way
      "travel_class": map_cabin_class(CABIN_CLASS),
      "adults": "2",
      "infants_on_lap": "1",
      "gl": geo["gl"],
      "hl": "en",
      "currency": "EUR",
      "api_key": SERPAPI_KEY
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Google Flights separates "best_flights" and "other_flights"
        best_flights = results.get("best_flights", [])
        other_flights = results.get("other_flights", [])
        
        all_options = best_flights + other_flights
        parsed_flights = []
        
        for flight in all_options:
            price = flight.get("price")
            if not price: continue
            
            # Flights usually have flights[0] for the specific legs
            legs = flight.get("flights", [])
            if not legs: continue
            
            departure_time = legs[0].get("departure_token", "") # Actually they provide departure_airport etc
            # better to extract from the legs
            airlines = list(set([leg.get("airline", "Unknown") for leg in legs]))
            
            # Sometimes price is an integer, sometimes float
            try:
                price_val = float(price)
            except:
                price_val = 99999.0
            
            total_duration = flight.get("total_duration", 0)
            dur_hours = total_duration // 60
            dur_mins = total_duration % 60
            dur_str = f"{dur_hours}h {dur_mins}m"
            
            parsed_flights.append({
                "price": price_val,
                "flyFrom": ORIGIN,
                "flyTo": DESTINATION,
                "departure_date": date_str,
                "local_departure": legs[0].get("departure_airport", {}).get("time", "TBD").split(" ")[0] if legs else "TBD",
                "local_arrival": legs[-1].get("arrival_airport", {}).get("time", "TBD").split(" ")[0] if legs else "TBD",
                "duration": dur_str,
                "airlines": airlines,
                "route_count": len(legs),
                "point_of_sale": geo['name'],
                "deep_link": flight.get("booking_token", f"https://www.google.com/flights?q=flights+from+{ORIGIN}+to+{DESTINATION}+on+{date_str}") 
                # Note: booking_token is not a URL, but SerpApi provides a Google Search link sometimes. 
                # Let's construct a general Google Flights link for safety.
            })
            
        return parsed_flights
    except Exception as e:
        print(f"Exception fetching for {date_str} in {geo['name']}: {e}")
        return []

def fetch_flights():
    if not SERPAPI_KEY:
        print("Error: SERPAPI_KEY environment variable not set.")
        return []
        
    try:
        start_dt = datetime.strptime(DATE_FROM, "%Y-%m-%d")
        end_dt = datetime.strptime(DATE_TO, "%Y-%m-%d")
    except:
        start_dt = datetime.strptime("2026-07-01", "%Y-%m-%d")
        end_dt = datetime.strptime("2026-07-05", "%Y-%m-%d")
        
    delta = (end_dt - start_dt).days
    if delta < 0: delta = 0
    # To save SerpApi searches (100 free/mo), we sweep dates but limit to top 3 geo-locations 
    # and maybe jump by 3-4 days to stay within limits if the date range is huge.
    # Total searches = (delta / step) * len(GEO_LOCATIONS)
    # We want to keep total searches per run under 30 to not burn the free tier immediately.
    
    target_searches = 30
    num_geos = 3 # Let's only use the top 3 geo-locations to save tokens
    active_geos = GEO_LOCATIONS[:num_geos]
    
    dates_to_check = max(1, target_searches // num_geos)
    step = max(1, delta // dates_to_check)
    
    all_flights = []
    print(f"Initiating Geo-Arbitrage Sweep from {ORIGIN} to {DESTINATION}")
    print(f"Dates: {DATE_FROM} to {DATE_TO} | Class: {CABIN_CLASS}")
    
    current_dt = start_dt
    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        for geo in active_geos:
            geo_flights = fetch_flights_for_geo(date_str, geo)
            all_flights.extend(geo_flights)
            
        current_dt += timedelta(days=step)
        if step == 0: break
        
    all_flights.sort(key=lambda x: x["price"])
    
    # Deduplicate exact same flights found across different geos, keeping the cheapest one.
    seen_flights = {}
    deduped_flights = []
    for fl in all_flights:
        uid = f"{fl['departure_date']}_{fl['local_departure']}_{'-'.join(fl['airlines'])}"
        if uid not in seen_flights:
            seen_flights[uid] = True
            fl['deep_link'] = f"https://www.google.com/travel/flights?q=Flights%20to%20{DESTINATION}%20from%20{ORIGIN}%20on%20{fl['departure_date']}%20one-way"
            deduped_flights.append(fl)
            
    return deduped_flights[:30]

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
            f.write(f"## Top Geo-Arbitrage Deals ({ORIGIN} ➔ {DESTINATION} | {CABIN_CLASS.capitalize()})\n\n")
            f.write("| Date | Price | Airlines | Duration | Point of Sale |\n")
            f.write("|------|-------|----------|----------|---------------|\n")
            for fl in flights[:10]:
                f.write(f"| {fl['departure_date']} | €{fl['price']} | {', '.join(fl['airlines'])} | {fl['duration']} | **{fl['point_of_sale']}** |\n")
            f.write("\n> View the full dashboard on GitHub Pages for all options!\n")

if __name__ == "__main__":
    flights = fetch_flights()
    generate_html(flights)
