"""
Natural Language Query Routes

Provides endpoints for querying observability data using natural language.
"""

from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_current_user

router = APIRouter()


# Pydantic models
class NLQueryRequest(BaseModel):
    """Natural language query request."""

    query: str = Field(..., description="Natural language query", min_length=3, max_length=1000)
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for the query",
    )


class QueryEntity(BaseModel):
    """Extracted entities from the query."""

    agent_ids: List[str] = []
    metrics: List[str] = []
    time_range: str = "24h"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    filters: Dict[str, Any] = {}
    group_by: List[str] = []
    order_by: Optional[str] = None
    limit: int = 100


class ParsedIntent(BaseModel):
    """Parsed query intent."""

    query_type: str
    intent: str
    entities: QueryEntity
    aggregations: List[str] = []
    comparison: Optional[Dict[str, Any]] = None


class QueryMetadata(BaseModel):
    """Query execution metadata."""

    query_type: str
    time_range: str
    executed_at: str
    execution_time_ms: Optional[float] = None


class NLQueryResponse(BaseModel):
    """Natural language query response."""

    query: str
    parsed_intent: ParsedIntent
    results: Dict[str, Any]
    response: str
    suggestions: List[str]
    metadata: Optional[QueryMetadata] = None


class QueryHistoryItem(BaseModel):
    """Query history item."""

    query_id: str
    query: str
    timestamp: str
    user_id: str
    parsed_intent: Optional[ParsedIntent] = None
    result_count: int = 0


class SavedQuery(BaseModel):
    """Saved query."""

    query_id: str
    name: str
    query: str
    description: Optional[str] = None
    created_at: str
    created_by: str
    is_shared: bool = False
    tags: List[str] = []


class SaveQueryRequest(BaseModel):
    """Request to save a query."""

    name: str = Field(..., min_length=1, max_length=100)
    query: str = Field(..., min_length=3, max_length=1000)
    description: Optional[str] = Field(None, max_length=500)
    is_shared: bool = False
    tags: List[str] = []


# In-memory storage for demo (replace with DynamoDB in production)
_query_history: List[Dict] = []
_saved_queries: Dict[str, Dict] = {}


# Mock NL query processor (replace with Lambda invocation in production)
async def process_nl_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a natural language query.

    In production, this would invoke the nl_query Lambda function.
    """
    import re
    import uuid
    from datetime import timedelta

    # Simple parsing for demo
    query_lower = query.lower()

    # Detect query type
    query_type = "metrics"
    if any(word in query_lower for word in ["error", "fail", "exception"]):
        query_type = "errors"
    elif any(word in query_lower for word in ["trace", "execution"]):
        query_type = "traces"
    elif any(word in query_lower for word in ["agent", "service"]):
        query_type = "agents"
    elif any(word in query_lower for word in ["trend", "over time"]):
        query_type = "trend"

    # Detect time range
    time_range = "24h"
    if "hour" in query_lower:
        time_range = "1h"
    elif "week" in query_lower:
        time_range = "7d"
    elif "month" in query_lower:
        time_range = "30d"

    # Detect metrics
    metrics = []
    if "latency" in query_lower or "response time" in query_lower:
        metrics.append("duration_ms")
    if "token" in query_lower:
        metrics.append("total_tokens")
    if "cost" in query_lower:
        metrics.append("cost")
    if "error" in query_lower:
        metrics.append("error_count")

    if not metrics:
        metrics = ["duration_ms"]

    # Generate mock results based on query type
    mock_data = []

    if query_type == "metrics":
        mock_data = [
            {"agent_id": "agent-1", "duration_ms_avg": 245.5, "request_count": 1523},
            {"agent_id": "agent-2", "duration_ms_avg": 312.8, "request_count": 892},
            {"agent_id": "agent-3", "duration_ms_avg": 178.2, "request_count": 2104},
        ]
    elif query_type == "errors":
        mock_data = [
            {"error_id": "err-1", "error_type": "TimeoutError", "count": 23, "agent_id": "agent-1"},
            {"error_id": "err-2", "error_type": "RateLimitError", "count": 15, "agent_id": "agent-2"},
            {"error_id": "err-3", "error_type": "ValidationError", "count": 8, "agent_id": "agent-1"},
        ]
    elif query_type == "traces":
        mock_data = [
            {"trace_id": "tr-1", "agent_id": "agent-1", "duration_ms": 523, "status": "completed"},
            {"trace_id": "tr-2", "agent_id": "agent-2", "duration_ms": 891, "status": "completed"},
            {"trace_id": "tr-3", "agent_id": "agent-1", "duration_ms": 1234, "status": "error"},
        ]
    elif query_type == "trend":
        # Generate time series data
        now = datetime.utcnow()
        for i in range(24):
            timestamp = (now - timedelta(hours=23 - i)).isoformat() + "Z"
            mock_data.append({
                "time_bucket": timestamp,
                "value": 200 + (i * 5) + (i % 3 * 20),
            })

    # Generate response
    if query_type == "errors":
        response = f"Found {len(mock_data)} error types in the last {time_range}. The most common error is {mock_data[0]['error_type']} with {mock_data[0]['count']} occurrences."
    elif query_type == "traces":
        response = f"Found {len(mock_data)} recent traces. Average duration is {sum(t['duration_ms'] for t in mock_data) / len(mock_data):.0f}ms."
    elif query_type == "trend":
        response = f"Showing {metrics[0]} trend over the last {time_range}. Values range from {min(d['value'] for d in mock_data):.1f} to {max(d['value'] for d in mock_data):.1f}."
    else:
        response = f"Found metrics for {len(mock_data)} agents. Average latency is {sum(d['duration_ms_avg'] for d in mock_data) / len(mock_data):.1f}ms."

    # Generate suggestions
    suggestions = [
        "Show me the trend over the last week",
        "Break down by agent",
        "Compare with yesterday",
        "What's causing the highest latency?",
    ]

    return {
        "query": query,
        "parsed_intent": {
            "query_type": query_type,
            "intent": f"Find {query_type}",
            "entities": {
                "agent_ids": [],
                "metrics": metrics,
                "time_range": time_range,
                "filters": {},
                "group_by": [],
                "limit": 100,
            },
            "aggregations": ["avg"],
        },
        "results": {
            "data": mock_data,
            "metadata": {
                "query_type": query_type,
                "time_range": time_range,
                "executed_at": datetime.utcnow().isoformat() + "Z",
            },
        },
        "response": response,
        "suggestions": suggestions,
    }


# Routes
@router.post("", response_model=NLQueryResponse)
async def execute_nl_query(
    request: NLQueryRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> NLQueryResponse:
    """
    Execute a natural language query against observability data.

    The query is parsed to understand intent, converted to structured queries,
    executed against appropriate data stores, and results are summarized.
    """
    import uuid

    context = request.context or {}
    context["user_id"] = current_user.get("user_id", "")

    # Process the query
    result = await process_nl_query(request.query, context)

    # Store in history
    history_item = {
        "query_id": str(uuid.uuid4()),
        "query": request.query,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": current_user.get("user_id", ""),
        "parsed_intent": result["parsed_intent"],
        "result_count": len(result["results"].get("data", [])),
    }
    _query_history.insert(0, history_item)
    if len(_query_history) > 100:
        _query_history.pop()

    return NLQueryResponse(**result)


@router.get("/suggestions")
async def get_query_suggestions(
    current_user: Annotated[dict, Depends(get_current_user)],
    context: Optional[str] = Query(None, description="Current context (e.g., viewing agent-1)"),
) -> Dict[str, List[str]]:
    """
    Get suggested queries based on current context.
    """
    general_suggestions = [
        "What's the average latency across all agents?",
        "Show me errors in the last hour",
        "Which agent has the highest token usage?",
        "What's the cost breakdown by agent?",
        "Show me the latency trend for the past week",
    ]

    contextual_suggestions = []
    if context:
        if "agent" in context.lower():
            agent_id = context.split(":")[-1] if ":" in context else context
            contextual_suggestions = [
                f"Show me recent traces for {agent_id}",
                f"What errors is {agent_id} experiencing?",
                f"Compare {agent_id} latency with other agents",
                f"Show {agent_id} token usage trend",
            ]

    return {
        "general": general_suggestions,
        "contextual": contextual_suggestions,
    }


@router.get("/history", response_model=List[QueryHistoryItem])
async def get_query_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(20, ge=1, le=100),
) -> List[QueryHistoryItem]:
    """
    Get recent query history for the current user.
    """
    user_id = current_user.get("user_id", "")
    user_history = [
        QueryHistoryItem(**h)
        for h in _query_history
        if h.get("user_id") == user_id
    ][:limit]

    return user_history


@router.post("/saved", response_model=SavedQuery)
async def save_query(
    request: SaveQueryRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SavedQuery:
    """
    Save a query for later use.
    """
    import uuid

    query_id = str(uuid.uuid4())
    saved_query = SavedQuery(
        query_id=query_id,
        name=request.name,
        query=request.query,
        description=request.description,
        created_at=datetime.utcnow().isoformat() + "Z",
        created_by=current_user.get("user_id", ""),
        is_shared=request.is_shared,
        tags=request.tags,
    )

    _saved_queries[query_id] = saved_query.model_dump()
    return saved_query


@router.get("/saved", response_model=List[SavedQuery])
async def list_saved_queries(
    current_user: Annotated[dict, Depends(get_current_user)],
    include_shared: bool = Query(True, description="Include shared queries"),
) -> List[SavedQuery]:
    """
    List saved queries for the current user.
    """
    user_id = current_user.get("user_id", "")

    queries = []
    for q in _saved_queries.values():
        if q["created_by"] == user_id or (include_shared and q["is_shared"]):
            queries.append(SavedQuery(**q))

    return sorted(queries, key=lambda x: x.created_at, reverse=True)


@router.get("/saved/{query_id}", response_model=SavedQuery)
async def get_saved_query(
    query_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SavedQuery:
    """
    Get a saved query by ID.
    """
    if query_id not in _saved_queries:
        raise HTTPException(status_code=404, detail="Query not found")

    query = _saved_queries[query_id]
    user_id = current_user.get("user_id", "")

    if query["created_by"] != user_id and not query["is_shared"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return SavedQuery(**query)


@router.delete("/saved/{query_id}")
async def delete_saved_query(
    query_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> Dict[str, str]:
    """
    Delete a saved query.
    """
    if query_id not in _saved_queries:
        raise HTTPException(status_code=404, detail="Query not found")

    query = _saved_queries[query_id]
    user_id = current_user.get("user_id", "")

    if query["created_by"] != user_id:
        raise HTTPException(status_code=403, detail="Only the creator can delete this query")

    del _saved_queries[query_id]
    return {"message": "Query deleted"}


@router.post("/saved/{query_id}/execute", response_model=NLQueryResponse)
async def execute_saved_query(
    query_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    context: Optional[Dict[str, Any]] = None,
) -> NLQueryResponse:
    """
    Execute a saved query.
    """
    if query_id not in _saved_queries:
        raise HTTPException(status_code=404, detail="Query not found")

    saved_query = _saved_queries[query_id]
    user_id = current_user.get("user_id", "")

    if saved_query["created_by"] != user_id and not saved_query["is_shared"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Execute the query
    request = NLQueryRequest(query=saved_query["query"], context=context)
    return await execute_nl_query(request, current_user)


@router.get("/examples")
async def get_example_queries() -> Dict[str, List[Dict[str, str]]]:
    """
    Get example queries organized by category.
    """
    return {
        "metrics": [
            {"query": "What's the average latency?", "description": "Get average latency across all agents"},
            {"query": "Show me token usage for the past week", "description": "Token consumption trend"},
            {"query": "What's our total cost today?", "description": "Daily cost summary"},
        ],
        "errors": [
            {"query": "What errors occurred in the last hour?", "description": "Recent error summary"},
            {"query": "Which agent has the most errors?", "description": "Error hotspots"},
            {"query": "Show me timeout errors", "description": "Filter by error type"},
        ],
        "traces": [
            {"query": "Show me the slowest traces", "description": "Performance outliers"},
            {"query": "Find traces with errors", "description": "Failed executions"},
            {"query": "What's the p95 latency?", "description": "Latency percentiles"},
        ],
        "comparisons": [
            {"query": "Compare latency between agent-1 and agent-2", "description": "Agent comparison"},
            {"query": "How does today compare to yesterday?", "description": "Time comparison"},
            {"query": "Which agent improved the most this week?", "description": "Trend comparison"},
        ],
    }
