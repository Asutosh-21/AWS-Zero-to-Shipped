import json
import boto3
import os

bedrock        = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
bedrock_runtime = boto3.client("bedrock-runtime",       region_name="us-east-1")

SUPERVISOR_AGENT_ID    = os.environ.get("BEDROCK_AGENT_SUPERVISOR_ID", "")
SUPERVISOR_AGENT_ALIAS = os.environ.get("BEDROCK_AGENT_SUPERVISOR_ALIAS", "LIVE")
NOVA_MODEL_ID          = "amazon.nova-lite-v1:0"

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

    # Use Bedrock Agent if configured, otherwise fall back to Nova Lite direct
    if SUPERVISOR_AGENT_ID:
        full_response, trace_steps = _invoke_agent(user_query, session_id)
    else:
        full_response, trace_steps = _invoke_nova(user_query)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({
            "response": full_response,
            "sessionId": session_id,
            "agentSteps": trace_steps,
            "model": "nova-lite" if not SUPERVISOR_AGENT_ID else "bedrock-agent",
        }),
    }


def _invoke_agent(user_query, session_id):
    response    = bedrock.invoke_agent(
        agentId      = SUPERVISOR_AGENT_ID,
        agentAliasId = SUPERVISOR_AGENT_ALIAS,
        sessionId    = session_id,
        inputText    = user_query,
        enableTrace  = True,
    )
    full_response = ""
    trace_steps   = []
    for event_stream in response.get("completion", []):
        if "chunk" in event_stream:
            full_response += event_stream["chunk"].get("bytes", b"").decode("utf-8")
        if "trace" in event_stream:
            trace = event_stream["trace"].get("trace", {})
            if "orchestrationTrace" in trace:
                step = trace["orchestrationTrace"]
                if "rationale" in step:
                    trace_steps.append(step["rationale"].get("text", ""))
    return full_response, trace_steps


def _invoke_nova(user_query):
    """Direct Nova Lite invocation — used before Bedrock Agents are configured."""
    system_prompt = AGENT_INSTRUCTIONS
    payload = {
        "messages": [{"role": "user", "content": [{"text": user_query}]}],
        "system": [{"text": system_prompt}],
        "inferenceConfig": {"maxTokens": 2048, "temperature": 0.3},
    }
    response = bedrock_runtime.invoke_model(
        modelId     = NOVA_MODEL_ID,
        body        = json.dumps(payload),
        contentType = "application/json",
        accept      = "application/json",
    )
    result = json.loads(response["body"].read())
    text   = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
    return text, ["Nova Lite direct invocation"]
