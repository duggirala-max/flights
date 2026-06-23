from serpapi import GoogleSearch
import os
import json

params = {
  "engine": "google_flights",
  "departure_id": "FRA",
  "arrival_id": "HYD",
  "outbound_date": "2026-07-01",
  "type": "2",
  "travel_class": "3",
  "adults": "2",
  "infants_on_lap": "1",
  "gl": "de",
  "hl": "en",
  "currency": "EUR",
  "api_key": os.environ.get("SERPAPI_KEY")
}

search = GoogleSearch(params)
results = search.get_dict()

# Let's save a sample of the results
with open("test_serp_out.json", "w") as f:
    json.dump(results, f, indent=2)

print("Done")
