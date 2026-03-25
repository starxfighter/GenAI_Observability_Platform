# GenAI Observability SDK

A comprehensive observability SDK for GenAI agents, providing automatic tracing, metrics, and error tracking.

## Features

- **Execution Tracing**: Track complete agent executions with nested spans
- **LLM Call Tracking**: Capture model, tokens, latency, and costs for all LLM calls
- **Tool/MCP Tracking**: Monitor tool and MCP server interactions
- **Error Capture**: Automatic error capture with stack traces
- **Cost Tracking**: Automatic cost calculation based on token usage
- **Framework Integrations**: Built-in support for LangChain and CrewAI
- **PII Redaction**: Configurable redaction of sensitive data
- **Batching**: Efficient event batching with background export
- **Sampling**: Configurable sampling rates for high-volume agents
- **Multi-Region Support**: Geographic routing with automatic failover
- **OpenTelemetry Export**: OTLP, Jaeger, Zipkin exporters with GenAI semantic conventions

## Installation

```bash
# Basic installation
pip install genai-observability

# With LangChain integration
pip install genai-observability[langchain]

# With CrewAI integration
pip install genai-observability[crewai]

# With async support
pip install genai-observability[async]

# All extras
pip install genai-observability[all]
```

## Quick Start

### Basic Usage

```python
from genai_observability import init, shutdown

# Initialize the client
client = init(
    api_endpoint="https://observability.example.com",
    api_key="your-api-key",
    agent_id="my-agent",
    agent_type="custom",
    environment="production",
)

# Use the tracer
with client.tracer.start_execution(input_data={"query": "Hello"}) as execution:
    # Your agent logic here

    # Track an LLM call
    with client.tracer.trace_llm_call(
        model="claude-sonnet-4",
        provider="anthropic",
        prompt="Hello, how are you?",
    ) as llm_span:
        # Make your LLM call
        response = call_your_llm(...)

        # Record token usage
        llm_span.set_token_usage(
            input_tokens=10,
            output_tokens=25,
        )
        llm_span.set_response(response)

    # Track a tool call
    with client.tracer.trace_tool_call(
        tool_name="search",
        tool_input={"query": "weather"},
    ) as tool_span:
        result = search_tool(...)
        tool_span.set_output(result)

    # Set execution output
    execution.set_output({"response": "I'm doing well!"})

# Shutdown when done
shutdown()
```

### Environment Variables

You can also configure via environment variables:

```bash
export GENAI_OBS_ENDPOINT="https://observability.example.com"
export GENAI_OBS_API_KEY="your-api-key"
export GENAI_OBS_AGENT_ID="my-agent"
export GENAI_OBS_AGENT_TYPE="custom"
export GENAI_OBS_ENVIRONMENT="production"
export GENAI_OBS_ENABLED="true"
export GENAI_OBS_DEBUG="false"
export GENAI_OBS_SAMPLING_RATE="1.0"
```

```python
from genai_observability import init_from_env

client = init_from_env()
```

## LangChain Integration

The SDK provides automatic instrumentation for LangChain applications:

```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from genai_observability import init
from genai_observability.integrations import LangChainCallbackHandler

# Initialize observability
client = init(
    api_endpoint="https://observability.example.com",
    api_key="your-api-key",
    agent_id="langchain-agent",
    agent_type="langchain",
)

# Create the callback handler
handler = LangChainCallbackHandler(client)

# Use with LangChain
llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    callbacks=[handler],  # Add the handler
)

# All LLM calls are now automatically traced
response = llm.invoke("What is the weather like?")

# Works with agents too
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[handler],  # Add to executor for full tracing
)

result = executor.invoke({"input": "Search for the latest news"})
```

## CrewAI Integration

```python
from crewai import Agent, Task, Crew

from genai_observability import init
from genai_observability.integrations import CrewAICallbackHandler

# Initialize observability
client = init(
    api_endpoint="https://observability.example.com",
    api_key="your-api-key",
    agent_id="crewai-agent",
    agent_type="crewai",
)

# Create the handler
handler = CrewAICallbackHandler(client)

# Define your crew
researcher = Agent(
    role="Researcher",
    goal="Research topics thoroughly",
    backstory="You are an expert researcher.",
)

task = Task(
    description="Research the latest AI trends",
    agent=researcher,
)

crew = Crew(
    agents=[researcher],
    tasks=[task],
)

# Trace the crew execution
with handler.trace_crew(crew):
    result = crew.kickoff()
```

### Auto-patching CrewAI

For automatic instrumentation without modifying your code:

```python
from genai_observability import init
from genai_observability.integrations.crewai import patch_crewai

client = init(...)
patch_crewai(client)

# Now all crew executions are automatically traced
crew = Crew(...)
result = crew.kickoff()  # Automatically traced!
```

## MCP Server Tracing

Track interactions with MCP (Model Context Protocol) servers:

```python
with client.tracer.trace_mcp_call(
    server_name="database-server",
    method="query",
    params={"sql": "SELECT * FROM users"},
) as mcp_span:
    result = mcp_client.call("query", {"sql": "SELECT * FROM users"})
    mcp_span.set_result(result)
```

## Custom Metrics and Logging

```python
# Record custom metrics
client.tracer.metric(
    name="cache_hit_rate",
    value=0.85,
    unit="ratio",
    dimensions={"cache_type": "embeddings"},
)

# Log messages
from genai_observability import Severity

client.tracer.log(
    message="Processing completed successfully",
    severity=Severity.INFO,
    context={"items_processed": 100},
)

# Log errors
try:
    risky_operation()
except Exception as e:
    client.tracer.error(
        error=e,
        severity=Severity.ERROR,
        context={"operation": "risky_operation"},
    )
```

## Function Decorator

Easily trace any function:

```python
from genai_observability import trace_function, get_tracer

tracer = get_tracer()

@trace_function(tracer, name="my_tool")
def my_custom_tool(query: str) -> str:
    # Your tool logic
    return f"Result for: {query}"

# Now calls to my_custom_tool are automatically traced
result = my_custom_tool("test query")
```

## Configuration Options

### Full Configuration

```python
from genai_observability import (
    ObservabilityClient,
    ObservabilityConfig,
    RedactionConfig,
    BatchConfig,
    RetryConfig,
)

config = ObservabilityConfig(
    # Required
    api_endpoint="https://observability.example.com",
    api_key="your-api-key",
    agent_id="my-agent",

    # Agent info
    agent_type="custom",
    agent_version="1.0.0",
    environment="production",

    # Feature flags
    enabled=True,
    debug=False,
    sampling_rate=1.0,  # 100% of events

    # Cost tracking
    track_costs=True,

    # Global tags for all events
    global_tags={
        "team": "platform",
        "service": "customer-support",
    },

    # Redaction settings
    redaction=RedactionConfig(
        redact_prompts=False,
        redact_responses=False,
        redact_pii=True,  # Redact emails, SSNs, etc.
        redact_patterns=[
            r"api_key=\w+",  # Custom pattern
        ],
    ),

    # Batching settings
    batch=BatchConfig(
        max_batch_size=100,
        max_batch_interval_seconds=5.0,
        max_queue_size=10000,
    ),

    # Retry settings
    retry=RetryConfig(
        max_retries=3,
        initial_backoff_seconds=1.0,
        max_backoff_seconds=30.0,
    ),
)

client = ObservabilityClient(config=config)
```

### Privacy Controls

```python
# Redact all prompts and responses
config = ObservabilityConfig(
    ...,
    redaction=RedactionConfig(
        redact_prompts=True,
        redact_responses=True,
        redact_tool_inputs=True,
        redact_tool_outputs=True,
    ),
)
```

### Sampling for High-Volume Agents

```python
# Only sample 10% of events
config = ObservabilityConfig(
    ...,
    sampling_rate=0.1,
)
```

## Multi-Region Support

The SDK supports multi-region deployments with automatic failover:

```python
from genai_observability.multi_region import (
    create_multi_region_client,
    RoutingStrategy,
)

# Simple setup with primary and secondary
client = create_multi_region_client(
    primary_endpoint="https://us-east-1.observability.example.com",
    secondary_endpoint="https://eu-west-1.observability.example.com",
    strategy=RoutingStrategy.FAILOVER,
)

# Make requests - automatically routes to healthy region
status, response = client.request("POST", "/api/v1/events", data=events)

# Check health status
health = client.get_health()
print(health)
# {"us-east-1": {"status": "healthy", "latency_ms": 45.2}, ...}
```

### Advanced Multi-Region Configuration

```python
from genai_observability.multi_region import (
    MultiRegionConfig,
    RegionConfig,
    RegionRouter,
    RoutingStrategy,
)

# Configure multiple regions with priorities
config = MultiRegionConfig(
    regions=[
        RegionConfig(
            region_id="us-east-1",
            endpoint="https://us-east-1.observability.example.com",
            priority=1,
            is_primary=True,
            weight=100,
        ),
        RegionConfig(
            region_id="eu-west-1",
            endpoint="https://eu-west-1.observability.example.com",
            priority=2,
            weight=50,
        ),
        RegionConfig(
            region_id="ap-southeast-1",
            endpoint="https://ap-southeast-1.observability.example.com",
            priority=3,
            weight=25,
        ),
    ],
    routing_strategy=RoutingStrategy.LATENCY_BASED,
    enable_health_checks=True,
    health_check_timeout=5,
    retry_count=3,
)

router = RegionRouter(config)
region = router.get_region()  # Returns lowest latency healthy region
```

### Routing Strategies

| Strategy | Description |
|----------|-------------|
| `PRIMARY_ONLY` | Always use primary region |
| `FAILOVER` | Use primary, failover to secondary on failure |
| `ROUND_ROBIN` | Distribute requests across healthy regions |
| `LATENCY_BASED` | Route to lowest latency region |
| `GEOGRAPHIC` | Route based on client location |

## OpenTelemetry Export

Export traces to OpenTelemetry-compatible backends:

```python
from genai_observability.exporters import (
    OTelExporter,
    OTelExporterConfig,
    setup_otel_tracing,
)

# Quick setup
setup_otel_tracing(
    service_name="my-agent",
    exporter_type="otlp",
    otlp_endpoint="http://localhost:4317",
)

# Or configure manually
config = OTelExporterConfig(
    service_name="my-agent",
    exporter_type="otlp",
    otlp_endpoint="http://collector:4317",
    otlp_protocol="grpc",  # or "http"
    otlp_headers={"Authorization": "Bearer token"},
)

exporter = OTelExporter(config)
```

### Supported Exporters

| Exporter | Configuration |
|----------|---------------|
| **OTLP (gRPC)** | `exporter_type="otlp"`, `otlp_protocol="grpc"` |
| **OTLP (HTTP)** | `exporter_type="otlp"`, `otlp_protocol="http"` |
| **Jaeger** | `exporter_type="jaeger"`, `jaeger_host`, `jaeger_port` |
| **Zipkin** | `exporter_type="zipkin"`, `zipkin_endpoint` |
| **Console** | `exporter_type="console"` |

### Bridge Exporter

Send to both the observability platform and OTel backend:

```python
from genai_observability.exporters import OTelBridgeExporter

bridge = OTelBridgeExporter(
    http_exporter=platform_exporter,
    otel_exporter=otel_exporter,
)

# Events are sent to both destinations
bridge.export(event)
```

### GenAI Semantic Conventions

The OTel exporter follows OpenTelemetry GenAI semantic conventions:

| Attribute | Description |
|-----------|-------------|
| `gen_ai.system` | LLM provider (anthropic, openai, etc.) |
| `gen_ai.request.model` | Model name |
| `gen_ai.usage.input_tokens` | Input token count |
| `gen_ai.usage.output_tokens` | Output token count |
| `gen_ai.response.finish_reason` | Why generation stopped |

## Context Manager Usage

```python
# Use as context manager for automatic shutdown
with ObservabilityClient(
    api_endpoint="...",
    api_key="...",
    agent_id="...",
) as client:
    with client.tracer.start_execution() as execution:
        # Your agent logic
        pass
# Client automatically shuts down
```

## Event Types

The SDK captures the following event types:

| Event Type | Description |
|------------|-------------|
| `execution_start` | Agent execution begins |
| `execution_end` | Agent execution completes |
| `llm_call_start` | LLM API call begins |
| `llm_call_end` | LLM API call completes |
| `tool_call_start` | Tool invocation begins |
| `tool_call_end` | Tool invocation completes |
| `mcp_call_start` | MCP server call begins |
| `mcp_call_end` | MCP server call completes |
| `error` | Error occurred |
| `metric` | Custom metric recorded |
| `log` | Log message |

## Best Practices

1. **Initialize Early**: Initialize the client at application startup
2. **Use Context Managers**: Always use `with` statements for proper span management
3. **Set Token Usage**: Always record token usage for accurate cost tracking
4. **Handle Errors**: Errors are automatically captured, but you can add context
5. **Shutdown Gracefully**: Call `shutdown()` or use context managers to ensure all events are sent
6. **Use Sampling**: For high-volume agents, use sampling to reduce costs
7. **Redact Sensitive Data**: Enable redaction for prompts containing sensitive information

## Troubleshooting

### Events Not Appearing

1. Check that `enabled=True` in your configuration
2. Verify your API endpoint and key are correct
3. Enable `debug=True` to see detailed logging
4. Check that `sampling_rate` isn't set too low

### High Memory Usage

1. Reduce `max_queue_size` in BatchConfig
2. Increase `max_batch_interval_seconds` to flush more frequently
3. Enable sampling to reduce event volume

### Missing Token Counts

Ensure you're calling `set_token_usage()` on LLM spans:

```python
with tracer.trace_llm_call(...) as span:
    response = llm.call(...)
    span.set_token_usage(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
```

## License

MIT License - see LICENSE file for details.
