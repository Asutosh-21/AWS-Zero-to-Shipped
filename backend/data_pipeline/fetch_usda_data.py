import json
import boto3
import os
import requests
from datetime import datetime, timezone
from decimal import Decimal

dynamodb       = boto3.resource("dynamodb", region_name="us-east-1")
TABLE_SOURCES  = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SOURCES", "nutriroute-food-sources"))
TABLE_INVENTORY = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_INVENTORY", "nutriroute-inventory"))

USDA_API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")
USDA_FDC_URL = "https://api.nal.usda.gov/fdc/v1"

# Top 10 food desert zip codes for the hackathon demo
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

# Seed data for demo — real addresses in each zip code
SEED_SOURCES = {
    "48201": [
        {"name": "Gleaners Community Food Bank",    "address": "2131 Beaufait St, Detroit, MI 48207",
         "lat": 42.3584, "lng": -83.0185, "sourceType": "foodBank",  "snapAccepted": True,  "trustScore": 94},
        {"name": "St. Mary's Food Pantry",          "address": "646 W. Willis St, Detroit, MI 48201",
         "lat": 42.3501, "lng": -83.0612, "sourceType": "pantry",    "snapAccepted": False, "trustScore": 88},
        {"name": "Detroit Community Fridge",        "address": "4201 Woodward Ave, Detroit, MI 48201",
         "lat": 42.3612, "lng": -83.0632, "sourceType": "fridge",    "snapAccepted": False, "trustScore": 82},
        {"name": "Save-A-Lot Michigan Ave",         "address": "8100 Michigan Ave, Detroit, MI 48210",
         "lat": 42.3298, "lng": -83.1012, "sourceType": "store",     "snapAccepted": True,  "trustScore": 91},
        {"name": "Eastern Market Shed 3",           "address": "2934 Russell St, Detroit, MI 48207",
         "lat": 42.3501, "lng": -83.0298, "sourceType": "market",    "snapAccepted": True,  "trustScore": 96},
    ],
    "60629": [
        {"name": "Greater Chicago Food Depository", "address": "4100 W Ann Lurie Pl, Chicago, IL 60632",
         "lat": 41.8198, "lng": -87.7298, "sourceType": "foodBank",  "snapAccepted": True,  "trustScore": 97},
        {"name": "Pilsen Food Pantry",              "address": "1818 S Paulina St, Chicago, IL 60608",
         "lat": 41.8562, "lng": -87.6698, "sourceType": "pantry",    "snapAccepted": False, "trustScore": 85},
        {"name": "Aldi West 63rd",                  "address": "6315 S Pulaski Rd, Chicago, IL 60629",
         "lat": 41.7798, "lng": -87.7248, "sourceType": "store",     "snapAccepted": True,  "trustScore": 93},
    ],
    "90011": [
        {"name": "LA Regional Food Bank",           "address": "1734 E 41st St, Los Angeles, CA 90058",
         "lat": 34.0098, "lng": -118.2198, "sourceType": "foodBank", "snapAccepted": True,  "trustScore": 96},
        {"name": "Proyecto Pastoral Food Pantry",   "address": "2715 Cesar Chavez Ave, Los Angeles, CA 90033",
         "lat": 34.0498, "lng": -118.2098, "sourceType": "pantry",   "snapAccepted": False, "trustScore": 89},
        {"name": "Superior Grocers Olympic",        "address": "4001 S Hooper Ave, Los Angeles, CA 90011",
         "lat": 34.0012, "lng": -118.2512, "sourceType": "store",    "snapAccepted": True,  "trustScore": 90},
    ],
}


def fetch_usda_data():
    """Seed food sources into DynamoDB for all target zip codes."""
    print("Seeding food sources into DynamoDB...")
    total = 0

    for zip_code, sources in SEED_SOURCES.items():
        for src in sources:
            source_id = f"{src['sourceType']}#{src['name'].lower().replace(' ', '-')[:20]}#{zip_code}"
            item = {
                "zipCode":     zip_code,
                "sourceId":    source_id,
                "name":        src["name"],
                "address":     src["address"],
                "lat":         Decimal(str(src["lat"])),
                "lng":         Decimal(str(src["lng"])),
                "sourceType":  src["sourceType"],
                "snapAccepted": src["snapAccepted"],
                "wicAccepted": src.get("wicAccepted", False),
                "ebtAccepted": src.get("snapAccepted", False),
                "trustScore":  Decimal(str(src["trustScore"])),
                "phone":       src.get("phone", ""),
                "hours": {
                    "monday":    "9am-4pm", "tuesday":   "9am-4pm",
                    "wednesday": "9am-4pm", "thursday":  "9am-4pm",
                    "friday":    "9am-3pm", "saturday":  "10am-2pm",
                    "sunday":    "closed",
                },
                "lastVerified": datetime.now(timezone.utc).isoformat(),
                "dataSource":   "seed",
            }
            TABLE_SOURCES.put_item(Item=item)

            # Seed inventory
            TABLE_INVENTORY.put_item(Item={
                "sourceId":    source_id,
                "itemCategory": "summary",
                "stockLevel":  "medium",
                "items":       ["produce", "canned goods", "bread", "protein"],
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "verifiedBy":  "seed",
            })
            total += 1
            print(f"  ✓ {src['name']} ({zip_code})")

    print(f"\nTotal seeded: {total} food sources across {len(SEED_SOURCES)} zip codes")
    return total


if __name__ == "__main__":
    count = fetch_usda_data()
    print(f"\nDone. {count} sources ready for demo.")
