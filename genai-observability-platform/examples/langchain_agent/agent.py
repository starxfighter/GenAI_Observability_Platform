"""
LangChain Agent with Observability Integration
Demonstrates how to instrument a LangChain agent.
"""
import os
from typing import Optional

# Observability SDK
from genai_observability import init, get_tracer
from genai_observability.integrations.langchain import ObservabilityCallbackHandler

# LangChain imports (uncomment when using)
# from langchain.agents import AgentExecutor, create_react_agent
# from langchain.tools import Tool
# from langchain_anthropic import ChatAnthropic
# from langchain.prompts import PromptTemplate


def create_observable_langchain_agent(
    agent_id: str,
    endpoint: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514"
):
    """
    Create a LangChain agent with observability instrumentation.

    This example shows the recommended pattern for LangChain integration.
    """

    # Initialize observability
    init(
        endpoint=endpoint,
        api_key=api_key,
        agent_id=agent_id,
        environment=os.getenv("ENVIRONMENT", "dev"),
    )

    tracer = get_tracer()

    # Create the observability callback handler
    # This automatically instruments all LangChain operations
    observability_handler = ObservabilityCallbackHandler(tracer=tracer)

    # Example LangChain setup (uncomment when using actual LangChain)
    """
    # Create the LLM
    llm = ChatAnthropic(
        model=model,
        callbacks=[observability_handler]
    )

    # Define tools
    tools = [
        Tool(
            name="search",
            func=lambda q: f"Search results for: {q}",
            description="Search for information"
        ),
        Tool(
            name="calculator",
            func=lambda expr: str(eval(expr)),
            description="Perform calculations"
        ),
    ]

    # Create the agent
    prompt = PromptTemplate.from_template(
        "Answer the following question: {input}\n{agent_scratchpad}"
    )

    agent = create_react_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        callbacks=[observability_handler],
        verbose=True
    )

    return agent_executor
    """

    # Return mock for demonstration
    return MockLangChainAgent(tracer, observability_handler)


class MockLangChainAgent:
    """Mock LangChain agent for demonstration."""

    def __init__(self, tracer, callback_handler):
        self.tracer = tracer
        self.callback_handler = callback_handler

    def invoke(self, input_data: dict) -> dict:
        """Simulate agent invocation with observability."""

        user_input = input_data.get("input", "")

        with self.tracer.trace(
            name="langchain_agent_invoke",
            attributes={"framework": "langchain"}
        ) as ctx:

            # Simulate LLM call
            with self.tracer.llm_span(
                name="llm_call",
                parent=ctx,
                model="claude-sonnet-4-20250514"
            ) as llm_ctx:

                # Simulate processing
                import time
                time.sleep(0.3)

                self.tracer.record_token_usage(
                    context=llm_ctx,
                    prompt_tokens=150,
                    completion_tokens=75
                )

            # Simulate tool use
            with self.tracer.tool_span(
                name="tool_call",
                parent=ctx,
                tool_name="search"
            ) as tool_ctx:

                time.sleep(0.1)
                self.tracer.record_tool_result(
                    context=tool_ctx,
                    status="success",
                    result_count=3
                )

            return {
                "output": f"Processed: {user_input}",
                "intermediate_steps": []
            }


def main():
    """Run the LangChain agent example."""

    endpoint = os.getenv("OBSERVABILITY_ENDPOINT", "http://localhost:8000")
    api_key = os.getenv("OBSERVABILITY_API_KEY", "test-api-key")
    agent_id = os.getenv("AGENT_ID", "langchain-agent-001")

    agent = create_observable_langchain_agent(
        agent_id=agent_id,
        endpoint=endpoint,
        api_key=api_key,
    )

    # Test the agent
    test_inputs = [
        "What is the capital of France?",
        "Calculate 15 * 8 + 22",
        "Search for Python best practices",
    ]

    print("\nLangChain Agent with Observability")
    print("=" * 50)

    for user_input in test_inputs:
        print(f"\nInput: {user_input}")
        result = agent.invoke({"input": user_input})
        print(f"Output: {result['output']}")

    print("\n" + "=" * 50)
    print("Check the dashboard for traces!")


if __name__ == "__main__":
    main()
