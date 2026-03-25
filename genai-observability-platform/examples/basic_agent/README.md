# Example Agent with Observability

This example demonstrates how to instrument a GenAI agent with the observability SDK.

## Overview

The example agent shows:
- SDK initialization
- Creating traces for requests
- Creating LLM spans with token tracking
- Creating tool spans with result recording
- Error handling and recording

## Running the Example

### 1. Set Environment Variables

```bash
export OBSERVABILITY_ENDPOINT=https://api.observability.example.com
export OBSERVABILITY_API_KEY=your-api-key
export AGENT_ID=example-agent-001
export ENVIRONMENT=dev
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Agent

```bash
python agent.py
```

## Code Structure

```python
# Initialize observability at startup
init(
    endpoint=endpoint,
    api_key=api_key,
    agent_id=agent_id,
)

tracer = get_tracer()

# Create a trace for each request
with tracer.trace(name="process_request") as trace_ctx:

    # Create LLM spans
    with tracer.llm_span(name="generate", parent=trace_ctx, model="claude-sonnet-4-20250514") as llm_ctx:
        response = llm.generate(prompt)
        tracer.record_token_usage(llm_ctx, prompt_tokens=100, completion_tokens=50)

    # Create tool spans
    with tracer.tool_span(name="search", parent=trace_ctx, tool_name="database") as tool_ctx:
        results = search(query)
        tracer.record_tool_result(tool_ctx, status="success", result_count=len(results))
```

## Viewing Results

After running the agent:

1. **CLI**: `genai-obs traces list --agent example-agent-001`
2. **Dashboard**: Open the web dashboard and navigate to the agent
3. **API**: `curl https://api.../api/v1/traces?agent_id=example-agent-001`

## Customization

### Using Real LLM Clients

Replace `MockLLMClient` with actual clients:

```python
import anthropic

client = anthropic.Anthropic()

with tracer.llm_span(name="call_claude", parent=ctx, model="claude-sonnet-4-20250514"):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    tracer.record_token_usage(
        ctx,
        prompt_tokens=response.usage.input_tokens,
        completion_tokens=response.usage.output_tokens
    )
```

### Adding Custom Attributes

```python
with tracer.trace(
    name="process_request",
    attributes={
        "user_id": user_id,
        "request_type": "chat",
        "priority": "high",
        "custom_field": "value"
    }
) as ctx:
    ...
```

### Error Handling

```python
try:
    result = risky_operation()
except Exception as e:
    tracer.record_error(
        error=e,
        context=ctx,
        attributes={"operation": "risky_operation"}
    )
    # Re-raise or handle as needed
    raise
```
