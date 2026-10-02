import json
import boto3
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
sns      = boto3.client("sns", region_name="us-east-1")
ses      = boto3.client("ses",  region_name="us-east-1")

TABLE_SOURCES  = dynamodb.Table(os.environ["DYNAMODB_TABLE_SOURCES"])
TABLE_NUTRI    = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_NUTRI",  "nutriroute-nutri-scores"))
TABLE_USERS    = dynamodb.Table(os.environ["DYNAMODB_TABLE_USERS"])
SNS_TOPIC_ARN  = os.environ["SNS_TOPIC_ARN"]


def lambda_handler(event, context):
    source = event.get("source", "aws.events")
    detail = event.get("detail-type", "")

    # EventBridge: pantry check every 30 min
    if source == "aws.events" and "pantry" in event.get("resources", [""])[0].lower():
        return _run_pantry_check()

    # EventBridge: weekly NutriScore report every Sunday
    if source == "aws.events" and "nutriscore" in event.get("resources", [""])[0].lower():
        return _run_nutriscore_report()

    # EventBridge: daily SNAP reminder
    if source == "aws.events":
        return _run_snap_reminder()

    # REST: manual trigger (admin)
    body   = json.loads(event.get("body", "{}"))
    action = body.get("action", "pantry_check")
    if action == "pantry_check":
        return _ok(_run_pantry_check())
    if action == "nutriscore":
        return _ok(_run_nutriscore_report())
    return _ok({"message": "alert-engine ready"})


# ── Alert jobs ───────────────────────────────────────────────────────────────

def _run_pantry_check():
    """Scan all food sources, detect restocks, push SNS alerts."""
    resp    = TABLE_SOURCES.scan(ProjectionExpression="sourceId, zipCode, #n, sourceType",
                                  ExpressionAttributeNames={"#n": "name"})
    sources = resp.get("Items", [])
    alerts  = 0

    for src in sources:
        source_id = src["sourceId"]
        old_level = _get_stock_level(source_id)
        new_level = _simulate_stock_check(source_id)   # replace with real API in prod

        if old_level in ("low", "empty") and new_level in ("high", "medium"):
            _send_restock_alert(src, new_level)
            alerts += 1

    return {"pantryChecks": len(sources), "alertsSent": alerts,
            "checkedAt": datetime.now(timezone.utc).isoformat()}


def _run_nutriscore_report():
    """Send weekly NutriScore email to all users who improved."""
    resp  = TABLE_NUTRI.scan()
    items = resp.get("Items", [])
    sent  = 0

    user_scores: dict = {}
    for item in items:
        uid   = item["userId"]
        score = int(item.get("score", 0))
        week  = item.get("weekOf", "")
        if uid not in user_scores or week > user_scores[uid]["week"]:
            user_scores[uid] = {"score": score, "week": week}

    for uid, data in user_scores.items():
        user = _get_user(uid)
        email = user.get("email", "")
        if email and data["score"] > 70:
            _send_nutriscore_email(email, data["score"])
            sent += 1

    return {"usersProcessed": len(user_scores), "emailsSent": sent}


def _run_snap_reminder():
    """Remind users 3 days before SNAP renewal to plan meals."""
    today    = datetime.now(timezone.utc).date()
    reminder = (today + timedelta(days=3)).strftime("%d")
    resp     = TABLE_USERS.scan(
        FilterExpression="snapRenewalDay = :d",
        ExpressionAttributeValues={":d": reminder},
    )
    sent = 0
    for user in resp.get("Items", []):
        phone = user.get("phone", "")
        if phone:
            _send_snap_sms(phone, user.get("snapBalance", 0))
            sent += 1
    return {"remindersSent": sent}


# ── Notification senders ─────────────────────────────────────────────────────

def _send_restock_alert(source, stock_level):
    message = (
        f"🥦 {source.get('name', 'Food Bank')} just restocked! "
        f"Stock: {stock_level.upper()}. "
        f"Open NutriRoute to plan your trip now."
    )
    try:
        sns.publish(
            TopicArn  = SNS_TOPIC_ARN,
            Message   = message,
            Subject   = "Food Bank Restocked Near You",
            MessageAttributes={
                "sourceId":  {"DataType": "String", "StringValue": source.get("sourceId", "")},
                "alertType": {"DataType": "String", "StringValue": "restock"},
            },
        )
    except Exception:
        pass


def _send_nutriscore_email(email, score):
    try:
        ses.send_email(
            Source      = "noreply@nutriroute.ai",
            Destination = {"ToAddresses": [email]},
            Message={
                "Subject": {"Data": f"Your NutriScore this week: {score}/100 🥦"},
                "Body": {"Text": {"Data": (
                    f"Great job! Your family's nutrition score this week is {score}/100.\n\n"
                    f"Keep using NutriRoute to plan meals and improve your score.\n\n"
                    f"Open the app to see this week's meal plan."
                )}},
            },
        )
    except Exception:
        pass


def _send_snap_sms(phone, balance):
    message = (
        f"NutriRoute: Your SNAP benefits renew in 3 days. "
        f"Current balance: ${balance}. "
        f"Open the app to plan your month's meals and save up to $47."
    )
    try:
        sns.publish(PhoneNumber=phone, Message=message)
    except Exception:
        pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_stock_level(source_id):
    try:
        resp = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_INVENTORY", "nutriroute-inventory")).get_item(
            Key={"sourceId": source_id, "itemCategory": "summary"}
        )
        return resp.get("Item", {}).get("stockLevel", "unknown")
    except Exception:
        return "unknown"


def _simulate_stock_check(source_id):
    """In production: call 211.org API. For demo: return medium."""
    return "medium"


def _get_user(user_id):
    try:
        resp = TABLE_USERS.get_item(Key={"userId": user_id, "profileType": "profile"})
        return resp.get("Item", {})
    except Exception:
        return {}


def _ok(body):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }
