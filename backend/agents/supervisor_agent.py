import json
import boto3
import os

bedrock = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

SUPERVISOR_AGENT_ID = os.environ["BEDROCK_AGENT_SUPERVISOR_ID"]
SUPERVISOR_AGENT_ALIAS = os.environ.get("BEDROCK_AGENT_SUPERVISOR_ALIAS", "LIVE")

AGENT_INSTRUCTIONS = """
You are the NutriRoute AI Supervisor. You orchestrate three specialist agents to help
food-insecure families access nutritious food.

When a user sends a query, you MUST:
1. Extract: location (zip code), family size, SNAP balance, dietary restrictions, transport mode, language
2. Call FoodFinder Agent to get real-time food sources near the zip code
3. Call MealPlanner Agent to generate a SNAP-optimized meal plan
4. Call RouteOptimizer Agent to get the best transit route to food sources
5. Synthesize all three responses into ONE unified, friendly response

Always respond in the user's language. If they write in Spanish, respond in Spanish.
Never give medical advice. Never store or repeat personal information beyond what's needed.
Always include: food sources found, meal plan summary, route summary, and money saved.

Tone: warm, practical, empowering. You are helping someone feed their family.
"""


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    user_query = body.get("query", "")
    session_id = body.get("sessionId", context.aws_request_id)
    user_id = event.get("requestContext", {}).get("authorizer", {}).get("sub", "anonymous")

    if not user_query:
        return {"statusCode": 400, "body": json.dumps({"error": "query is required"})}

    response = bedrock.invoke_agent(
        agentId=SUPERVISOR_AGENT_ID,
        agentAliasId=SUPERVISOR_AGENT_ALIAS,
        sessionId=session_id,
        inputText=user_query,
        enableTrace=True,
    )

    full_response = ""
    trace_steps = []

    for event_stream in response.get("completion", []):
        if "chunk" in event_stream:
            chunk = event_stream["chunk"]
            full_response += chunk.get("bytes", b"").decode("utf-8")
        if "trace" in event_stream:
            trace = event_stream["trace"].get("trace", {})
            if "orchestrationTrace" in trace:
                step = trace["orchestrationTrace"]
                if "rationale" in step:
                    trace_steps.append(step["rationale"].get("text", ""))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({
            "response": full_response,
            "sessionId": session_id,
            "agentSteps": trace_steps,
        }),
    }
