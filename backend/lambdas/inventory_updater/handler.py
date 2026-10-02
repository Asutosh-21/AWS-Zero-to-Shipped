import json
import boto3
import os
import requests
from datetime import datetime, timezone, timedelta
from decimal import Decimal

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
sns = boto3.client("sns", region_name="us-east-1")
location = boto3.client("location", region_name="us-east-1")

TABLE_SOURCES = dynamodb.Table(os.environ["DYNAMODB_TABLE_SOURCES"])
TABLE_INVENTORY = dynamodb.Table(os.environ["DYNAMODB_TABLE_INVENTORY"])
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
GEOFENCE_COLLECTION = os.environ.get("LOCATION_GEOFENCE_COLLECTION", "nutriroute-geofences")

API_211_BASE = "https://api.211.org/search/v1"


def lambda_handler(event, context):
    source = event.get("source", "aws.events")

    if source == "aws.events":
        return sync_all_inventory()

    body = json.loads(event.get("body", "{}"))
    action = body.get("action", "update")

    if action == "update":
        return update_inventory(body)
    if action == "photo_verify":
        return photo_verify_inventory(body)

    return {"statusCode": 400, "body": json.dumps({"error": "Unknown action"})}


def sync_all_inventory():
    response = TABLE_SOURCES.scan(
        FilterExpression="attribute_exists(sourceId)",
        ProjectionExpression="sourceId, zipCode, #n, sourceType",
        ExpressionAttributeNames={"#n": "name"},
    )

    updated = 0
    alerts_sent = 0

    for source in response.get("Items", []):
        source_id = source["sourceId"]
        old_stock = _get_current_stock(source_id)
        new_stock = _fetch_211_stock(source_id, source.get("zipCode", ""))

        if new_stock and old_stock.get("stockLevel") != new_stock.get("stockLevel"):
            _update_stock_in_dynamo(source_id, new_stock)
            updated += 1

            if (old_stock.get("stockLevel") in ["low", "empty"] and
                    new_stock.get("stockLevel") in ["high", "medium"]):
                alerts_sent += _send_restock_alerts(source, new_stock)

    return {
        "statusCode": 200,
        "body": json.dumps({"sourcesUpdated": updated, "alertsSent": alerts_sent}),
    }


def update_inventory(body):
    source_id = body.get("sourceId")
    stock_level = body.get("stockLevel")
    items = body.get("items", [])
    updated_by = body.get("updatedBy", "ngo-admin")

    if not source_id or not stock_level:
        return {"statusCode": 400, "body": json.dumps({"error": "sourceId and stockLevel required"})}

    old_stock = _get_current_stock(source_id)
    _update_stock_in_dynamo(source_id, {"stockLevel": stock_level, "items": items, "verifiedBy": updated_by})
    _update_trust_score(source_id, verified=True)

    alerts_sent = 0
    if old_stock.get("stockLevel") in ["low", "empty"] and stock_level in ["high", "medium"]:
        source_info = {"sourceId": source_id, "name": body.get("sourceName", "Food Bank")}
        alerts_sent = _send_restock_alerts(source_info, {"stockLevel": stock_level, "items": items})

    return {
        "statusCode": 200,
        "body": json.dumps({"updated": True, "alertsSent": alerts_sent}),
    }


def photo_verify_inventory(body):
    source_id = body.get("sourceId")
    detected_items = body.get("detectedItems", [])
    reported_items = body.get("reportedItems", [])

    if not detected_items or not reported_items:
        return {"statusCode": 400, "body": json.dumps({"error": "detectedItems and reportedItems required"})}

    detected_names = {item.lower() for item in detected_items}
    reported_names = {item.lower() for item in reported_items}
    overlap = detected_names & reported_names
    accuracy = len(overlap) / max(len(reported_names), 1)

    _update_trust_score(source_id, verified=accuracy > 0.7, accuracy=accuracy)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "verified": accuracy > 0.7,
            "accuracyScore": round(accuracy * 100, 1),
            "matchedItems": list(overlap),
        }),
    }


def _get_current_stock(source_id):
    response = TABLE_INVENTORY.get_item(Key={"sourceId": source_id, "itemCategory": "summary"})
    return response.get("Item", {})


def _update_stock_in_dynamo(source_id, stock_data):
    expires_at = int((datetime.now(timezone.utc) + timedelta(hours=6)).timestamp())
    TABLE_INVENTORY.put_item(Item={
        "sourceId": source_id,
        "itemCategory": "summary",
        "stockLevel": stock_data.get("stockLevel", "unknown"),
        "items": stock_data.get("items", []),
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "verifiedBy": stock_data.get("verifiedBy", "system"),
        "expiresAt": expires_at,
    })


def _fetch_211_stock(source_id, zip_code):
    try:
        response = requests.get(
            f"{API_211_BASE}/organizations",
            params={"zip": zip_code, "category": "food"},
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            for org in data.get("organizations", []):
                if source_id in org.get("id", ""):
                    return {"stockLevel": "medium", "items": org.get("services", [])}
    except Exception:
        pass
    return None


def _send_restock_alerts(source, stock_data):
    message = (
        f"🥦 {source.get('name', 'Food Bank')} just restocked! "
        f"Stock level: {stock_data.get('stockLevel', 'available').upper()}. "
        f"Available items: {', '.join(stock_data.get('items', [])[:3])}. "
        f"Open NutriRoute to plan your trip."
    )
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject="Food Bank Restocked Near You",
            MessageAttributes={
                "sourceId": {"DataType": "String", "StringValue": source.get("sourceId", "")},
                "alertType": {"DataType": "String", "StringValue": "restock"},
            },
        )
        return 1
    except Exception:
        return 0


def _update_trust_score(source_id, verified=True, accuracy=1.0):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trust_table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_TRUST", "nutriroute-trust-scores"))
    try:
        trust_table.update_item(
            Key={"sourceId": source_id, "date": today},
            UpdateExpression="SET verificationCount = if_not_exists(verificationCount, :zero) + :one, "
                             "accuracyRate = :acc, lastCalculated = :now",
            ExpressionAttributeValues={
                ":zero": 0, ":one": 1,
                ":acc": Decimal(str(round(accuracy, 2))),
                ":now": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        pass
