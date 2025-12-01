import os
import logging
import google.cloud.logging
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams, MCPTool
from google.adk.tools.tool_context import ToolContext

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token


cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = os.getenv("MODEL")


# Greet user and save their prompt

def add_prompt_to_state(tool_context: ToolContext, prompt: str) -> dict[str, str]:
    tool_context.state["PROMPT"] = prompt
    import google.generativeai as genai
    model = genai.GenerativeModel(os.getenv("MODEL"))
    tone_response = model.generate_content(
        f"""
        Classify tone of this message in ONE WORD from:
        calm, neutral, confused, angry, frustrated, worried, upset.
        Message: {prompt}
        """
    )
    tone = tone_response.text.strip().lower()
    tool_context.state["TONE"] = tone
    return {"status": "success", "tone": tone}



# Configuring the MCP Tool to connect to the customer MCP server

mcp_server_url = os.getenv("MCP_SERVER_URL")
if not mcp_server_url:
    raise ValueError("The environment variable MCP_SERVER_URL is not set.")

def get_id_token():
    """Get an ID token to authenticate with the MCP server."""
    target_url = os.getenv("MCP_SERVER_URL")
    audience = target_url.split('/mcp/')[0]
    request = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(request, audience)
    return id_token

"""
# Use this code if you are using the public MCP Server and comment out the code below defining mcp_tools
mcp_tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_server_url
    )
)
"""

# Explicitly define the tools available on the MCP server.
# This avoids discovery issues and ensures the agent knows the exact toolset.
mcp_tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_server_url,
        headers={
            "Authorization": f"Bearer {get_id_token()}",
        },
        # Match the working settings from mcp_connection_test.py
        use_single_connection=False,
        keep_alive_interval_seconds=10,
        timeout_seconds=60,
    ),
    # The toolset will discover tools from the MCP server.
    # Use tool_filter to specify which tools the agent can use.
    tool_filter=[
        "get_customer",
        "list_customers",
        "update_customer",
        "create_ticket",
        "get_customer_history",
    ]
)


# 0. User input agent
user_input_agent = Agent(
    name="user_input_agent",
    description="The agent that receives the user's prompt and saves it to the state.",
    model=model_name,
    instruction="""
    You are the first agent in the chain. Your only job is to take the user's
    prompt and save it to the state using the add_prompt_to_state tool.
    """,
    tools=[add_prompt_to_state],
    # The user's prompt is passed to this agent's `run` method.
    # The `prompt` argument name must match the `add_prompt_to_state` tool's argument.
)

# 1. Customer data agent
customer_data_agent = Agent(
    name="customer_data_agent",
    model=model_name,
    description="The primary data analyst for the customer success team.",
    instruction="""
    You are a helpful data analyst. Your goal is to use the tools at your disposal
    to retrieve or update customer information from a database based on the user's PROMPT.

    IMPORTANT — CUSTOMER TONE:
    You also receive TONE = {{ TONE }}.
    Use it to decide PRIORITY when creating tickets:
    - If tone is 'angry', 'frustrated', 'upset', 'worried' => priority = 'high'
    - If tone is neutral or calm => priority = 'medium'
    - Otherwise => priority = 'low'

    Rules:
    - If creating a support ticket, ALWAYS choose priority based on tone.
    - If tone indicates distress, provide more thorough explanations.
    - Summarize what tools you used and what data you retrieved.

    PROMPT:
    {{ PROMPT }}
    """
    ,
    tools=[
        mcp_tools
    ],
    output_key="research_data" # A key to store the combined findings
)

# 2. Support agent
support_agent = Agent(
    name="support_agent",
    model=model_name,
    description="Synthesizes all information into a friendly, readable response.",
    instruction="""
    You are the friendly customer-facing voice of the company.
    You receive:

    - RESEARCH_DATA = {{ research_data }}
    - TONE = {{ TONE }}

    Your job:
    1. Provide the factual results from RESEARCH_DATA.
    2. Adjust your tone based on TONE:
    - If TONE is 'angry', 'frustrated', or 'upset': apologize briefly, acknowledge feelings, 
        reassure the customer we are resolving the issue.
    - If TONE is 'worried' or 'confused': provide comfort and clear guidance.
    - Otherwise: respond in your normal friendly tone.

    3. Do NOT over-apologize. Keep it professional and empathetic.
    """

)

# The router agent
root_agent = SequentialAgent(
    name="router_agent",
    description="The main workflow for orchestrating other specialist agents",
    sub_agents=[
        user_input_agent,    # Step 0: Get the user's prompt and save it to the state
        customer_data_agent, # Step 1: Gather all data
        support_agent,       # Step 2: Format the final response
    ]
)