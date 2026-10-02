import json
import boto3
import os
from math import radians, sin, cos, sqrt, atan2

location_client = boto3.client("location", region_name="us-east-1")

ROUTE_CALCULATOR = os.environ["LOCATION_ROUTER_NAME"]
PLACE_INDEX      = os.environ["LOCATION_PLACE_INDEX"]


def lambda_handler(event, context):
    # Bedrock Agent invocation
    if "actionGroup" in event:
        return _handle_agent_action(event)

    # REST: GET /route
    params = event.get("queryStringParameters") or {}
    origin      = params.get("origin", "")
    destination = params.get("destination", "")
    mode        = params.get("mode", "Walking")

    if not origin or not destination:
        return _err("origin and destination are required")

    result = _calculate_route(origin, destination, mode)
    return _ok(result)


# ── Bedrock Agent dispatcher ─────────────────────────────────────────────────

def _handle_agent_action(event):
    fn         = event.get("function", "")
    action_grp = event.get("actionGroup", "")
    params     = {p["name"]: p["value"] for p in event.get("parameters", [])}

    dispatch = {
        "calculate_route":      lambda: _calculate_route(
            params.get("origin", ""),
            params.get("destination", ""),
            params.get("transport_mode", "Walking"),
        ),
        "multi_stop_optimize":  lambda: _multi_stop(
            params.get("origin", ""),
            json.loads(params.get("stops", "[]")),
            params.get("transport_mode", "Walking"),
        ),
        "estimate_travel_time": lambda: _estimate_time(
            params.get("origin", ""),
            params.get("destination", ""),
        ),
    }

    result = dispatch.get(fn, lambda: {"error": f"Unknown function: {fn}"})()
    return {
        "actionGroup": action_grp,
        "function": fn,
        "functionResponse": {"responseBody": {"TEXT": {"body": json.dumps(result)}}},
    }


# ── Core logic ───────────────────────────────────────────────────────────────

def _calculate_route(origin, destination, transport_mode="Walking"):
    origin_coords = _geocode(origin)
    dest_coords   = _geocode(destination)

    if not origin_coords or not dest_coords:
        return {"error": "Could not geocode one or both locations"}

    try:
        resp    = location_client.calculate_route(
            CalculatorName      = ROUTE_CALCULATOR,
            DeparturePosition   = [origin_coords[1], origin_coords[0]],   # [lng, lat]
            DestinationPosition = [dest_coords[1],   dest_coords[0]],
            TravelMode          = transport_mode,
            IncludeLegGeometry  = False,
        )
        summary  = resp.get("Summary", {})
        dist_mi  = round(summary.get("Distance", 0) * 0.621371, 2)
        dur_min  = round(summary.get("DurationSeconds", 0) / 60, 1)
    except Exception as e:
        # Fallback: straight-line estimate
        dist_mi = round(_haversine(*origin_coords, *dest_coords), 2)
        dur_min = round(dist_mi * (20 if transport_mode == "Walking" else 5), 1)

    bus_fare = 1.50 if transport_mode != "Walking" or dist_mi > 0.5 else 0.0

    return {
        "origin":        origin,
        "destination":   destination,
        "transportMode": transport_mode,
        "distanceMiles": dist_mi,
        "durationMinutes": dur_min,
        "estimatedFare": bus_fare,
        "tip": _route_tip(dist_mi, transport_mode),
    }


def _multi_stop(origin, stops, transport_mode="Walking"):
    if not stops:
        return {"error": "No stops provided"}

    ordered    = _nearest_neighbor(origin, stops)
    legs       = []
    total_time = 0.0
    total_dist = 0.0
    total_fare = 0.0
    current    = origin

    for stop in ordered:
        leg = _calculate_route(current, stop.get("address", stop.get("name", "")), transport_mode)
        if "error" not in leg:
            total_time += leg["durationMinutes"]
            total_dist += leg["distanceMiles"]
            total_fare += leg["estimatedFare"]
            legs.append({
                "from":            current,
                "to":              stop.get("name", ""),
                "durationMinutes": leg["durationMinutes"],
                "distanceMiles":   leg["distanceMiles"],
                "fare":            leg["estimatedFare"],
            })
        current = stop.get("address", stop.get("name", ""))

    return {
        "optimizedStops":      ordered,
        "routeLegs":           legs,
        "totalDurationMinutes": round(total_time, 1),
        "totalDistanceMiles":  round(total_dist, 2),
        "totalFare":           round(total_fare, 2),
        "stopCount":           len(ordered),
        "summary": f"{len(ordered)} stops · {round(total_time)} min · ${round(total_fare, 2)} fare",
    }


def _estimate_time(origin, destination):
    walking = _calculate_route(origin, destination, "Walking")
    dist    = walking.get("distanceMiles", 99)
    return {
        "walkingMinutes":   walking.get("durationMinutes", 0),
        "walkingMiles":     dist,
        "recommendedMode":  "Walking" if dist <= 0.5 else "Transit",
        "estimatedWaitMin": 8,
        "totalWithTransit": round(walking.get("durationMinutes", 0) * 0.4 + 8, 1),
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _geocode(text):
    try:
        resp    = location_client.search_place_index_for_text(
            IndexName=PLACE_INDEX, Text=text, MaxResults=1
        )
        results = resp.get("Results", [])
        if results:
            pt = results[0]["Place"]["Geometry"]["Point"]
            return pt[1], pt[0]   # lat, lng
    except Exception:
        pass
    return None


def _nearest_neighbor(origin, stops):
    if len(stops) <= 1:
        return stops
    origin_coords = _geocode(origin) or (0.0, 0.0)
    remaining     = stops[:]
    ordered       = []
    current       = origin_coords
    while remaining:
        nearest = min(
            remaining,
            key=lambda s: _dist2(current, _geocode(s.get("address", s.get("name", ""))) or (0.0, 0.0)),
        )
        ordered.append(nearest)
        current = _geocode(nearest.get("address", nearest.get("name", ""))) or current
        remaining.remove(nearest)
    return ordered


def _dist2(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2


def _haversine(lat1, lon1, lat2, lon2):
    R    = 3958.8
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a    = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _route_tip(dist_miles, mode):
    if dist_miles <= 0.3:
        return "Short walk — no bus needed"
    if dist_miles <= 1.0:
        return "Easy walking distance — about 20 minutes"
    return f"Take the bus — {dist_miles} miles is too far to walk with groceries"


def _ok(body):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }


def _err(msg, code=400):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": msg}),
    }
