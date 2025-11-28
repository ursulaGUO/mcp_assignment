import os
import asyncio
import logging
from dotenv import load_dotenv

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_id_token() -> str:
    """
    Get an OIDC ID token to authenticate with a Cloud Run MCP server.
    """
    try:
        target_url = os.getenv("MCP_SERVER_URL")
        audience = target_url.split('/mcp/')[0]
        logging.info(f"Authenticating for audience: {audience}")
        request = google.auth.transport.requests.Request()
        return google.oauth2.id_token.fetch_id_token(request, audience)
    except Exception as e:
        logging.error(f"Failed to generate ID token: {e}")
        raise


async def test_mcp_connection():
    """
    Tests MCP connectivity by attempting tool discovery.
    """
    mcp_server_url = os.getenv("MCP_SERVER_URL")
    if not mcp_server_url:
        logging.error("The environment variable MCP_SERVER_URL is not set.")
        return

    logging.info(f"Attempting to connect to MCP server at: {mcp_server_url}")

    toolset = None
    try:
        # Correct usage — now takes no args
        id_token = get_id_token()

        toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_server_url,
                headers={
                    "Authorization": f"Bearer {id_token}",
                },
                use_single_connection=False,
                keep_alive_interval_seconds=10,
                timeout_seconds=60,
            ),
            tool_filter=[
                "get_customer",
                "list_customers",
                "update_customer",
                "create_ticket",
                "get_customer_history",
            ]
        )

        # get_tools() forces MCP handshake + discovery
        tools = await toolset.get_tools()
        logging.info("✅ MCP server connection successful!")
        logging.info(f"Discovered {len(tools)} tools: {[tool.name for tool in tools]}")

    except Exception as e:
        logging.error(f"❌ Failed to connect to MCP server: {e}")
    finally:
        if toolset:
            await toolset.close()
            logging.info("MCP toolset connection closed.")


if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
