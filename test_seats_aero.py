import os
import requests
import json
from datetime import datetime

def test_seats_aero():
    api_key = os.environ.get("SEATS_AERO_KEY")
    if not api_key:
        print("Error: SEATS_AERO_KEY environment variable is missing.")
        print("Please export it: export SEATS_AERO_KEY='your_pro_key_here'")
        return

    url = "https://seats.aero/partnerapi/search"
    headers = {
        "Partner-Authorization": api_key,
        "Accept": "application/json"
    }

    params = {
        "origin": "FRA",
        "destination": "HYD",
        "cabin": "business",
        "source": "aeroplan",
        "start_date": "2026-07-01",
        "end_date": "2026-08-31"
    }

    print(f"Querying Seats.aero Partner API for FRA -> HYD on Aeroplan...")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            
            if not items:
                print("\nNo availability found for this specific route and date range.")
            else:
                print(f"\nFound {len(items)} results! Sample:")
                for item in items[:3]:
                    date = item.get("Date", "Unknown")
                    miles = item.get("JMileageCost", "N/A")
                    airlines = item.get("Airlines", "")
                    print(f"- {date}: FRA->HYD via {airlines} | Cost: {miles} miles")
        else:
            print("\nError response from API:")
            print(response.text)
            
    except Exception as e:
        print(f"\nRequest failed: {str(e)}")

if __name__ == "__main__":
    test_seats_aero()
