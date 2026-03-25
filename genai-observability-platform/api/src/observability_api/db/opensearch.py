"""OpenSearch client for full-text search."""

from datetime import datetime, timedelta
from typing import Any

from opensearchpy import OpenSearch, RequestsHttpConnection

from ..config import get_settings


class OpenSearchClient:
    """OpenSearch client wrapper."""

    def __init__(self) -> None:
        """Initialize OpenSearch client."""
        settings = get_settings()
        self._settings = settings
        self._index_prefix = settings.opensearch_index_prefix

        if settings.opensearch_endpoint:
            self._client = OpenSearch(
                hosts=[{"host": settings.opensearch_endpoint, "port": 443}],
                http_auth=None,  # Uses IAM auth via request signing
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
            )
        else:
            self._client = None

    def _get_time_range(self, period: str) -> tuple[datetime, datetime]:
        """Convert period string to time range."""
        now = datetime.utcnow()
        periods = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = periods.get(period, timedelta(hours=24))
        return now - delta, now

    async def search_traces(
        self,
        query: str | None = None,
        agent_id: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search traces with full-text search and filters."""
        if not self._client:
            return [], 0

        must_clauses: list[dict[str, Any]] = []
        filter_clauses: list[dict[str, Any]] = []

        # Full-text search on name and metadata
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^2", "agent_id", "metadata.*"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            })

        # Filters
        if agent_id:
            filter_clauses.append({"term": {"agent_id": agent_id}})

        if status:
            filter_clauses.append({"term": {"status": status}})

        if start_time or end_time:
            range_filter: dict[str, Any] = {"range": {"start_time": {}}}
            if start_time:
                range_filter["range"]["start_time"]["gte"] = start_time.isoformat()
            if end_time:
                range_filter["range"]["start_time"]["lte"] = end_time.isoformat()
            filter_clauses.append(range_filter)

        # Build query
        search_body: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "sort": [{"start_time": {"order": "desc"}}],
            "from": (page - 1) * page_size,
            "size": page_size,
        }

        try:
            response = self._client.search(
                index=f"{self._index_prefix}-traces",
                body=search_body,
            )

            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            items = [hit["_source"] for hit in hits.get("hits", [])]

            return items, total
        except Exception as e:
            print(f"OpenSearch query error: {e}")
            return [], 0

    async def search_spans(
        self,
        trace_id: str | None = None,
        query: str | None = None,
        span_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search spans within traces."""
        if not self._client:
            return [], 0

        must_clauses: list[dict[str, Any]] = []
        filter_clauses: list[dict[str, Any]] = []

        if trace_id:
            filter_clauses.append({"term": {"trace_id": trace_id}})

        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["name^2", "attributes.*"],
                }
            })

        if span_type:
            filter_clauses.append({"term": {"span_type": span_type}})

        search_body: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "sort": [{"start_time": {"order": "asc"}}],
            "from": (page - 1) * page_size,
            "size": page_size,
        }

        try:
            response = self._client.search(
                index=f"{self._index_prefix}-spans",
                body=search_body,
            )

            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            items = [hit["_source"] for hit in hits.get("hits", [])]

            return items, total
        except Exception as e:
            print(f"OpenSearch query error: {e}")
            return [], 0

    async def search_errors(
        self,
        agent_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search error events."""
        if not self._client:
            return [], 0

        filter_clauses: list[dict[str, Any]] = [{"term": {"status": "error"}}]

        if agent_id:
            filter_clauses.append({"term": {"agent_id": agent_id}})

        if start_time or end_time:
            range_filter: dict[str, Any] = {"range": {"timestamp": {}}}
            if start_time:
                range_filter["range"]["timestamp"]["gte"] = start_time.isoformat()
            if end_time:
                range_filter["range"]["timestamp"]["lte"] = end_time.isoformat()
            filter_clauses.append(range_filter)

        search_body: dict[str, Any] = {
            "query": {"bool": {"filter": filter_clauses}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "from": (page - 1) * page_size,
            "size": page_size,
        }

        try:
            response = self._client.search(
                index=f"{self._index_prefix}-errors",
                body=search_body,
            )

            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            items = [hit["_source"] for hit in hits.get("hits", [])]

            return items, total
        except Exception as e:
            print(f"OpenSearch query error: {e}")
            return [], 0

    async def get_agent_count(self) -> int:
        """Get total number of unique agents."""
        if not self._client:
            return 0

        try:
            response = self._client.search(
                index=f"{self._index_prefix}-traces",
                body={
                    "size": 0,
                    "aggs": {
                        "unique_agents": {
                            "cardinality": {"field": "agent_id"}
                        }
                    },
                },
            )
            return response.get("aggregations", {}).get("unique_agents", {}).get("value", 0)
        except Exception:
            return 0
