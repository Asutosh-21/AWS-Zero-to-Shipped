import json
import boto3
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

dynamodb        = boto3.resource("dynamodb", region_name="us-east-1")
TABLE_SOURCES   = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_SOURCES",   "nutriroute-food-sources"))
TABLE_INVENTORY = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_INVENTORY", "nutriroute-inventory"))

# Simulated stock rotation for demo realism
STOCK_ROTATION = ["high", "medium", "medium", "low", "medium", "high", "medium"]


def sync_inventory():
    """Refresh inventory TTL and simulate realistic stock fluctuation."""
    print("Syncing inventory for all food sources...")

    resp    = TABLE_SOURCES.scan(ProjectionExpression="sourceId, zipCode, #n",
                                  ExpressionAttributeNames={"#n": "name"})
    sources = resp.get("Items", [])
    updated = 0

    for src in sources:
        source_id  = src["sourceId"]
        day_of_week = datetime.now(timezone.utc).weekday()   # 0=Mon … 6=Sun
        stock_level = STOCK_ROTATION[day_of_week % len(STOCK_ROTATION)]

        expires_at = int((datetime.now(timezone.utc) + timedelta(hours=6)).timestamp())

        TABLE_INVENTORY.put_item(Item={
            "sourceId":     source_id,
            "itemCategory": "summary",
            "stockLevel":   stock_level,
            "items":        _stock_items(stock_level),
            "lastUpdated":  datetime.now(timezone.utc).isoformat(),
            "verifiedBy":   "sync",
            "expiresAt":    expires_at,
        })
        updated += 1

    print(f"Synced {updated} inventory records.")
    return updated


def _stock_items(level):
    base = ["canned goods", "rice", "beans"]
    if level == "high":
        return base + ["fresh produce", "bread", "eggs", "protein", "dairy alternatives", "frozen vegetables"]
    if level == "medium":
        return base + ["bread", "eggs", "frozen vegetables"]
    return base   # low


if __name__ == "__main__":
    count = sync_inventory()
    print(f"Done. {count} inventory records synced.")
