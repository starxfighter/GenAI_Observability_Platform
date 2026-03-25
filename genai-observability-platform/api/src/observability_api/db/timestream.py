"""Timestream client for metrics queries."""

from datetime import datetime, timedelta
from typing import Any

import boto3

from ..config import get_settings


class TimestreamClient:
    """Timestream query client wrapper."""

    def __init__(self) -> None:
        """Initialize Timestream client."""
        settings = get_settings()
        self._client = boto3.client("timestream-query", region_name=settings.aws_region)
        self._database = settings.timestream_database
        self._table = settings.timestream_table

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

    def _execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a Timestream query."""
        try:
            paginator = self._client.get_paginator("query")
            results = []

            for page in paginator.paginate(QueryString=query):
                columns = [col["Name"] for col in page["ColumnInfo"]]
                for row in page["Rows"]:
                    record = {}
                    for i, col in enumerate(columns):
                        datum = row["Data"][i]
                        if "ScalarValue" in datum:
                            record[col] = datum["ScalarValue"]
                        elif "NullValue" in datum:
                            record[col] = None
                    results.append(record)

            return results
        except Exception as e:
            # Log error and return empty list
            print(f"Timestream query error: {e}")
            return []

    async def get_dashboard_metrics(self, period: str) -> dict[str, Any]:
        """Get dashboard overview metrics."""
        start_time, end_time = self._get_time_range(period)

        # Query for aggregated metrics
        query = f"""
            SELECT
                COUNT(*) as total_traces,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as total_errors,
                AVG(duration_ms) as avg_latency_ms,
                approx_percentile(duration_ms, 0.95) as p95_latency_ms,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost
            FROM "{self._database}"."{self._table}"
            WHERE time BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
                AND measure_name = 'trace_metrics'
        """

        results = self._execute_query(query)

        if results:
            row = results[0]
            return {
                "period": period,
                "total_traces": int(row.get("total_traces", 0) or 0),
                "total_errors": int(row.get("total_errors", 0) or 0),
                "avg_latency_ms": float(row.get("avg_latency_ms", 0) or 0),
                "p95_latency_ms": float(row.get("p95_latency_ms", 0) or 0),
                "total_tokens": int(row.get("total_tokens", 0) or 0),
                "total_cost": float(row.get("total_cost", 0) or 0),
            }

        return {
            "period": period,
            "total_traces": 0,
            "total_errors": 0,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "total_tokens": 0,
            "total_cost": 0,
        }

    async def get_latency_series(
        self, period: str, agent_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get latency time series data."""
        start_time, end_time = self._get_time_range(period)

        # Determine bucket size based on period
        bucket_sizes = {
            "1h": "1m",
            "6h": "5m",
            "24h": "15m",
            "7d": "1h",
            "30d": "6h",
        }
        bucket = bucket_sizes.get(period, "15m")

        agent_filter = f"AND agent_id = '{agent_id}'" if agent_id else ""

        query = f"""
            SELECT
                bin(time, {bucket}) as timestamp,
                AVG(duration_ms) as value,
                approx_percentile(duration_ms, 0.95) as p95
            FROM "{self._database}"."{self._table}"
            WHERE time BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
                AND measure_name = 'trace_metrics'
                {agent_filter}
            GROUP BY bin(time, {bucket})
            ORDER BY timestamp ASC
        """

        return self._execute_query(query)

    async def get_request_series(
        self, period: str, agent_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get request count time series data."""
        start_time, end_time = self._get_time_range(period)

        bucket_sizes = {
            "1h": "1m",
            "6h": "5m",
            "24h": "15m",
            "7d": "1h",
            "30d": "6h",
        }
        bucket = bucket_sizes.get(period, "15m")

        agent_filter = f"AND agent_id = '{agent_id}'" if agent_id else ""

        query = f"""
            SELECT
                bin(time, {bucket}) as timestamp,
                COUNT(*) as value
            FROM "{self._database}"."{self._table}"
            WHERE time BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
                AND measure_name = 'trace_metrics'
                {agent_filter}
            GROUP BY bin(time, {bucket})
            ORDER BY timestamp ASC
        """

        return self._execute_query(query)

    async def get_agent_metrics(self, agent_id: str, period: str) -> dict[str, Any]:
        """Get metrics for a specific agent."""
        start_time, end_time = self._get_time_range(period)

        query = f"""
            SELECT
                COUNT(*) as request_count,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                AVG(duration_ms) as avg_latency_ms,
                approx_percentile(duration_ms, 0.50) as p50_latency_ms,
                approx_percentile(duration_ms, 0.95) as p95_latency_ms,
                approx_percentile(duration_ms, 0.99) as p99_latency_ms,
                SUM(total_tokens) as total_tokens,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(cost) as total_cost
            FROM "{self._database}"."{self._table}"
            WHERE time BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
                AND measure_name = 'trace_metrics'
                AND agent_id = '{agent_id}'
        """

        results = self._execute_query(query)

        if results:
            row = results[0]
            request_count = int(row.get("request_count", 0) or 0)
            error_count = int(row.get("error_count", 0) or 0)
            error_rate = error_count / request_count if request_count > 0 else 0

            return {
                "agent_id": agent_id,
                "period": period,
                "request_count": request_count,
                "error_count": error_count,
                "error_rate": error_rate,
                "avg_latency_ms": float(row.get("avg_latency_ms", 0) or 0),
                "p50_latency_ms": float(row.get("p50_latency_ms", 0) or 0),
                "p95_latency_ms": float(row.get("p95_latency_ms", 0) or 0),
                "p99_latency_ms": float(row.get("p99_latency_ms", 0) or 0),
                "total_tokens": int(row.get("total_tokens", 0) or 0),
                "input_tokens": int(row.get("input_tokens", 0) or 0),
                "output_tokens": int(row.get("output_tokens", 0) or 0),
                "total_cost": float(row.get("total_cost", 0) or 0),
            }

        return {
            "agent_id": agent_id,
            "period": period,
            "request_count": 0,
            "error_count": 0,
            "error_rate": 0,
            "avg_latency_ms": 0,
            "p50_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost": 0,
        }

    async def get_error_rate(self, agent_id: str, window_minutes: int = 5) -> float:
        """Get current error rate for anomaly detection."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=window_minutes)

        query = f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors
            FROM "{self._database}"."{self._table}"
            WHERE time BETWEEN '{start_time.isoformat()}' AND '{end_time.isoformat()}'
                AND measure_name = 'trace_metrics'
                AND agent_id = '{agent_id}'
        """

        results = self._execute_query(query)

        if results:
            row = results[0]
            total = int(row.get("total", 0) or 0)
            errors = int(row.get("errors", 0) or 0)
            return errors / total if total > 0 else 0

        return 0
