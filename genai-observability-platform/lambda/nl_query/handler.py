"""
Natural Language Query Lambda

Converts natural language queries to structured queries against the
observability data stores (DynamoDB, Timestream, OpenSearch).

Uses Claude to understand intent and generate appropriate queries.
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
ANTHROPIC_SECRET_ARN = os.environ.get("ANTHROPIC_SECRET_ARN", "")
TIMESTREAM_DATABASE = os.environ.get("TIMESTREAM_DATABASE", "")
TIMESTREAM_LATENCY_TABLE = os.environ.get("TIMESTREAM_LATENCY_TABLE", "latency-metrics")
TIMESTREAM_METRICS_TABLE = os.environ.get("TIMESTREAM_METRICS_TABLE", "metrics")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
TRACES_TABLE = os.environ.get("TRACES_TABLE", "")
ERRORS_TABLE = os.environ.get("ERROR_STORE_TABLE", "")
AGENTS_TABLE = os.environ.get("AGENTS_TABLE", "")

# Model configuration
MODEL_ID = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4000"))

# Initialize clients
secrets = boto3.client("secretsmanager")
dynamodb = boto3.resource("dynamodb")
timestream_query = boto3.client("timestream-query")

# Cached Anthropic client
_anthropic_client = None


class QueryType(str, Enum):
    """Types of queries."""
    METRICS = "metrics"
    TRACES = "traces"
    ERRORS = "errors"
    AGENTS = "agents"
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    TREND = "trend"
    INVESTIGATION = "investigation"


class TimeRange(str, Enum):
    """Common time ranges."""
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"


def get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client

    if _anthropic_client is None and ANTHROPIC_SECRET_ARN:
        try:
            secret_response = secrets.get_secret_value(SecretId=ANTHROPIC_SECRET_ARN)
            api_key = json.loads(secret_response["SecretString"])["api_key"]

            from anthropic import Anthropic

            _anthropic_client = Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"Error initializing Anthropic client: {e}")
            return None

    return _anthropic_client


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for natural language queries.

    Args:
        event: Contains the natural language query
        context: Lambda context

    Returns:
        Query results and explanation
    """
    query = event.get("query", "")
    user_id = event.get("user_id", "")
    context_data = event.get("context", {})

    if not query:
        return {
            "statusCode": 400,
            "error": "Query is required",
        }

    logger.info(f"Processing NL query: {query[:100]}...")

    try:
        # Parse the query to understand intent
        parsed = parse_query(query, context_data)

        # Execute the appropriate queries
        results = execute_query(parsed)

        # Generate natural language response
        response = generate_response(query, parsed, results)

        return {
            "statusCode": 200,
            "query": query,
            "parsed_intent": parsed,
            "results": results,
            "response": response,
            "suggestions": generate_follow_up_suggestions(query, parsed, results),
        }

    except Exception as e:
        logger.error(f"Query processing error: {e}")
        return {
            "statusCode": 500,
            "error": str(e),
            "query": query,
        }


def parse_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to parse natural language query into structured format.

    Args:
        query: Natural language query
        context: Additional context (current agent, time range, etc.)

    Returns:
        Parsed query structure
    """
    client = get_anthropic_client()
    if client is None:
        # Fallback to rule-based parsing
        return fallback_parse(query)

    system_prompt = """You are a query parser for a GenAI observability platform. Parse the user's natural language query into a structured format.

Available data sources:
- metrics: Timestream metrics (latency, token usage, costs, error rates)
- traces: DynamoDB traces (execution traces, spans)
- errors: DynamoDB errors (error events, stack traces)
- agents: DynamoDB agents (registered agents, configurations)

Available metrics:
- duration_ms: Execution latency in milliseconds
- input_tokens: LLM input tokens
- output_tokens: LLM output tokens
- total_tokens: Total tokens used
- cost: Cost in USD
- error_count: Number of errors
- request_count: Number of requests

Return a JSON object with:
{
    "query_type": "metrics|traces|errors|agents|aggregation|comparison|trend|investigation",
    "intent": "brief description of what the user wants",
    "entities": {
        "agent_ids": ["list of agent IDs mentioned"],
        "metrics": ["list of metrics to query"],
        "time_range": "1h|6h|24h|7d|30d",
        "start_time": "ISO timestamp if specific",
        "end_time": "ISO timestamp if specific",
        "filters": {"key": "value"},
        "group_by": ["fields to group by"],
        "order_by": "field to order by",
        "limit": number
    },
    "aggregations": ["sum|avg|min|max|count|p50|p95|p99"],
    "comparison": {
        "type": "time|agents|none",
        "compare_to": "previous period or agent list"
    }
}"""

    user_prompt = f"""Parse this query: "{query}"

Current context:
- Current time: {datetime.utcnow().isoformat()}
- Active agent filter: {context.get('agent_id', 'none')}
- Default time range: {context.get('time_range', '24h')}

Return only the JSON object, no explanation."""

    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=1000,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())

    except Exception as e:
        logger.error(f"LLM parsing error: {e}")

    return fallback_parse(query)


def fallback_parse(query: str) -> Dict[str, Any]:
    """Rule-based fallback parser when LLM is unavailable."""
    query_lower = query.lower()

    parsed = {
        "query_type": QueryType.METRICS.value,
        "intent": "Unknown",
        "entities": {
            "agent_ids": [],
            "metrics": [],
            "time_range": "24h",
            "filters": {},
            "limit": 100,
        },
        "aggregations": [],
    }

    # Detect query type
    if any(word in query_lower for word in ["error", "fail", "exception"]):
        parsed["query_type"] = QueryType.ERRORS.value
        parsed["intent"] = "Find errors"
    elif any(word in query_lower for word in ["trace", "execution", "span"]):
        parsed["query_type"] = QueryType.TRACES.value
        parsed["intent"] = "Find traces"
    elif any(word in query_lower for word in ["agent", "service"]):
        parsed["query_type"] = QueryType.AGENTS.value
        parsed["intent"] = "Get agent information"
    elif any(word in query_lower for word in ["trend", "over time", "history"]):
        parsed["query_type"] = QueryType.TREND.value
        parsed["intent"] = "Show trend"
    elif any(word in query_lower for word in ["compare", "versus", "vs"]):
        parsed["query_type"] = QueryType.COMPARISON.value
        parsed["intent"] = "Compare metrics"

    # Detect time range
    time_patterns = [
        (r"last\s+(\d+)\s+hour", lambda m: f"{m.group(1)}h"),
        (r"last\s+(\d+)\s+day", lambda m: f"{m.group(1)}d"),
        (r"past\s+hour", lambda m: "1h"),
        (r"past\s+day|yesterday", lambda m: "24h"),
        (r"past\s+week|last\s+week", lambda m: "7d"),
        (r"past\s+month|last\s+month", lambda m: "30d"),
    ]

    for pattern, extractor in time_patterns:
        match = re.search(pattern, query_lower)
        if match:
            parsed["entities"]["time_range"] = extractor(match)
            break

    # Detect metrics
    metric_keywords = {
        "latency": "duration_ms",
        "response time": "duration_ms",
        "tokens": "total_tokens",
        "cost": "cost",
        "errors": "error_count",
        "requests": "request_count",
    }

    for keyword, metric in metric_keywords.items():
        if keyword in query_lower:
            parsed["entities"]["metrics"].append(metric)

    # Detect aggregations
    if "average" in query_lower or "avg" in query_lower:
        parsed["aggregations"].append("avg")
    if "total" in query_lower or "sum" in query_lower:
        parsed["aggregations"].append("sum")
    if "maximum" in query_lower or "max" in query_lower:
        parsed["aggregations"].append("max")
    if "minimum" in query_lower or "min" in query_lower:
        parsed["aggregations"].append("min")
    if "p95" in query_lower or "95th percentile" in query_lower:
        parsed["aggregations"].append("p95")
    if "p99" in query_lower or "99th percentile" in query_lower:
        parsed["aggregations"].append("p99")

    # Default aggregation
    if not parsed["aggregations"]:
        parsed["aggregations"].append("avg")

    return parsed


def execute_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the parsed query against appropriate data stores.

    Args:
        parsed: Parsed query structure

    Returns:
        Query results
    """
    query_type = parsed.get("query_type", "")
    entities = parsed.get("entities", {})
    aggregations = parsed.get("aggregations", ["avg"])

    results = {
        "data": [],
        "metadata": {
            "query_type": query_type,
            "time_range": entities.get("time_range", "24h"),
            "executed_at": datetime.utcnow().isoformat() + "Z",
        },
    }

    try:
        if query_type == QueryType.METRICS.value:
            results["data"] = query_metrics(entities, aggregations)
        elif query_type == QueryType.TRACES.value:
            results["data"] = query_traces(entities)
        elif query_type == QueryType.ERRORS.value:
            results["data"] = query_errors(entities)
        elif query_type == QueryType.AGENTS.value:
            results["data"] = query_agents(entities)
        elif query_type == QueryType.TREND.value:
            results["data"] = query_trend(entities, aggregations)
        elif query_type == QueryType.COMPARISON.value:
            results["data"] = query_comparison(parsed)
        elif query_type == QueryType.AGGREGATION.value:
            results["data"] = query_aggregation(entities, aggregations)
        else:
            results["data"] = query_metrics(entities, aggregations)

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        results["error"] = str(e)

    return results


def query_metrics(entities: Dict[str, Any], aggregations: List[str]) -> List[Dict]:
    """Query metrics from Timestream."""
    if not TIMESTREAM_DATABASE:
        return []

    time_range = entities.get("time_range", "24h")
    metrics = entities.get("metrics", ["duration_ms"])
    agent_ids = entities.get("agent_ids", [])
    group_by = entities.get("group_by", [])

    # Build aggregation functions
    agg_funcs = []
    for metric in metrics:
        for agg in aggregations:
            if agg == "avg":
                agg_funcs.append(f"AVG(measure_value::double) as {metric}_{agg}")
            elif agg == "sum":
                agg_funcs.append(f"SUM(measure_value::double) as {metric}_{agg}")
            elif agg == "min":
                agg_funcs.append(f"MIN(measure_value::double) as {metric}_{agg}")
            elif agg == "max":
                agg_funcs.append(f"MAX(measure_value::double) as {metric}_{agg}")
            elif agg == "count":
                agg_funcs.append(f"COUNT(*) as {metric}_count")
            elif agg == "p95":
                agg_funcs.append(f"approx_percentile(measure_value::double, 0.95) as {metric}_p95")
            elif agg == "p99":
                agg_funcs.append(f"approx_percentile(measure_value::double, 0.99) as {metric}_p99")

    select_clause = ", ".join(agg_funcs) if agg_funcs else "AVG(measure_value::double) as value"

    # Build WHERE clause
    where_conditions = [f"time >= ago({time_range})"]

    if metrics:
        metric_list = ", ".join([f"'{m}'" for m in metrics])
        where_conditions.append(f"measure_name IN ({metric_list})")

    if agent_ids:
        agent_list = ", ".join([f"'{a}'" for a in agent_ids])
        where_conditions.append(f"agent_id IN ({agent_list})")

    where_clause = " AND ".join(where_conditions)

    # Build GROUP BY
    group_clause = ""
    if group_by:
        group_clause = f"GROUP BY {', '.join(group_by)}"
        select_clause = f"{', '.join(group_by)}, " + select_clause

    query = f"""
    SELECT {select_clause}
    FROM "{TIMESTREAM_DATABASE}"."{TIMESTREAM_LATENCY_TABLE}"
    WHERE {where_clause}
    {group_clause}
    """

    try:
        response = timestream_query.query(QueryString=query)
        return parse_timestream_results(response)
    except Exception as e:
        logger.error(f"Timestream query error: {e}")
        return []


def query_trend(entities: Dict[str, Any], aggregations: List[str]) -> List[Dict]:
    """Query trend data with time bucketing."""
    if not TIMESTREAM_DATABASE:
        return []

    time_range = entities.get("time_range", "24h")
    metrics = entities.get("metrics", ["duration_ms"])

    # Determine bucket size based on time range
    bucket_map = {
        "1h": "1m",
        "6h": "5m",
        "24h": "1h",
        "7d": "6h",
        "30d": "1d",
    }
    bucket_size = bucket_map.get(time_range, "1h")

    # Build query
    metric = metrics[0] if metrics else "duration_ms"
    agg = aggregations[0] if aggregations else "avg"

    agg_func = {
        "avg": "AVG",
        "sum": "SUM",
        "min": "MIN",
        "max": "MAX",
        "count": "COUNT",
    }.get(agg, "AVG")

    query = f"""
    SELECT
        BIN(time, {bucket_size}) as time_bucket,
        agent_id,
        {agg_func}(measure_value::double) as value
    FROM "{TIMESTREAM_DATABASE}"."{TIMESTREAM_LATENCY_TABLE}"
    WHERE measure_name = '{metric}'
        AND time >= ago({time_range})
    GROUP BY BIN(time, {bucket_size}), agent_id
    ORDER BY time_bucket ASC
    """

    try:
        response = timestream_query.query(QueryString=query)
        return parse_timestream_results(response)
    except Exception as e:
        logger.error(f"Trend query error: {e}")
        return []


def query_traces(entities: Dict[str, Any]) -> List[Dict]:
    """Query traces from DynamoDB."""
    if not TRACES_TABLE:
        return []

    limit = entities.get("limit", 100)
    agent_ids = entities.get("agent_ids", [])
    filters = entities.get("filters", {})

    try:
        table = dynamodb.Table(TRACES_TABLE)

        if agent_ids:
            # Query by agent_id
            results = []
            for agent_id in agent_ids[:5]:  # Limit to 5 agents
                response = table.query(
                    IndexName="agent-timestamp-index",
                    KeyConditionExpression="agent_id = :agent_id",
                    ExpressionAttributeValues={":agent_id": agent_id},
                    Limit=limit // len(agent_ids),
                    ScanIndexForward=False,
                )
                results.extend(response.get("Items", []))
            return results
        else:
            # Scan with filters
            scan_kwargs = {"Limit": limit}

            if filters:
                filter_expr = []
                expr_values = {}
                for i, (key, value) in enumerate(filters.items()):
                    filter_expr.append(f"{key} = :val{i}")
                    expr_values[f":val{i}"] = value

                if filter_expr:
                    scan_kwargs["FilterExpression"] = " AND ".join(filter_expr)
                    scan_kwargs["ExpressionAttributeValues"] = expr_values

            response = table.scan(**scan_kwargs)
            return response.get("Items", [])

    except Exception as e:
        logger.error(f"Traces query error: {e}")
        return []


def query_errors(entities: Dict[str, Any]) -> List[Dict]:
    """Query errors from DynamoDB."""
    if not ERRORS_TABLE:
        return []

    limit = entities.get("limit", 100)
    agent_ids = entities.get("agent_ids", [])
    time_range = entities.get("time_range", "24h")

    # Calculate time cutoff
    hours = int(time_range.replace("h", "").replace("d", "")) * (24 if "d" in time_range else 1)
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        table = dynamodb.Table(ERRORS_TABLE)

        if agent_ids:
            results = []
            for agent_id in agent_ids[:5]:
                response = table.query(
                    IndexName="agent-timestamp-index",
                    KeyConditionExpression="agent_id = :agent_id AND #ts >= :cutoff",
                    ExpressionAttributeNames={"#ts": "timestamp"},
                    ExpressionAttributeValues={
                        ":agent_id": agent_id,
                        ":cutoff": cutoff,
                    },
                    Limit=limit // max(len(agent_ids), 1),
                    ScanIndexForward=False,
                )
                results.extend(response.get("Items", []))
            return results
        else:
            response = table.scan(
                FilterExpression="#ts >= :cutoff",
                ExpressionAttributeNames={"#ts": "timestamp"},
                ExpressionAttributeValues={":cutoff": cutoff},
                Limit=limit,
            )
            return response.get("Items", [])

    except Exception as e:
        logger.error(f"Errors query error: {e}")
        return []


def query_agents(entities: Dict[str, Any]) -> List[Dict]:
    """Query agent information."""
    if not AGENTS_TABLE:
        return []

    agent_ids = entities.get("agent_ids", [])

    try:
        table = dynamodb.Table(AGENTS_TABLE)

        if agent_ids:
            results = []
            for agent_id in agent_ids:
                response = table.get_item(Key={"agent_id": agent_id})
                if "Item" in response:
                    results.append(response["Item"])
            return results
        else:
            response = table.scan(Limit=entities.get("limit", 100))
            return response.get("Items", [])

    except Exception as e:
        logger.error(f"Agents query error: {e}")
        return []


def query_comparison(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Execute comparison query."""
    comparison = parsed.get("comparison", {})
    entities = parsed.get("entities", {})
    aggregations = parsed.get("aggregations", ["avg"])

    comparison_type = comparison.get("type", "time")

    if comparison_type == "time":
        # Compare current period with previous period
        current_results = query_metrics(entities, aggregations)

        # Modify time range for previous period
        prev_entities = entities.copy()
        time_range = entities.get("time_range", "24h")
        hours = int(time_range.replace("h", "").replace("d", "")) * (24 if "d" in time_range else 1)

        end_time = datetime.utcnow() - timedelta(hours=hours)
        start_time = end_time - timedelta(hours=hours)

        prev_entities["start_time"] = start_time.isoformat()
        prev_entities["end_time"] = end_time.isoformat()
        prev_entities.pop("time_range", None)

        previous_results = query_metrics(prev_entities, aggregations)

        return {
            "current_period": current_results,
            "previous_period": previous_results,
            "comparison_type": "time",
        }

    elif comparison_type == "agents":
        # Compare between agents
        compare_agents = comparison.get("compare_to", [])
        entities["agent_ids"] = compare_agents
        entities["group_by"] = ["agent_id"]

        return query_metrics(entities, aggregations)

    return {}


def query_aggregation(entities: Dict[str, Any], aggregations: List[str]) -> List[Dict]:
    """Execute aggregation query."""
    return query_metrics(entities, aggregations)


def parse_timestream_results(response: Dict) -> List[Dict]:
    """Parse Timestream query results into a list of dictionaries."""
    results = []
    columns = [col["Name"] for col in response.get("ColumnInfo", [])]

    for row in response.get("Rows", []):
        record = {}
        for i, datum in enumerate(row.get("Data", [])):
            value = datum.get("ScalarValue")
            if value is not None:
                # Try to convert to number
                try:
                    if "." in value:
                        record[columns[i]] = float(value)
                    else:
                        record[columns[i]] = int(value)
                except ValueError:
                    record[columns[i]] = value
        results.append(record)

    return results


def generate_response(
    query: str,
    parsed: Dict[str, Any],
    results: Dict[str, Any],
) -> str:
    """
    Generate natural language response explaining the results.

    Args:
        query: Original query
        parsed: Parsed query structure
        results: Query results

    Returns:
        Natural language response
    """
    client = get_anthropic_client()
    if client is None:
        return generate_fallback_response(parsed, results)

    prompt = f"""You are explaining query results to a user of a GenAI observability platform.

Original query: "{query}"

Parsed intent: {json.dumps(parsed.get('intent', 'Unknown'))}

Results summary:
- Number of records: {len(results.get('data', []))}
- Time range: {results.get('metadata', {}).get('time_range', 'Unknown')}
- Sample data: {json.dumps(results.get('data', [])[:5], default=str)}

Provide a concise, helpful response that:
1. Directly answers the user's question
2. Highlights key insights from the data
3. Notes any anomalies or important trends
4. Uses specific numbers where relevant

Keep the response under 200 words."""

    try:
        message = client.messages.create(
            model=MODEL_ID,
            max_tokens=500,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        return generate_fallback_response(parsed, results)


def generate_fallback_response(parsed: Dict[str, Any], results: Dict[str, Any]) -> str:
    """Generate a simple response without LLM."""
    data = results.get("data", [])
    query_type = parsed.get("query_type", "")
    time_range = results.get("metadata", {}).get("time_range", "24h")

    if not data:
        return f"No {query_type} data found for the specified time range ({time_range})."

    if query_type == QueryType.METRICS.value:
        if isinstance(data, list) and data:
            first_record = data[0]
            metrics_summary = ", ".join([f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}" for k, v in first_record.items()])
            return f"Found {len(data)} records. Summary: {metrics_summary}"

    elif query_type == QueryType.ERRORS.value:
        return f"Found {len(data)} errors in the last {time_range}."

    elif query_type == QueryType.TRACES.value:
        return f"Found {len(data)} traces in the last {time_range}."

    return f"Query returned {len(data)} results."


def generate_follow_up_suggestions(
    query: str,
    parsed: Dict[str, Any],
    results: Dict[str, Any],
) -> List[str]:
    """Generate follow-up query suggestions."""
    suggestions = []
    query_type = parsed.get("query_type", "")
    entities = parsed.get("entities", {})

    if query_type == QueryType.METRICS.value:
        suggestions.extend([
            "Show me the trend over the last week",
            "Compare with the previous period",
            "Break down by agent",
        ])

    elif query_type == QueryType.ERRORS.value:
        suggestions.extend([
            "What's the most common error type?",
            "Show error trend over time",
            "Which agent has the most errors?",
        ])

    elif query_type == QueryType.TRACES.value:
        suggestions.extend([
            "Show me the slowest traces",
            "What's the average latency?",
            "Show traces with errors",
        ])

    # Add time-based suggestions
    time_range = entities.get("time_range", "24h")
    if time_range == "1h":
        suggestions.append("Expand to last 24 hours")
    elif time_range == "24h":
        suggestions.append("Show last week instead")

    return suggestions[:4]  # Limit to 4 suggestions
