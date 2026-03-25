"""
Example GenAI Agent with Observability
Demonstrates how to instrument a LangChain-style agent with the observability SDK.
"""
import os
import json
import random
import time
from datetime import datetime
from typing import Optional

# Import the observability SDK
from genai_observability import init, get_tracer

# Simulated LLM client (replace with actual Anthropic/OpenAI client)
class MockLLMClient:
    """Mock LLM client for demonstration purposes."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 1024) -> dict:
        """Simulate an LLM call with realistic latency and token counts."""
        # Simulate latency (200-800ms)
        time.sleep(random.uniform(0.2, 0.8))

        # Simulate token counts
        prompt_tokens = len(prompt.split()) * 1.3  # Rough estimate
        completion_tokens = random.randint(50, 200)

        # Simulate occasional errors (5% chance)
        if random.random() < 0.05:
            raise Exception("LLM API rate limit exceeded")

        return {
            "content": f"This is a simulated response to: {prompt[:50]}...",
            "model": self.model,
            "usage": {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": completion_tokens,
                "total_tokens": int(prompt_tokens) + completion_tokens
            }
        }


class MockToolkit:
    """Mock tools for the agent."""

    @staticmethod
    def search_database(query: str) -> list:
        """Simulate a database search."""
        time.sleep(random.uniform(0.1, 0.3))

        # Simulate occasional failures
        if random.random() < 0.03:
            raise Exception("Database connection timeout")

        return [
            {"id": 1, "title": f"Result for: {query}", "relevance": 0.95},
            {"id": 2, "title": f"Related: {query}", "relevance": 0.82},
        ]

    @staticmethod
    def fetch_url(url: str) -> str:
        """Simulate fetching a URL."""
        time.sleep(random.uniform(0.2, 0.5))

        if "error" in url:
            raise Exception(f"Failed to fetch URL: {url}")

        return f"<html><body>Content from {url}</body></html>"

    @staticmethod
    def calculate(expression: str) -> float:
        """Simulate a calculation."""
        time.sleep(0.01)
        # Simple eval for demo (don't do this in production!)
        try:
            return eval(expression)
        except Exception:
            return 0.0


class ObservableAgent:
    """
    An example agent instrumented with observability.

    This demonstrates best practices for instrumenting GenAI agents:
    1. Initialize the SDK at startup
    2. Create traces for each request
    3. Create spans for LLM calls
    4. Create spans for tool calls
    5. Record errors appropriately
    """

    def __init__(
        self,
        agent_id: str,
        endpoint: str,
        api_key: str,
        model: str = "claude-sonnet-4-20250514"
    ):
        self.agent_id = agent_id
        self.llm = MockLLMClient(model)
        self.tools = MockToolkit()

        # Initialize observability
        init(
            endpoint=endpoint,
            api_key=api_key,
            agent_id=agent_id,
            environment=os.getenv("ENVIRONMENT", "dev"),
            flush_interval=5.0,  # Flush every 5 seconds
            batch_size=50,       # Or when batch reaches 50 events
        )

        self.tracer = get_tracer()
        print(f"Agent '{agent_id}' initialized with observability")

    def process_request(self, user_input: str, session_id: Optional[str] = None) -> str:
        """
        Process a user request with full observability.

        Args:
            user_input: The user's input message
            session_id: Optional session identifier for grouping requests

        Returns:
            The agent's response
        """
        # Create a trace for the entire request
        with self.tracer.trace(
            name="process_request",
            attributes={
                "user_input_length": len(user_input),
                "session_id": session_id,
            }
        ) as trace_ctx:

            try:
                # Step 1: Understand the request
                intent = self._analyze_intent(user_input, trace_ctx)

                # Step 2: Gather information if needed
                context = self._gather_context(intent, user_input, trace_ctx)

                # Step 3: Generate response
                response = self._generate_response(user_input, context, trace_ctx)

                return response

            except Exception as e:
                # Record error in trace
                self.tracer.record_error(
                    error=e,
                    context=trace_ctx,
                    attributes={"user_input": user_input[:100]}
                )
                raise

    def _analyze_intent(self, user_input: str, parent_ctx) -> dict:
        """Analyze user intent using LLM."""

        # Create an LLM span
        with self.tracer.llm_span(
            name="analyze_intent",
            parent=parent_ctx,
            model=self.llm.model,
            attributes={"step": "intent_analysis"}
        ) as llm_ctx:

            prompt = f"""Analyze the following user request and identify the intent:

User: {user_input}

Respond with JSON: {{"intent": "...", "entities": [...], "requires_search": true/false}}"""

            try:
                response = self.llm.generate(prompt, max_tokens=256)

                # Record token usage
                self.tracer.record_token_usage(
                    context=llm_ctx,
                    prompt_tokens=response["usage"]["prompt_tokens"],
                    completion_tokens=response["usage"]["completion_tokens"],
                )

                # Parse intent (simplified)
                return {
                    "intent": "information_request",
                    "entities": [user_input.split()[0]] if user_input else [],
                    "requires_search": "search" in user_input.lower() or "find" in user_input.lower()
                }

            except Exception as e:
                self.tracer.record_error(e, llm_ctx)
                raise

    def _gather_context(self, intent: dict, user_input: str, parent_ctx) -> dict:
        """Gather additional context using tools."""

        context = {"search_results": [], "url_content": None}

        # Use search tool if needed
        if intent.get("requires_search"):
            with self.tracer.tool_span(
                name="search_database",
                parent=parent_ctx,
                tool_name="database_search",
                attributes={"query": user_input[:50]}
            ) as tool_ctx:

                try:
                    results = self.tools.search_database(user_input)
                    context["search_results"] = results

                    # Record tool success
                    self.tracer.record_tool_result(
                        context=tool_ctx,
                        status="success",
                        result_count=len(results)
                    )

                except Exception as e:
                    self.tracer.record_error(e, tool_ctx)
                    # Continue without search results
                    context["search_error"] = str(e)

        # Check if URL fetch is needed
        if "http" in user_input:
            # Extract URL (simplified)
            words = user_input.split()
            urls = [w for w in words if w.startswith("http")]

            for url in urls[:1]:  # Limit to first URL
                with self.tracer.tool_span(
                    name="fetch_url",
                    parent=parent_ctx,
                    tool_name="url_fetcher",
                    attributes={"url": url}
                ) as tool_ctx:

                    try:
                        content = self.tools.fetch_url(url)
                        context["url_content"] = content[:500]

                        self.tracer.record_tool_result(
                            context=tool_ctx,
                            status="success",
                            content_length=len(content)
                        )

                    except Exception as e:
                        self.tracer.record_error(e, tool_ctx)
                        context["url_error"] = str(e)

        return context

    def _generate_response(self, user_input: str, context: dict, parent_ctx) -> str:
        """Generate final response using LLM."""

        with self.tracer.llm_span(
            name="generate_response",
            parent=parent_ctx,
            model=self.llm.model,
            attributes={"step": "response_generation"}
        ) as llm_ctx:

            # Build prompt with context
            context_str = ""
            if context.get("search_results"):
                context_str += f"\nSearch Results: {json.dumps(context['search_results'])}"
            if context.get("url_content"):
                context_str += f"\nURL Content: {context['url_content'][:200]}"

            prompt = f"""You are a helpful assistant. Answer the user's question based on the available context.

User Question: {user_input}
{context_str}

Provide a helpful, accurate response:"""

            try:
                response = self.llm.generate(prompt, max_tokens=1024)

                # Record token usage
                self.tracer.record_token_usage(
                    context=llm_ctx,
                    prompt_tokens=response["usage"]["prompt_tokens"],
                    completion_tokens=response["usage"]["completion_tokens"],
                )

                return response["content"]

            except Exception as e:
                self.tracer.record_error(e, llm_ctx)
                raise


def main():
    """Run the example agent."""

    # Configuration from environment
    endpoint = os.getenv("OBSERVABILITY_ENDPOINT", "http://localhost:8000")
    api_key = os.getenv("OBSERVABILITY_API_KEY", "test-api-key")
    agent_id = os.getenv("AGENT_ID", "example-agent-001")

    # Create the agent
    agent = ObservableAgent(
        agent_id=agent_id,
        endpoint=endpoint,
        api_key=api_key,
    )

    # Example requests
    test_requests = [
        "What is the weather like today?",
        "Search for information about Python programming",
        "Calculate 25 * 4 + 10",
        "Fetch https://example.com and summarize it",
        "Help me understand machine learning",
    ]

    print("\n" + "="*60)
    print("Running example agent with observability")
    print("="*60 + "\n")

    for i, request in enumerate(test_requests, 1):
        print(f"\n[Request {i}] User: {request}")
        print("-" * 40)

        try:
            response = agent.process_request(
                user_input=request,
                session_id=f"demo-session-{datetime.now().strftime('%Y%m%d')}"
            )
            print(f"Agent: {response[:200]}...")

        except Exception as e:
            print(f"Error: {str(e)}")

        # Small delay between requests
        time.sleep(0.5)

    print("\n" + "="*60)
    print("Example complete! Check the observability dashboard for traces.")
    print("="*60)


if __name__ == "__main__":
    main()
