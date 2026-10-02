import json
import boto3
import os
import requests
from datetime import datetime, timezone
from decimal import Decimal

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
TABLE_SOURCES = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SOURCES", "nutriroute-food-sources"))

USDA_API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")
USDA_BASE = "https://api.nal.usda.gov/fdc/v1"
API_211_BASE = "https://api.211.org/search/v1"

TARGET_ZIPS = [
    "48201",  # Detroit, MI
    "60629",  # Chicago, IL
    "90011",  # Los Angeles, CA
    "77011",  # Houston, TX
    "19132",  # Philadelphia, PA
    "21217",  # Baltimore, MD
    "38106",  # Memphis, TN
    "70117",  # New Orleans, LA
    "44103",  # Cleveland, OH
    "07103",  # Newark, NJ
]


def fetch_food_banks():
    print(f"Fetching food banks for {len(TARGET_ZIPS)} zip codes...")
    total = 0

    for zip_code in TARGET_ZIPS:
        try:
            response = requests.get(
                f"{API_211_BASE}/organizations",
                params={"zip": zip_code, "category": "food", "radius": 5},
                timeout=10,
            )
            if response.status_code != 200:
                print(f"  {zip_code}: API error {response.status_code}")
                continue

            orgs = response.json().get("organizations", [])
            print(f"  {zip_code}: {len(orgs)} organizations found")

            for org in orgs:
                source_id = f"foodbank#{org.get('id', 'unknown')}#{zip_code}"
                item = {
                    "zipCode": zip_code,
                    "sourceId": source_id,
                    "name": org.get("name", "Unknown"),
                    "address": org.get("address", {}).get("street", ""),
                    "lat": Decimal(str(org.get("location", {}).get("lat", 0))),
                    "lng": Decimal(str(org.get("location", {}).get("lng", 0))),
                    "phone": org.get("phone", ""),
                    "sourceType": _classify_source_type(org),
                    "hours": org.get("hours", {}),
                    "snapAccepted": org.get("snap_accepted", False),
                    "wicAccepted": org.get("wic_accepted", False),
                    "ebtAccepted": org.get("ebt_accepted", False),
                    "trustScore": Decimal("75"),
                    "lastVerified": datetime.now(timezone.utc).isoformat(),
                    "dataSource": "211.org",
                }
                TABLE_SOURCES.put_item(Item=item)
                total += 1

        except Exception as e:
            print(f"  {zip_code}: Error — {e}")

    print(f"\nTotal food sources loaded: {total}")
    return total


def _classify_source_type(org):
    name = org.get("name", "").lower()
    services = [s.lower() for s in org.get("services", [])]
    if "pantry" in name or "pantry" in str(services):
        return "pantry"
    if "bank" in name or "food bank" in str(services):
        return "foodBank"
    if "fridge" in name or "community fridge" in str(services):
        return "fridge"
    if "market" in name or "farmers" in name:
        return "market"
    return "store"


if __name__ == "__main__":
    count = fetch_food_banks()
    print(f"Done. {count} food sources loaded into DynamoDB.")
