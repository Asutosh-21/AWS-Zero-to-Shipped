import json
import boto3
import os
from datetime import datetime, timezone

dynamodb             = boto3.resource("dynamodb", region_name="us-east-1")
bedrock_agent_rt     = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

TABLE_USERS      = dynamodb.Table(os.environ["DYNAMODB_TABLE_USERS"])
TABLE_NUTRI      = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_NUTRI", "nutriroute-nutri-scores"))
KB_ID            = os.environ["BEDROCK_KB_ID"]


def lambda_handler(event, context):
    # Bedrock Agent invocation
    if "actionGroup" in event:
        return _handle_agent_action(event)

    # REST: GET /mealplan
    body     = json.loads(event.get("body", "{}"))
    user_id  = event.get("requestContext", {}).get("authorizer", {}).get("sub", "anonymous")
    result   = _generate_meal_plan(
        snap_balance          = float(body.get("snapBalance", 180)),
        family_size           = int(body.get("familySize", 4)),
        dietary_restrictions  = body.get("dietaryRestrictions", "none"),
        available_foods       = body.get("availableFoods", []),
        days                  = int(body.get("days", 7)),
    )
    _save_nutri_score(user_id, result.get("nutritionScore", 75))
    return _ok(result)


# ── Bedrock Agent dispatcher ─────────────────────────────────────────────────

def _handle_agent_action(event):
    fn         = event.get("function", "")
    action_grp = event.get("actionGroup", "")
    params     = {p["name"]: p["value"] for p in event.get("parameters", [])}

    dispatch = {
        "generate_meal_plan":   lambda: _generate_meal_plan(
            snap_balance         = float(params.get("snap_balance", 180)),
            family_size          = int(params.get("family_size", 4)),
            dietary_restrictions = params.get("dietary_restrictions", "none"),
            available_foods      = json.loads(params.get("available_foods", "[]")),
            days                 = int(params.get("days", 7)),
        ),
        "optimize_snap_budget": lambda: _optimize_snap(
            float(params.get("snap_balance", 180)),
            int(params.get("family_size", 4)),
        ),
        "calculate_nutrition":  lambda: _calc_nutrition(
            json.loads(params.get("meal_plan", "[]"))
        ),
        "dietary_filter":       lambda: _dietary_filter(
            json.loads(params.get("meals", "[]")),
            params.get("restrictions", ""),
        ),
    }

    result = dispatch.get(fn, lambda: {"error": f"Unknown function: {fn}"})()
    return {
        "actionGroup": action_grp,
        "function": fn,
        "functionResponse": {"responseBody": {"TEXT": {"body": json.dumps(result)}}},
    }


# ── Core logic ───────────────────────────────────────────────────────────────

def _generate_meal_plan(snap_balance, family_size, dietary_restrictions, available_foods, days):
    daily_budget  = snap_balance / 30
    weekly_budget = daily_budget * days
    is_dairy_free = any(k in dietary_restrictions.lower() for k in ["lactose", "dairy"])
    is_gluten_free = "gluten" in dietary_restrictions.lower()
    is_vegan      = "vegan" in dietary_restrictions.lower()
    is_halal      = "halal" in dietary_restrictions.lower()

    templates = _meal_templates(is_dairy_free, is_gluten_free, is_vegan, is_halal)
    plan       = []
    total_cost = 0.0

    for day in range(1, days + 1):
        idx = (day - 1) % 3
        breakfast = templates["breakfast"][idx]
        lunch     = templates["lunch"][idx]
        dinner    = templates["dinner"][idx]
        day_cost  = (breakfast["cost"] + lunch["cost"] + dinner["cost"]) * family_size
        total_cost += day_cost
        plan.append({
            "day":       day,
            "breakfast": breakfast,
            "lunch":     lunch,
            "dinner":    dinner,
            "dayCost":   round(day_cost, 2),
        })

    avg_waste = 47.0
    savings   = round(avg_waste - max(0, snap_balance - total_cost - (snap_balance - weekly_budget * (30 / days))), 2)

    return {
        "mealPlan":            plan,
        "totalCost":           round(total_cost, 2),
        "weeklyBudget":        round(weekly_budget, 2),
        "snapBalance":         snap_balance,
        "estimatedSavings":    max(0.0, savings),
        "costPerMeal":         round(total_cost / (days * 3 * family_size), 2),
        "familySize":          family_size,
        "dietaryRestrictions": dietary_restrictions,
        "nutritionScore":      _avg_score(plan),
        "shoppingList":        _shopping_list(plan),
        "days":                days,
    }


def _optimize_snap(snap_balance, family_size):
    daily  = snap_balance / 30
    return {
        "snapBalance":          snap_balance,
        "dailyBudget":          round(daily, 2),
        "costPerPersonPerDay":  round(daily / family_size, 2),
        "costPerMeal":          round(daily / family_size / 3, 2),
        "averageAmericanWaste": 47.0,
        "tips": [
            "Dried beans vs canned — 60% cheaper, same nutrition",
            "Frozen vegetables = same nutrition as fresh, 40% less cost",
            "Bulk rice and oats = highest nutrition-per-dollar",
            "Whole chicken vs parts — 35% cheaper per pound",
        ],
    }


def _calc_nutrition(meal_plan):
    score = _avg_score(meal_plan)
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D"
    return {"nutritionScore": score, "grade": grade}


def _dietary_filter(meals, restrictions):
    tags = [r.strip().lower() for r in restrictions.split(",")]
    filtered = [m for m in meals if all(t in [x.lower() for x in m.get("dietaryTags", [])] for t in tags)]
    return {"filteredMeals": filtered, "count": len(filtered)}


# ── Meal templates ───────────────────────────────────────────────────────────

def _meal_templates(dairy_free, gluten_free, vegan, halal):
    B = [
        {"name": "Oatmeal with banana",          "cost": 0.45, "prepTime": 5,  "nutrition": 82,
         "dietaryTags": ["dairy-free", "vegan", "gluten-free-oats", "halal"]},
        {"name": "Scrambled eggs with toast",     "cost": 0.60, "prepTime": 8,  "nutrition": 78,
         "dietaryTags": ["vegetarian", "halal"] + (["dairy-free"] if dairy_free else [])},
        {"name": "Rice porridge with fruit",      "cost": 0.40, "prepTime": 10, "nutrition": 75,
         "dietaryTags": ["dairy-free", "gluten-free", "vegan", "halal"]},
    ]
    L = [
        {"name": "Bean and rice bowl",            "cost": 0.55, "prepTime": 15, "nutrition": 88,
         "dietaryTags": ["dairy-free", "gluten-free", "vegan", "halal"]},
        {"name": "Vegetable soup with bread",     "cost": 0.65, "prepTime": 20, "nutrition": 85,
         "dietaryTags": ["dairy-free", "vegan", "halal"]},
        {"name": "Egg salad sandwich",            "cost": 0.70, "prepTime": 10, "nutrition": 80,
         "dietaryTags": ["vegetarian", "halal"] + (["dairy-free"] if dairy_free else [])},
    ]
    D = [
        {"name": "Chicken stir-fry with rice",   "cost": 1.20, "prepTime": 25, "nutrition": 91,
         "dietaryTags": ["dairy-free", "gluten-free", "halal"]},
        {"name": "Lentil soup with cornbread",   "cost": 0.85, "prepTime": 30, "nutrition": 89,
         "dietaryTags": ["dairy-free", "vegan", "halal"] + (["gluten-free"] if gluten_free else [])},
        {"name": "Baked potato with beans",      "cost": 0.75, "prepTime": 45, "nutrition": 86,
         "dietaryTags": ["dairy-free", "gluten-free", "vegan", "halal"]},
    ]

    def _filter(meals):
        if dairy_free:  meals = [m for m in meals if "dairy-free"  in m["dietaryTags"]]
        if gluten_free: meals = [m for m in meals if "gluten-free" in m["dietaryTags"]]
        if vegan:       meals = [m for m in meals if "vegan"       in m["dietaryTags"]]
        if halal:       meals = [m for m in meals if "halal"       in m["dietaryTags"]]
        return meals or meals  # fallback: return unfiltered if all filtered out

    return {"breakfast": _filter(B) or B, "lunch": _filter(L) or L, "dinner": _filter(D) or D}


def _avg_score(plan):
    scores = []
    for day in plan:
        for key in ["breakfast", "lunch", "dinner"]:
            meal = day.get(key, {})
            if isinstance(meal, dict) and "nutrition" in meal:
                scores.append(meal["nutrition"])
    return round(sum(scores) / len(scores)) if scores else 75


def _shopping_list(plan):
    items: dict = {}
    ingredient_map = {
        "Oatmeal with banana":         [("Rolled oats", 1), ("Banana", 1)],
        "Scrambled eggs with toast":   [("Eggs", 2), ("Bread", 2)],
        "Rice porridge with fruit":    [("Rice", 0.5), ("Seasonal fruit", 1)],
        "Bean and rice bowl":          [("Dried black beans", 0.5), ("Rice", 0.5)],
        "Vegetable soup with bread":   [("Mixed vegetables", 1), ("Bread", 1)],
        "Egg salad sandwich":          [("Eggs", 2), ("Bread", 2)],
        "Chicken stir-fry with rice":  [("Chicken breast", 0.5), ("Rice", 0.5), ("Mixed vegetables", 0.5)],
        "Lentil soup with cornbread":  [("Dried lentils", 0.5), ("Cornmeal", 0.25)],
        "Baked potato with beans":     [("Potato", 1), ("Canned beans", 1)],
    }
    for day in plan:
        for key in ["breakfast", "lunch", "dinner"]:
            meal = day.get(key, {})
            if isinstance(meal, dict):
                for ing, qty in ingredient_map.get(meal.get("name", ""), []):
                    items[ing] = round(items.get(ing, 0) + qty, 2)
    return [{"item": k, "quantity": v, "unit": "lbs/units"} for k, v in items.items()]


def _save_nutri_score(user_id, score):
    if user_id == "anonymous":
        return
    week_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        TABLE_NUTRI.put_item(Item={
            "userId": user_id, "weekOf": week_of,
            "score": score, "recordedAt": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass


def _ok(body):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }
