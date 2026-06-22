import os
import requests
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

KIWI_API_KEY = os.environ.get("KIWI_API_KEY")
DATE_FROM = os.environ.get("DATE_FROM", "2026-06-22")
DATE_TO = os.environ.get("DATE_TO", "2026-12-31")
CABIN_CLASS = os.environ.get("CABIN_CLASS", "Business")
ORIGIN = os.environ.get("ORIGIN", "FRA")
DESTINATION = os.environ.get("DESTINATION", "HYD")

def format_date(date_str):
    # Convert YYYY-MM-DD to DD/MM/YYYY
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except:
        return date_str

def format_duration(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"

def fetch_flights():
    if not KIWI_API_KEY:
        print("Error: KIWI_API_KEY environment variable not set.")
        return []
        
    url = "https://api.tequila.kiwi.com/v2/search"
    headers = {
        "apikey": KIWI_API_KEY,
        "accept": "application/json"
    }
    
    cabin_map = {
        "Business": "C",
        "Economy": "M"
    }
    
    params = {
        "fly_from": ORIGIN,
        "fly_to": DESTINATION,
        "date_from": format_date(DATE_FROM),
        "date_to": format_date(DATE_TO),
        "adults": 2,
        "infants": 1,
        "selected_cabins": cabin_map.get(CABIN_CLASS, "C"),
        "curr": "EUR",
        "limit": 50,
        "sort": "price"
    }
    
    print(f"Searching flights from {ORIGIN} to {DESTINATION} for {DATE_FROM} - {DATE_TO} in {CABIN_CLASS} class...")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        flights = []
        for item in data.get("data", []):
            # FILTER OUT SELF TRANSFERS to ensure family safety (single-ticket)
            if item.get("virtual_interlining") is True:
                continue
                
            duration_secs = item.get("duration", {}).get("total", 0)
            if duration_secs == 0 and "duration" in item and isinstance(item["duration"], int):
                 duration_secs = item["duration"]
                 
            departure_datetime = datetime.strptime(item.get("local_departure", "").split('.')[0], "%Y-%m-%dT%H:%M:%S")
            arrival_datetime = datetime.strptime(item.get("local_arrival", "").split('.')[0], "%Y-%m-%dT%H:%M:%S")
            
            flights.append({
                "price": item.get("price"),
                "flyFrom": item.get("flyFrom"),
                "flyTo": item.get("flyTo"),
                "departure_date": departure_datetime.strftime("%a, %b %d, %Y"),
                "local_departure": departure_datetime.strftime("%H:%M"),
                "local_arrival": arrival_datetime.strftime("%H:%M"),
                "duration": format_duration(duration_secs),
                "airlines": item.get("airlines", []),
                "route_count": len(item.get("route", [])),
                "deep_link": item.get("deep_link")
            })
            
            if len(flights) >= 20: # Keep top 20 safe flights
                break
                
        return flights
    except Exception as e:
        print(f"Error fetching flights: {e}")
        return []

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
    
    # Also write a simple markdown summary for GitHub Actions Step Summary
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
