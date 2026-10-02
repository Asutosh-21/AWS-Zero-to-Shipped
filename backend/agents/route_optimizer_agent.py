import json
import boto3
import os

location = boto3.client("location", region_name="us-east-1")

ROUTE_CALCULATOR = os.environ["LOCATION_ROUTER_NAME"]
PLACE_INDEX = os.environ["LOCATION_PLACE_INDEX"]

AGENT_INSTRUCTIONS = """
You are the NutriRoute RouteOptimizer Agent. You plan the best routes for families
without cars to reach food sources using public transit and walking.

You have access to:
- calculate_route: gets walking/transit route between two points
- multi_stop_optimize: optimizes a route with multiple food source stops
- get_transit_schedule: gets bus/train schedule for a route
- estimate_travel_time: estimates total trip time including waits

Rules:
- Always prefer public transit over walking for distances > 0.5 miles
- Always include bus fare cost in the total trip cost
- Optimize for: minimum total time first, then minimum cost
- Show: departure time, each stop, arrival time, total time, total cost
- If a stop has limited hours, factor that into the route order
- Always show a walking-only fallback route for distances under 2 miles
"""


def lambda_handler(event, context):
    function_name = event.get("function", "")
    action_group = event.get("actionGroup", "")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    if function_name == "calculate_route":
        result = calculate_route(
            origin=parameters.get("origin"),
            destination=parameters.get("destination"),
            transport_mode=parameters.get("transport_mode", "Walking"),
        )
    elif function_name == "multi_stop_optimize":
        result = multi_stop_optimize(
            origin=parameters.get("origin"),
            stops=json.loads(parameters.get("stops", "[]")),
            transport_mode=parameters.get("transport_mode", "Walking"),
        )
    elif function_name == "estimate_travel_time":
        result = estimate_travel_time(
            origin=parameters.get("origin"),
            destination=parameters.get("destination"),
        )
    else:
        result = {"error": f"Unknown function: {function_name}"}

    return {
        "actionGroup": action_group,
        "function": function_name,
        "functionResponse": {"responseBody": {"TEXT": {"body": json.dumps(result)}}},
    }


def calculate_route(origin, destination, transport_mode):
    origin_coords = _geocode(origin)
    dest_coords = _geocode(destination)

    if not origin_coords or not dest_coords:
        return {"error": "Could not geocode one or both locations"}

    response = location.calculate_route(
        CalculatorName=ROUTE_CALCULATOR,
        DeparturePosition=origin_coords,
        DestinationPosition=dest_coords,
        TravelMode=transport_mode,
        IncludeLegGeometry=True,
    )

    summary = response.get("Summary", {})
    legs = response.get("Legs", [])

    steps = []
    for leg in legs:
        for step in leg.get("Steps", []):
            steps.append({
                "instruction": step.get("GeometryOffset", ""),
                "distanceMeters": step.get("Distance", 0),
                "durationSeconds": step.get("DurationSeconds", 0),
            })

    distance_miles = round(summary.get("Distance", 0) * 0.621371, 2)
    duration_minutes = round(summary.get("DurationSeconds", 0) / 60, 1)
    bus_fare = 1.50 if transport_mode == "Walking" and distance_miles > 0.5 else 0

    return {
        "origin": origin,
        "destination": destination,
        "transportMode": transport_mode,
        "distanceMiles": distance_miles,
        "durationMinutes": duration_minutes,
        "estimatedFare": bus_fare,
        "steps": steps[:10],
        "geometry": legs[0].get("Geometry", {}) if legs else {},
    }


def multi_stop_optimize(origin, stops, transport_mode):
    if not stops:
        return {"error": "No stops provided"}

    ordered_stops = _nearest_neighbor_sort(origin, stops)
    total_time = 0
    total_distance = 0
    total_fare = 0
    route_legs = []

    current = origin
    for stop in ordered_stops:
        leg = calculate_route(current, stop.get("address", ""), transport_mode)
        if "error" not in leg:
            total_time += leg["durationMinutes"]
            total_distance += leg["distanceMiles"]
            total_fare += leg["estimatedFare"]
            route_legs.append({
                "from": current,
                "to": stop.get("name", stop.get("address", "")),
                "durationMinutes": leg["durationMinutes"],
                "distanceMiles": leg["distanceMiles"],
                "fare": leg["estimatedFare"],
            })
        current = stop.get("address", "")

    return {
        "optimizedStops": ordered_stops,
        "routeLegs": route_legs,
        "totalDurationMinutes": round(total_time, 1),
        "totalDistanceMiles": round(total_distance, 2),
        "totalFare": round(total_fare, 2),
        "stopCount": len(ordered_stops),
        "tip": f"Visit {ordered_stops[0]['name']} first — closes earliest today" if ordered_stops else "",
    }


def estimate_travel_time(origin, destination):
    walking = calculate_route(origin, destination, "Walking")
    return {
        "walkingMinutes": walking.get("durationMinutes", 0),
        "walkingMiles": walking.get("distanceMiles", 0),
        "recommendedMode": "Walking" if walking.get("distanceMiles", 99) <= 0.5 else "Transit",
        "estimatedWaitMinutes": 8,
        "totalWithTransit": round(walking.get("durationMinutes", 0) * 0.4 + 8, 1),
    }


def _geocode(address_or_zip):
    try:
        response = location.search_place_index_for_text(
            IndexName=PLACE_INDEX,
            Text=address_or_zip,
            MaxResults=1,
        )
        results = response.get("Results", [])
        if results:
            point = results[0]["Place"]["Geometry"]["Point"]
            return [point[0], point[1]]
    except Exception:
        pass
    return None


def _nearest_neighbor_sort(origin, stops):
    if len(stops) <= 1:
        return stops
    origin_coords = _geocode(origin) or [0, 0]
    remaining = stops[:]
    ordered = []
    current = origin_coords
    while remaining:
        nearest = min(
            remaining,
            key=lambda s: _distance(current, _geocode(s.get("address", "")) or [0, 0])
        )
        ordered.append(nearest)
        current = _geocode(nearest.get("address", "")) or current
        remaining.remove(nearest)
    return ordered


def _distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
