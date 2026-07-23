import os
from dotenv import load_dotenv

# Load .env
load_dotenv("/var/www/fundsarthi/fundsarthi/.env")

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from app import app
from extensions import db
from models.property import Property

geolocator = Nominatim(
    user_agent="fundsarthi_property_updater",
    timeout=10
)

geocode = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1
)

with app.app_context():

    properties = Property.query.all()

    total = len(properties)
    updated = 0
    skipped = 0

    print(f"\nFound {total} properties\n")

    for index, p in enumerate(properties, start=1):

        # Already has coordinates
        if p.latitude is not None and p.longitude is not None:
            skipped += 1
            print(f"[{index}/{total}] Skipped - {p.title}")
            continue

        if not p.city:
            skipped += 1
            print(f"[{index}/{total}] No city - {p.title}")
            continue

        address = ", ".join(
            filter(
                None,
                [
                    p.locality,
                    p.city,
                    "India"
                ]
            )
        )

        print(f"[{index}/{total}] Searching: {address}")

        try:

            location = geocode(address)

            if location:

                p.latitude = location.latitude
                p.longitude = location.longitude

                updated += 1

                print(
                    f"   ✓ {location.latitude}, {location.longitude}"
                )

            else:
                print("   ✗ Not Found")

            # Commit every 20 updates
            if updated % 20 == 0:
                db.session.commit()

        except Exception as e:
            print(f"   ERROR: {e}")

    db.session.commit()

    print("\n================================")
    print("Completed")
    print(f"Updated : {updated}")
    print(f"Skipped : {skipped}")
    print("================================")