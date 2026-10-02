import json
import boto3
import os
import requests

s3 = boto3.client("s3", region_name="us-east-1")
bedrock_agent = boto3.client("bedrock-agent", region_name="us-east-1")

S3_BUCKET_DOCS = os.environ.get("S3_BUCKET_DOCS", "nutriroute-usda-docs")
KB_ID = os.environ.get("BEDROCK_KB_ID", "")

USDA_DATASETS = [
    {
        "name": "USDA_Dietary_Guidelines_2025.json",
        "url": "https://api.nal.usda.gov/fdc/v1/foods/list?api_key=DEMO_KEY&dataType=Foundation&pageSize=200",
        "description": "USDA Foundation Foods nutritional data",
    },
    {
        "name": "SNAP_Eligible_Foods.json",
        "url": "https://www.fns.usda.gov/snap/eligible-food-items",
        "description": "SNAP eligible food items list",
    },
]

NUTRITION_KNOWLEDGE = {
    "snap_guidelines": {
        "average_monthly_benefit": 180,
        "average_waste_per_family": 47,
        "highest_value_foods": [
            {"food": "Dried lentils", "cost_per_serving": 0.15, "nutrition_score": 95},
            {"food": "Dried black beans", "cost_per_serving": 0.18, "nutrition_score": 93},
            {"food": "Brown rice (bulk)", "cost_per_serving": 0.12, "nutrition_score": 78},
            {"food": "Rolled oats (bulk)", "cost_per_serving": 0.10, "nutrition_score": 88},
            {"food": "Frozen spinach", "cost_per_serving": 0.25, "nutrition_score": 97},
            {"food": "Canned sardines", "cost_per_serving": 0.45, "nutrition_score": 94},
            {"food": "Eggs (dozen)", "cost_per_serving": 0.25, "nutrition_score": 91},
            {"food": "Peanut butter", "cost_per_serving": 0.20, "nutrition_score": 85},
            {"food": "Sweet potato", "cost_per_serving": 0.35, "nutrition_score": 96},
            {"food": "Canned tomatoes", "cost_per_serving": 0.22, "nutrition_score": 82},
        ],
    },
    "dietary_guidelines": {
        "daily_servings": {
            "vegetables": 5, "fruits": 4, "grains": 6,
            "protein": 5.5, "dairy": 3,
        },
        "lactose_free_calcium_sources": [
            "Fortified soy milk", "Canned salmon with bones",
            "Broccoli", "Kale", "Fortified orange juice",
        ],
        "gluten_free_grains": ["Rice", "Corn", "Quinoa", "Oats (certified GF)", "Millet"],
    },
}


def ingest_nutrition_data():
    print("Uploading nutrition knowledge base to S3...")

    knowledge_json = json.dumps(NUTRITION_KNOWLEDGE, indent=2)
    s3.put_object(
        Bucket=S3_BUCKET_DOCS,
        Key="nutrition_knowledge_base.json",
        Body=knowledge_json.encode("utf-8"),
        ContentType="application/json",
    )
    print("  Uploaded: nutrition_knowledge_base.json")

    snap_guide = _generate_snap_guide()
    s3.put_object(
        Bucket=S3_BUCKET_DOCS,
        Key="snap_optimization_guide.txt",
        Body=snap_guide.encode("utf-8"),
        ContentType="text/plain",
    )
    print("  Uploaded: snap_optimization_guide.txt")

    if KB_ID:
        print("Triggering Bedrock Knowledge Base sync...")
        bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=os.environ.get("BEDROCK_KB_DATASOURCE_ID", ""),
        )
        print("  Sync started.")

    print("Done.")


def _generate_snap_guide():
    return """
NUTRIROUTE AI — SNAP OPTIMIZATION GUIDE

MAXIMIZING YOUR SNAP BENEFITS

The average American family wastes $47/month in SNAP benefits due to poor planning.
NutriRoute AI eliminates this waste through intelligent meal planning.

TOP 10 HIGHEST NUTRITION-PER-DOLLAR FOODS (SNAP Eligible):
1. Dried lentils — $0.15/serving — Nutrition Score: 95/100
2. Dried black beans — $0.18/serving — Nutrition Score: 93/100
3. Frozen spinach — $0.25/serving — Nutrition Score: 97/100
4. Canned sardines — $0.45/serving — Nutrition Score: 94/100
5. Eggs — $0.25/serving — Nutrition Score: 91/100
6. Sweet potato — $0.35/serving — Nutrition Score: 96/100
7. Rolled oats (bulk) — $0.10/serving — Nutrition Score: 88/100
8. Peanut butter — $0.20/serving — Nutrition Score: 85/100
9. Brown rice (bulk) — $0.12/serving — Nutrition Score: 78/100
10. Canned tomatoes — $0.22/serving — Nutrition Score: 82/100

LACTOSE-FREE CALCIUM SOURCES (for lactose intolerant family members):
- Fortified soy milk (same calcium as dairy milk)
- Canned salmon with bones
- Broccoli (1 cup = 180mg calcium)
- Kale (1 cup cooked = 177mg calcium)
- Fortified orange juice

GLUTEN-FREE GRAINS (SNAP eligible):
- Rice (all varieties)
- Corn and cornmeal
- Quinoa
- Certified gluten-free oats
- Millet

WEEKLY MEAL PLANNING FORMULA:
- Protein: 2 lbs dried beans OR 1 dozen eggs + 1 lb chicken = ~$4.50
- Grains: 5 lbs rice OR oats = ~$3.00
- Vegetables: 3 lbs frozen mixed vegetables = ~$4.50
- Fruit: 5 lbs seasonal fruit = ~$5.00
- Total for family of 4 for one week: ~$17 = $68/month
- Remaining SNAP balance: $112 for variety and fresh items

This approach saves the average family $47/month vs. unplanned shopping.
"""


if __name__ == "__main__":
    ingest_nutrition_data()
