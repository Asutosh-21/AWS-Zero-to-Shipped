import json
import boto3
import os
import base64
from datetime import datetime, timezone

rekognition = boto3.client("rekognition", region_name="us-east-1")
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
s3 = boto3.client("s3", region_name="us-east-1")

S3_BUCKET_UPLOADS      = os.environ["S3_BUCKET_UPLOADS"]
SUPERVISOR_AGENT_ID    = os.environ.get("BEDROCK_AGENT_SUPERVISOR_ID", "")
SUPERVISOR_AGENT_ALIAS = os.environ.get("BEDROCK_AGENT_SUPERVISOR_ALIAS", "LIVE")
NOVA_MODEL_ID          = "amazon.nova-lite-v1:0"

bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

FOOD_LABELS = {
    "Egg", "Rice", "Bread", "Milk", "Cheese", "Butter", "Yogurt",
    "Chicken", "Beef", "Pork", "Fish", "Shrimp", "Tuna",
    "Apple", "Banana", "Orange", "Tomato", "Potato", "Onion", "Carrot",
    "Broccoli", "Spinach", "Lettuce", "Corn", "Bean", "Lentil",
    "Pasta", "Flour", "Sugar", "Oil", "Sauce", "Soup", "Cereal",
    "Oat", "Peanut Butter", "Jam", "Canned Food", "Frozen Food",
}


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    image_base64 = body.get("image")
    user_id = event.get("requestContext", {}).get("authorizer", {}).get("sub", "anonymous")
    session_id = body.get("sessionId", context.aws_request_id)
    dietary_restrictions = body.get("dietaryRestrictions", "none")

    if not image_base64:
        return {"statusCode": 400, "body": json.dumps({"error": "image is required"})}

    image_bytes = base64.b64decode(image_base64)

    s3_key = f"user-uploads/{user_id}/{context.aws_request_id}.jpg"
    s3.put_object(Bucket=S3_BUCKET_UPLOADS, Key=s3_key, Body=image_bytes, ContentType="image/jpeg")

    rekognition_response = rekognition.detect_labels(
        Image={"Bytes": image_bytes},
        MaxLabels=50,
        MinConfidence=75,
    )

    detected_foods = []
    for label in rekognition_response.get("Labels", []):
        label_name = label["Name"]
        confidence = label["Confidence"]
        if label_name in FOOD_LABELS or any(food.lower() in label_name.lower() for food in FOOD_LABELS):
            detected_foods.append({
                "name": label_name,
                "confidence": round(confidence, 1),
            })

    if not detected_foods:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "detectedFoods": [],
                "mealSuggestions": [],
                "message": "No food items detected. Try better lighting or a closer photo.",
                "fallbackToManual": True,
            }),
        }

    food_names = [f["name"] for f in detected_foods]
    food_list = ", ".join(food_names)

    meal_query = (
        f"Generate 3 quick meals using ONLY these ingredients: {food_list}. "
        f"Dietary restrictions: {dietary_restrictions}. "
        f"Each meal must take under 30 minutes. Show nutrition score out of 100."
    )

    if SUPERVISOR_AGENT_ID:
        bedrock_response = bedrock_agent_runtime.invoke_agent(
            agentId=SUPERVISOR_AGENT_ID,
            agentAliasId=SUPERVISOR_AGENT_ALIAS,
            sessionId=f"foodlens-{session_id}",
            inputText=meal_query,
        )
        meal_plan_text = ""
        for event_stream in bedrock_response.get("completion", []):
            if "chunk" in event_stream:
                meal_plan_text += event_stream["chunk"].get("bytes", b"").decode("utf-8")
    else:
        payload = {
            "messages": [{"role": "user", "content": [{"text": meal_query}]}],
            "inferenceConfig": {"maxTokens": 1024, "temperature": 0.3},
        }
        resp = bedrock_runtime.invoke_model(
            modelId=NOVA_MODEL_ID, body=json.dumps(payload),
            contentType="application/json", accept="application/json",
        )
        result = json.loads(resp["body"].read())
        meal_plan_text = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({
            "detectedFoods": detected_foods,
            "foodCount": len(detected_foods),
            "mealSuggestions": meal_plan_text,
            "message": f"Found {len(detected_foods)} ingredients. Here's what you can make right now.",
            "imageKey": s3_key,
        }),
    }
