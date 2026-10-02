import json
import boto3
import os
from math import radians, sin, cos, sqrt, atan2

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
location_client = boto3.client("location", region_name="us-east-1")

TABLE_SOURCES   = dynamodb.Table(os.environ["DYNAMODB_TABLE_SOURCES"])
TABLE_INVENTORY = dynamodb.Table(os.environ["DYNAMODB_TABLE_INVENTORY"])
PLACE_INDEX     = os.environ["LOCATION_PLACE_INDEX"]


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "POST")
    path        = event.get("path", "/sources")

    # Bedrock Agent invocation
    if "actionGroup" in event:
        return _handle_agent_action(event)

    # REST API: GET /sources/{zipCode}
    if http_method == "GET" and "/sources/" in path:
        zip_code = event.get("pathParameters", {}).get("zip", "48201")
        snap_required = event.get("queryStringParameters", {}).get("snap", "false") == "true"
        result = _search_sources(zip_code, snap_required=snap_required)
        return _ok(result)

    # REST API: GET /impact/{zipCode}
    if http_method == "GET" and "/impact/" in path:
        zip_code = event.get("pathParameters", {}).get("zip", "48201")
        return _ok(_get_impact_metrics(zip_code))

    return _ok({"message": "food-finder ready"})


# ── Bedrock Agent action dispatcher ─────────────────────────────────────────

def _handle_agent_action(event):
    fn         = event.get("function", "")
    action_grp = event.get("actionGroup", "")
    params     = {p["name"]: p["value"] for p in event.get("parameters", [])}

    dispatch = {
        "search_food_sources":   lambda: _search_sources(
            params.get("zip_code", "48201"),
            source_types=params.get("source_types", "all"),
            snap_required=params.get("snap_required", "false") == "true",
            radius_miles=int(params.get("radius_miles", 5)),
        ),
        "check_stock":           lambda: _check_stock(params.get("source_id", "")),
        "verify_snap_acceptance": lambda: _verify_snap(params.get("source_id", "")),
    }

    result = dispatch.get(fn, lambda: {"error": f"Unknown function: {fn}"})()
    return {
        "actionGroup": action_grp,
        "function": fn,
        "functionResponse": {"responseBody": {"TEXT": {"body": json.dumps(result)}}},
    }


# ── Core logic ───────────────────────────────────────────────────────────────

def _search_sources(zip_code, source_types="all", snap_required=False, radius_miles=5):
    coords = _geocode(zip_code)
    if not coords:
        return {"error": "Zip code not found", "sources": []}

    user_lat, user_lng = coords

    resp  = TABLE_SOURCES.query(
        KeyConditionExpression="zipCode = :z",
        ExpressionAttributeValues={":z": zip_code},
    )
    items = resp.get("Items", [])

    sources = []
    for item in items:
        if snap_required and not item.get("snapAccepted"):
            continue
        if source_types != "all" and item.get("sourceType") not in source_types.split(","):
            continue
        trust = int(item.get("trustScore", 0))
        if trust < 60:
            continue

        stock = _check_stock(item["sourceId"])
        if stock.get("stockLevel") == "empty":
            continue

        dist = _haversine(user_lat, user_lng,
                          float(item.get("lat", 0)), float(item.get("lng", 0)))
        if dist > radius_miles:
            continue

        sources.append({
            "sourceId":     item["sourceId"],
            "name":         item.get("name", ""),
            "address":      item.get("address", ""),
            "distanceMiles": round(dist, 1),
            "sourceType":   item.get("sourceType", ""),
            "hours":        item.get("hours", {}),
            "snapAccepted": item.get("snapAccepted", False),
            "wicAccepted":  item.get("wicAccepted", False),
            "trustScore":   trust,
            "stockLevel":   stock.get("stockLevel", "unknown"),
            "availableItems": stock.get("items", []),
            "phone":        item.get("phone", ""),
            "lat":          float(item.get("lat", 0)),
            "lng":          float(item.get("lng", 0)),
        })

    sources.sort(key=lambda x: (-x["trustScore"], x["distanceMiles"]))
    return {"sources": sources[:10], "totalFound": len(sources), "zipCode": zip_code}


def _check_stock(source_id):
    resp = TABLE_INVENTORY.get_item(
        Key={"sourceId": source_id, "itemCategory": "summary"}
    )
    item = resp.get("Item", {})
    return {
        "sourceId":    source_id,
        "stockLevel":  item.get("stockLevel", "unknown"),
        "items":       item.get("items", []),
        "lastUpdated": item.get("lastUpdated", ""),
        "verifiedBy":  item.get("verifiedBy", "system"),
    }


def _verify_snap(source_id):
    resp = TABLE_SOURCES.scan(
        FilterExpression="sourceId = :s",
        ExpressionAttributeValues={":s": source_id},
        Limit=1,
    )
    item = resp.get("Items", [{}])[0]
    return {
        "sourceId":    source_id,
        "snapAccepted": item.get("snapAccepted", False),
        "wicAccepted":  item.get("wicAccepted", False),
        "ebtAccepted":  item.get("ebtAccepted", False),
    }


def _get_impact_metrics(zip_code):
    """Returns impact metrics for a zip code (seeded demo data for pilot zips)."""
    demo = {
        "48201": {"familiesServed": 847,  "mealsPlanned": 12400, "snapOptimized": 34200, "hoursSaved": 1948, "satisfactionRate": 94},
        "60629": {"familiesServed": 1240, "mealsPlanned": 18600, "snapOptimized": 58280, "hoursSaved": 2852, "satisfactionRate": 92},
        "90011": {"familiesServed": 1820, "mealsPlanned": 27300, "snapOptimized": 85540, "hoursSaved": 4186, "satisfactionRate": 96},
    }
    metrics = demo.get(zip_code, {"familiesServed": 0, "mealsPlanned": 0,
                                   "snapOptimized": 0, "hoursSaved": 0, "satisfactionRate": 0})
    metrics["zipCode"] = zip_code
    metrics["topZipCodes"] = [
        {"zip": "48201", "families": 847},
        {"zip": "60629", "families": 1240},
        {"zip": "90011", "families": 1820},
    ]
    return metrics


# ── Helpers ──────────────────────────────────────────────────────────────────

def _geocode(address):
    try:
        resp = location_client.search_place_index_for_text(
            IndexName=PLACE_INDEX, Text=address, MaxResults=1
        )
        results = resp.get("Results", [])
        if results:
            pt = results[0]["Place"]["Geometry"]["Point"]
            return pt[1], pt[0]   # lat, lng
    except Exception:
        pass
    return None


def _haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _ok(body):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }
