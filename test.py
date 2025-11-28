# test.py

import logging
from dotenv import load_dotenv

from google.adk.tools.tool_context import ToolContext

from agent import router_agent, add_prompt_to_state
from builder import make_invocation_context  # the function we defined above

load_dotenv()
logging.basicConfig(level=logging.INFO)


def run_test_case(user_prompt: str):
    print("\n========== TEST CASE ==========")
    print("USER PROMPT:", user_prompt)
    print("================================\n")

    # ✔ Create a valid invocation context
    invocation_context = make_invocation_context(router_agent)

    # ✔ ToolContext uses the invocation context
    tool_context = ToolContext(invocation_context)
    tool_context.state = {}

    # ✔ Save prompt
    add_prompt_to_state(tool_context, user_prompt)

    final_answer = router_agent.run(
        tool_context=tool_context,
        inputs={"PROMPT": user_prompt}
    )

    print("\n========== FINAL OUTPUT ==========")
    print(final_answer["output"])
    print("==================================\n")


if __name__ == "__main__":
    run_test_case("What is the capital of France?")
    run_test_case("Show me the service tickets for customer 3.")
    run_test_case("Add a support ticket for customer 12: billing issue.")
    run_test_case("Give me customer success best practices.")
