import json
import boto3
import os
import requests
from decimal import Decimal
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
location = boto3.client("location", region_name="us-east-1")
secrets = boto3.client("secretsmanager", region_name="us-east-1")

TABLE_SOURCES = dynamodb.Table(os.environ["DYNAMODB_TABLE_SOURCES"])
TABLE_INVENTORY = dynamodb.Table(os.environ["DYNAMODB_TABLE_INVENTORY"])
PLACE_INDEX = os.environ["LOCATION_PLACE_INDEX"]

AGENT_INSTRUCTIONS = """
You are the NutriRoute FoodFinder Agent. Your job is to find real food sources near a given zip code.

You have access to:
- search_food_sources: finds food banks, pantries, stores near a zip code
- check_stock: gets real-time inventory for a specific food source
- verify_snap_acceptance: confirms if a source accepts SNAP/EBT

Always return sources sorted by: trust score (highest first), then distance (nearest first).
Always include: name, address, distance, hours, stock level, SNAP acceptance, trust score.
Filter out sources with trust score below 60.
Flag sources with stock level "empty" — do not recommend them.
"""


def lambda_handler(event, context):
    action_group = event.get("actionGroup", "")
    function_name = event.get("function", "")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    if function_name == "search_food_sources":
        result = search_food_sources(
            parameters.get("zip_code"),
            parameters.get("source_types", "all"),
            parameters.get("snap_required", "false") == "true",
            int(parameters.get("radius_miles", 5)),
        )
    elif function_name == "check_stock":
        result = check_stock(parameters.get("source_id"))
    elif function_name == "verify_snap_acceptance":
        result = verify_snap_acceptance(parameters.get("source_id"))
    else:
        result = {"error": f"Unknown function: {function_name}"}

    return {
        "actionGroup": action_group,
        "function": function_name,
        "functionResponse": {"responseBody": {"TEXT": {"body": json.dumps(result)}}},
    }


def search_food_sources(zip_code, source_types, snap_required, radius_miles):
    geo = location.search_place_index_for_text(
        IndexName=PLACE_INDEX,
        Text=zip_code,
        MaxResults=1,
    )
    if not geo.get("Results"):
        return {"error": "Zip code not found", "sources": []}

    coords = geo["Results"][0]["Place"]["Geometry"]["Point"]
    lng, lat = coords[0], coords[1]

    response = TABLE_SOURCES.query(
        IndexName="byType-index",
        KeyConditionExpression="zipCode = :zip",
        ExpressionAttributeValues={":zip": zip_code},
    )

    sources = []
    for item in response.get("Items", []):
        if snap_required and not item.get("snapAccepted"):
            continue
        if source_types != "all" and item.get("sourceType") not in source_types.split(","):
            continue
        trust_score = int(item.get("trustScore", 0))
        if trust_score < 60:
            continue

        stock = check_stock(item["sourceId"])
        if stock.get("stockLevel") == "empty":
            continue

        distance = _haversine(lat, lng, float(item.get("lat", 0)), float(item.get("lng", 0)))
        if distance > radius_miles:
            continue

        sources.append({
            "sourceId": item["sourceId"],
            "name": item["name"],
            "address": item["address"],
            "distanceMiles": round(distance, 1),
            "sourceType": item["sourceType"],
            "hours": item.get("hours", {}),
            "snapAccepted": item.get("snapAccepted", False),
            "wicAccepted": item.get("wicAccepted", False),
            "trustScore": trust_score,
            "stockLevel": stock.get("stockLevel", "unknown"),
            "availableItems": stock.get("items", []),
            "phone": item.get("phone", ""),
            "lat": float(item.get("lat", 0)),
            "lng": float(item.get("lng", 0)),
        })

    sources.sort(key=lambda x: (-x["trustScore"], x["distanceMiles"]))
    return {"sources": sources[:10], "totalFound": len(sources), "zipCode": zip_code}


def check_stock(source_id):
    response = TABLE_INVENTORY.get_item(Key={"sourceId": source_id, "itemCategory": "summary"})
    item = response.get("Item", {})
    return {
        "sourceId": source_id,
        "stockLevel": item.get("stockLevel", "unknown"),
        "items": item.get("items", []),
        "lastUpdated": item.get("lastUpdated", ""),
        "verifiedBy": item.get("verifiedBy", "system"),
    }


def verify_snap_acceptance(source_id):
    response = TABLE_SOURCES.get_item(
        Key={"sourceId": source_id, "zipCode": source_id.split("#")[2] if "#" in source_id else "00000"}
    )
    item = response.get("Item", {})
    return {
        "sourceId": source_id,
        "snapAccepted": item.get("snapAccepted", False),
        "wicAccepted": item.get("wicAccepted", False),
        "ebtAccepted": item.get("ebtAccepted", False),
    }


def _haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))
