"""Metrics service for dashboard and analytics."""

from ..db import DynamoDBClient, TimestreamClient
from ..models.metrics import DashboardMetrics, MetricDataPoint, MetricsSeries
from .agents import AgentService


class MetricsService:
    """Service for metrics and analytics."""

    def __init__(self) -> None:
        """Initialize metrics service."""
        self._dynamodb = DynamoDBClient()
        self._timestream = TimestreamClient()
        self._agent_service = AgentService()

    async def get_dashboard_metrics(self, period: str = "24h") -> DashboardMetrics:
        """Get dashboard overview metrics."""
        # Get base metrics from Timestream
        ts_metrics = await self._timestream.get_dashboard_metrics(period)

        # Get agent counts
        total_agents, active_agents = await self._agent_service.get_agent_count()

        # Calculate error rate
        total_traces = ts_metrics.get("total_traces", 0)
        total_errors = ts_metrics.get("total_errors", 0)
        error_rate = total_errors / total_traces if total_traces > 0 else 0

        return DashboardMetrics(
            period=period,
            total_agents=total_agents,
            active_agents=active_agents,
            total_traces=total_traces,
            total_errors=total_errors,
            error_rate=error_rate,
            avg_latency_ms=ts_metrics.get("avg_latency_ms", 0),
            p95_latency_ms=ts_metrics.get("p95_latency_ms", 0),
            total_tokens=ts_metrics.get("total_tokens", 0),
            total_cost=ts_metrics.get("total_cost", 0),
            traces_trend=0,  # Would calculate trend from previous period
            errors_trend=0,
            latency_trend=0,
        )

    async def get_latency_series(
        self, period: str = "24h", agent_id: str | None = None
    ) -> MetricsSeries:
        """Get latency time series."""
        data = await self._timestream.get_latency_series(period, agent_id)

        data_points = [
            MetricDataPoint(
                timestamp=row["timestamp"],
                value=float(row.get("value", 0) or 0),
                p95=float(row.get("p95", 0) or 0) if row.get("p95") else None,
            )
            for row in data
        ]

        return MetricsSeries(
            metric_name="latency",
            period=period,
            data=data_points,
        )

    async def get_request_series(
        self, period: str = "24h", agent_id: str | None = None
    ) -> MetricsSeries:
        """Get request count time series."""
        data = await self._timestream.get_request_series(period, agent_id)

        data_points = [
            MetricDataPoint(
                timestamp=row["timestamp"],
                value=float(row.get("value", 0) or 0),
            )
            for row in data
        ]

        return MetricsSeries(
            metric_name="requests",
            period=period,
            data=data_points,
        )

    async def get_error_series(
        self, period: str = "24h", agent_id: str | None = None
    ) -> MetricsSeries:
        """Get error count time series."""
        # Would implement similar to request series but filtering for errors
        return MetricsSeries(
            metric_name="errors",
            period=period,
            data=[],
        )

    async def get_token_usage(
        self, period: str = "24h", agent_id: str | None = None
    ) -> dict:
        """Get token usage breakdown."""
        if agent_id:
            metrics = await self._timestream.get_agent_metrics(agent_id, period)
            return {
                "period": period,
                "total_tokens": metrics.get("total_tokens", 0),
                "input_tokens": metrics.get("input_tokens", 0),
                "output_tokens": metrics.get("output_tokens", 0),
            }

        dashboard = await self._timestream.get_dashboard_metrics(period)
        return {
            "period": period,
            "total_tokens": dashboard.get("total_tokens", 0),
            "input_tokens": 0,  # Would need separate query
            "output_tokens": 0,
        }

    async def get_cost_breakdown(
        self, period: str = "24h", agent_id: str | None = None
    ) -> dict:
        """Get cost breakdown."""
        if agent_id:
            metrics = await self._timestream.get_agent_metrics(agent_id, period)
            return {
                "period": period,
                "total_cost": metrics.get("total_cost", 0),
                "by_model": {},
                "by_agent": {agent_id: metrics.get("total_cost", 0)},
            }

        dashboard = await self._timestream.get_dashboard_metrics(period)
        return {
            "period": period,
            "total_cost": dashboard.get("total_cost", 0),
            "by_model": {},
            "by_agent": {},
        }
