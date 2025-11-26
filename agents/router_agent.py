from dotenv import load_dotenv
import os
from openai import OpenAI



# load credential
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)
print("[OpenAI] Connected")

# Router prompt
ROUTER_AGENT_PROMPT = """
You are a Router Agent (Orchestrator). You do the following:
- Receive customer queries.
- Analyze query intent. 
    - This can include but not limited to 
        1. Account lookup
        2. Billing lookup
        3. Updating personal data
        4. Answer questions about products
- Route to appropriate speacialist agent (Customer Data Agent or Support Agent):
    - Route to Customer Data Agent for customer information lookup and data validation
    - Route to Support Agent for more general questions
- Coordinate responses from multiple agent
    - Collect returned customer data.
    - Forward the enriched context to Support Agent when needed.


Note:
    - You don't answer customer support questions directly. You only route to the other two agents and coordinate answers.
    - You don't skip specialist agent to form an answer directly.
    - You always return a final clean response for users.
    - Your output must be in structured JSON:
    {
    "next_agent": "<name>",
    "task":"<description>",
    "data":{...}
    }
"""

def run_router_agent(user_query:str):
    """
    Input: 
        user_query (str) is user original question or request
    Returns:
        JSON that lists out next agent to route to, task, and data
          {
            "next_agent": "<name>",
            "task": "<description>",
            "data": {...}
            }
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        message=[
            {"role":"system", "content": ROUTER_AGENT_PROMPT},
            {"role": "user", "content": user_query},
        ],
        temperature=0.2
    )
    router_output = response.choices[0].message.content

    return router_output