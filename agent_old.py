import os
import json
import httpx
import asyncio
from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig
from google.genai import types


# ==========================================
# LOAD ENV
# ==========================================
load_dotenv()

MODEL = os.getenv("MODEL")
MCP_URL = os.getenv("MCP_SERVER_URL")    # ex: https://xxx.run.app/mcp
MCP_TOKEN = os.getenv("MCP_LOGIN")       # the same IAM token used in CLI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# ======================================================
# REST-BASED MCP CLIENT (NO ADK MCP LAYER — FULL FIX)
# ======================================================
async def mcp_call(method: str, params: dict):
    """
    Calls your Cloud Run MCP server using HTTP POST.
    """
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            MCP_URL,
            headers={
                "Authorization": f"Bearer {MCP_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": method,
                "params": params
            }
        )

    if response.status_code != 200:
        return {"error": f"HTTP {response.status_code}", "body": response.text}

    return response.json()


# ======================================================
# CUSTOMER MCP TOOL WRAPPER
# ======================================================
class CustomerMCPTools:

    async def get_customer(self, customer_id: str):
        return await mcp_call("get_customer", {"customer_id": customer_id})

    async def list_customers(self):
        return await mcp_call("list_customers", {})

    async def update_customer(self, customer_id: str, data: dict):
        return await mcp_call("update_customer", {"customer_id": customer_id, "data": data})

    async def get_customer_history(self, customer_id: str):
        return await mcp_call("get_customer_history", {"customer_id": customer_id})

    async def create_ticket(self, customer_id: str, message: str):
        return await mcp_call("create_ticket", {"customer_id": customer_id, "message": message})


mcp_tools = CustomerMCPTools()


# ======================================================
# PLANNER
# ======================================================
thinking = ThinkingConfig(include_thoughts=True, thinking_budget=128)
planner = BuiltInPlanner(thinking_config=thinking)


# ======================================================
# ROUTING AGENT
# ======================================================
routing_agent = LlmAgent(
    name="routing_agent",
    model=MODEL,
    instruction="""
You are the Routing Agent.
Your job is ONLY to decide which agent should run next.

You MUST return a JSON dict like:

{
  "next_agent": "customer_data_agent" or "support_agent",
  "customer_id": "<id or empty>",
  "original_ask": "<full user text>"
}

Rules:
- If user mentions "customer", "account", "id", "lookup", or any number → choose customer_data_agent.
- Else → choose support_agent.
""",
    planner=planner
)


# ======================================================
# CUSTOMER DATA AGENT
# ======================================================
customer_data_agent = LlmAgent(
    name="customer_data_agent",
    model=MODEL,
    instruction="""
You are customer_data_agent.
Your job is to call the MCP REST tools I provide.

You will be given:
{
  "customer_id": "...",
  "original_ask": "..."
}

Call the REST MCP tools (already implemented).
Return:

{
  "customer_info": {...},
  "original_ask": "..."
}
""",
    planner=planner
)


# ======================================================
# SUPPORT AGENT
# ======================================================
support_agent = LlmAgent(
    name="support_agent",
    model=MODEL,
    instruction="""
You are the Support Agent.

You will receive:
{
  "original_ask": "...",
  "customer_info": {...}  (or null)
}

If customer_info exists → give personalized help.
If not → give general support help.

Return a final human-facing answer.
""",
    planner=planner
)


# ======================================================
# RUNNER + SESSION
# ======================================================
session_service = InMemorySessionService()


async def run_llm(agent, session_id, payload):
    runner = Runner(agent=agent, app_name="customer_a2a", session_service=session_service)

    content = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(payload))]
    )

    events = runner.run(
        user_id="local-user",
        session_id=session_id,
        new_message=content
    )

    for e in events:
        if e.is_final_response():
            return e.content.parts[0].text

    return None


# ======================================================
# MAIN WORKFLOW: routing → customer (optional) → support
# ======================================================
def run_workflow(user_text: str):

    session_id = "workflow-session"
    asyncio.run(session_service.create_session(
        app_name="customer_a2a",
        user_id="local-user",
        session_id=session_id
    ))

    # 1) ROUTING
    routing_raw = asyncio.run(run_llm(
        routing_agent,
        session_id,
        {"ask": user_text}
    ))

    try:
        routing = json.loads(routing_raw)
    except:
        return {"error": "Routing returned invalid JSON", "raw": routing_raw}

    next_agent = routing.get("next_agent")
    customer_id = routing.get("customer_id")
    original_ask = routing.get("original_ask", user_text)

    # 2) If support agent directly → finish
    if next_agent == "support_agent" and not customer_id:
        support_raw = asyncio.run(run_llm(
            support_agent,
            session_id,
            {"original_ask": original_ask, "customer_info": None}
        ))
        return {"reply": support_raw}

    # 3) CUSTOMER DATA PHASE
    customer_info = None
    if customer_id:
        # call MCP directly (REST)
        customer_info = asyncio.run(mcp_tools.get_customer(customer_id))

    # pass both ask + data to support
    support_raw = asyncio.run(run_llm(
        support_agent,
        session_id,
        {"original_ask": original_ask, "customer_info": customer_info}
    ))

    return {"reply": support_raw}


# ======================================================
# ENTRYPOINT
# ======================================================
if __name__ == "__main__":
    print("Running FULL WORKFLOW...\n")
    result = run_workflow("I need help with my account, customer ID 3")
    print("\nWORKFLOW RESULT:\n", result)
