import os
import requests
import json

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
if not SERPAPI_KEY:
    print("No SERPAPI_KEY")
    exit(1)

# 1. Search Flights
search_url = "https://serpapi.com/search.json"
params = {
    "engine": "google_flights",
    "departure_id": "FRA",
    "arrival_id": "HYD",
    "outbound_date": "2026-08-01",
    "currency": "EUR",
    "hl": "en",
    "type": "2", # one-way
    "adults": 2,
    "infants_in_seat": 1, 
    "travel_class": "2", # business
    "api_key": SERPAPI_KEY
}

resp = requests.get(search_url, params=params)
data = resp.json()
flights = data.get("best_flights", [])
if not flights:
    flights = data.get("other_flights", [])

if not flights:
    print("No flights found")
    exit()

flight = flights[0]
print(f"Found Flight: {flight.get('price')} EUR - {flight.get('airline')}")
token = flight.get("booking_token")
if token:
    print(f"Resolving Token: {token[:20]}...")
    res_params = {
        "engine": "google_flights",
        "booking_token": token,
        "api_key": SERPAPI_KEY
    }
    r2 = requests.get(search_url, params=res_params)
    r2_data = r2.json()
    options = r2_data.get("booking_options", [])
    for opt in options:
        print(f"OTA: {opt.get('name')} - Price: {opt.get('price')} - URL: {opt.get('url')[:60]}")
