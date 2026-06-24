import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

from src.config import load_config, load_api_keys
from src.models import SearchConfig
from src.sources.seats_aero import SeatsAeroSource
from src.history import HistoryDB
from src.aggregator import Aggregator

def generate_html(flights, config: SearchConfig):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('templates/dashboard.html')
    
    html_out = template.render(
        origin=config.origin,
        destination=config.destination,
        target_months=", ".join(config.target_months),
        cabin_classes=", ".join(config.cabin_classes).title(),
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        flights=flights
    )
    
    os.makedirs('output', exist_ok=True)
    with open('output/index.html', 'w', encoding='utf-8') as f:
        f.write(html_out)
    
    print("Dashboard generated at output/index.html")
    
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path and flights:
        with open(summary_path, 'a', encoding='utf-8') as f:
            f.write(f"## Top Stealth Deals ({config.origin} ➔ {config.destination} | {config.cabin_class})\n\n")
            f.write("| Date | Price | Airlines | Duration | PoS | Source | Anomaly |\n")
            f.write("|------|-------|----------|----------|-----|--------|---------|\n")
            for fl in flights[:15]:
                anomaly = "⚠️" if fl.anomaly_score > 0 else ""
                f.write(f"| {fl.departure_date} | €{fl.price_eur:.0f} | {', '.join(fl.airlines)} | {fl.duration_minutes//60}h {fl.duration_minutes%60}m | {fl.point_of_sale} | {fl.source} | {anomaly} |\n")
            f.write("\n> View the full dashboard on GitHub Pages for booking links!\n")

def main():
    config = load_config()
    keys = load_api_keys()

    # Initialize sources (Real Award Availability via Seats.aero)
    sources = [
        SeatsAeroSource()
    ]

    # Initialize DB
    db = HistoryDB()

    # Run Aggregator
    aggregator = Aggregator(sources, db)
    print("Starting Multi-Source Aggregator...")
    best_flights = aggregator.run(config, keys)

    print(f"Found {len(best_flights)} deduplicated flights.")

    # Generate Output
    generate_html(best_flights, config)

if __name__ == "__main__":
    main()
