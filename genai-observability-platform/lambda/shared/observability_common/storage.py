"""
Storage operations for GenAI Observability.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .clients import get_clients
from .config import get_config
from .models import Event, Error, Investigation, Alert


class StorageManager:
    """
    Manages storage operations across different backends.
    """

    def __init__(self):
        self.config = get_config()
        self.clients = get_clients()

    # =========================================================================
    # DynamoDB Operations
    # =========================================================================

    def store_error(self, error: Error) -> None:
        """Store an error in DynamoDB."""
        table = self.clients.get_dynamodb_table(self.config.error_store_table)

        # Set TTL
        if error.ttl == 0:
            error.ttl = int(
                datetime.utcnow().timestamp() + (self.config.error_ttl_days * 24 * 60 * 60)
            )

        table.put_item(Item=error.to_dynamodb_item())

    def get_recent_errors(
        self, agent_id: str, hours: int = 1, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent errors for an agent."""
        table = self.clients.get_dynamodb_table(self.config.error_store_table)

        cutoff_time = datetime.utcnow().isoformat()
        # Note: In production, calculate the actual cutoff time

        try:
            response = table.query(
                IndexName="agent-timestamp-index",
                KeyConditionExpression="agent_id = :agent_id",
                ExpressionAttributeValues={":agent_id": agent_id},
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Error fetching recent errors: {e}")
            return []

    def get_errors_in_window(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get all errors in a time window (for anomaly detection)."""
        table = self.clients.get_dynamodb_table(self.config.error_store_table)

        # Calculate cutoff time
        from datetime import timedelta

        cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()

        try:
            response = table.scan(
                FilterExpression="#ts >= :time_threshold",
                ExpressionAttributeNames={"#ts": "timestamp"},
                ExpressionAttributeValues={":time_threshold": cutoff},
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Error scanning errors: {e}")
            return []

    def store_investigation(self, investigation: Investigation) -> None:
        """Store an investigation result."""
        table = self.clients.get_dynamodb_table(self.config.investigation_results_table)

        if investigation.ttl == 0:
            investigation.ttl = int(
                datetime.utcnow().timestamp()
                + (self.config.investigation_ttl_days * 24 * 60 * 60)
            )

        table.put_item(Item=investigation.to_dynamodb_item())

    def get_similar_investigations(
        self, agent_id: str, anomaly_type: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar past investigations."""
        table = self.clients.get_dynamodb_table(self.config.investigation_results_table)

        try:
            response = table.query(
                IndexName="agent-timestamp-index",
                KeyConditionExpression="agent_id = :agent_id",
                FilterExpression="anomaly_type = :anomaly_type AND resolution_status = :resolved",
                ExpressionAttributeValues={
                    ":agent_id": agent_id,
                    ":anomaly_type": anomaly_type,
                    ":resolved": "resolved",
                },
                Limit=limit,
                ScanIndexForward=False,
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Error finding similar investigations: {e}")
            return []

    def check_alert_cache(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Check if an alert fingerprint exists in cache."""
        table = self.clients.get_dynamodb_table(self.config.alert_cache_table)

        try:
            response = table.get_item(Key={"alert_fingerprint": fingerprint})
            return response.get("Item")
        except Exception as e:
            print(f"Error checking alert cache: {e}")
            return None

    def cache_alert(self, fingerprint: str, alert_data: Dict[str, Any]) -> None:
        """Cache an alert fingerprint."""
        table = self.clients.get_dynamodb_table(self.config.alert_cache_table)

        table.put_item(
            Item={
                "alert_fingerprint": fingerprint,
                "last_sent": datetime.utcnow().isoformat(),
                "alert_data": json.dumps(alert_data),
                "count": 1,
                "ttl": int(
                    datetime.utcnow().timestamp()
                    + (self.config.alert_cache_ttl_days * 24 * 60 * 60)
                ),
            }
        )

    def increment_alert_count(self, fingerprint: str) -> None:
        """Increment the count for a cached alert."""
        table = self.clients.get_dynamodb_table(self.config.alert_cache_table)

        table.update_item(
            Key={"alert_fingerprint": fingerprint},
            UpdateExpression="SET #count = #count + :inc",
            ExpressionAttributeNames={"#count": "count"},
            ExpressionAttributeValues={":inc": 1},
        )

    def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent metadata."""
        table = self.clients.get_dynamodb_table(self.config.agent_metadata_table)

        try:
            response = table.get_item(Key={"agent_id": agent_id})
            return response.get("Item")
        except Exception as e:
            print(f"Error getting agent metadata: {e}")
            return None

    # =========================================================================
    # OpenSearch Operations
    # =========================================================================

    def index_event(self, event: Event) -> None:
        """Index an event in OpenSearch."""
        opensearch = self.clients.opensearch
        if opensearch is None:
            print("OpenSearch client not configured")
            return

        # Use monthly indices
        index_name = f"traces-{datetime.utcnow().strftime('%Y-%m')}"

        try:
            opensearch.index(index=index_name, body=event.to_dict())
        except Exception as e:
            print(f"Error indexing to OpenSearch: {e}")

    def search_traces(
        self, agent_id: str, execution_id: Optional[str] = None, hours: int = 1
    ) -> List[Dict[str, Any]]:
        """Search for traces in OpenSearch."""
        opensearch = self.clients.opensearch
        if opensearch is None:
            return []

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"agent_id": agent_id}},
                        {"range": {"timestamp": {"gte": f"now-{hours}h", "lte": "now"}}},
                    ]
                }
            },
            "sort": [{"timestamp": "asc"}],
            "size": 100,
        }

        if execution_id:
            query["query"]["bool"]["must"].append({"term": {"execution_id": execution_id}})

        try:
            response = opensearch.search(index="traces-*", body=query)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            print(f"Error searching OpenSearch: {e}")
            return []

    # =========================================================================
    # Timestream Operations
    # =========================================================================

    def write_metrics(self, event: Event) -> None:
        """Write metrics from an event to Timestream."""
        if not event.is_end_event():
            return

        records = []
        current_time = str(int(datetime.utcnow().timestamp() * 1000))

        common_dimensions = [
            {"Name": "agent_id", "Value": event.agent_id},
            {"Name": "agent_type", "Value": event.agent_type or "unknown"},
            {"Name": "environment", "Value": event.environment or "unknown"},
        ]

        # Duration metric
        if event.duration_ms is not None:
            records.append(
                {
                    "Dimensions": common_dimensions
                    + [{"Name": "event_type", "Value": event.event_type}],
                    "MeasureName": "duration_ms",
                    "MeasureValue": str(event.duration_ms),
                    "MeasureValueType": "DOUBLE",
                    "Time": current_time,
                }
            )

        # Token metrics
        if event.token_usage:
            model_dimensions = common_dimensions + [
                {"Name": "model", "Value": event.model or "unknown"},
                {"Name": "provider", "Value": event.provider or "unknown"},
            ]

            if event.token_usage.get("input_tokens"):
                records.append(
                    {
                        "Dimensions": model_dimensions,
                        "MeasureName": "input_tokens",
                        "MeasureValue": str(event.token_usage["input_tokens"]),
                        "MeasureValueType": "BIGINT",
                        "Time": current_time,
                    }
                )

            if event.token_usage.get("output_tokens"):
                records.append(
                    {
                        "Dimensions": model_dimensions,
                        "MeasureName": "output_tokens",
                        "MeasureValue": str(event.token_usage["output_tokens"]),
                        "MeasureValueType": "BIGINT",
                        "Time": current_time,
                    }
                )

        # Cost metric
        if event.cost and event.cost > 0:
            records.append(
                {
                    "Dimensions": common_dimensions,
                    "MeasureName": "cost_usd",
                    "MeasureValue": str(event.cost),
                    "MeasureValueType": "DOUBLE",
                    "Time": current_time,
                }
            )

        # Write to Timestream
        if records:
            try:
                self.clients.timestream_write.write_records(
                    DatabaseName=self.config.timestream_database,
                    TableName=self.config.timestream_latency_table,
                    Records=records,
                )
            except Exception as e:
                print(f"Error writing to Timestream: {e}")

    def query_latency_anomalies(self, threshold_ms: float) -> List[Dict[str, Any]]:
        """Query for latency anomalies."""
        query = f"""
        SELECT agent_id, AVG(measure_value::double) as avg_latency, MAX(measure_value::double) as max_latency
        FROM "{self.config.timestream_database}"."{self.config.timestream_latency_table}"
        WHERE measure_name = 'duration_ms'
            AND time >= ago(5m)
        GROUP BY agent_id
        HAVING AVG(measure_value::double) > {threshold_ms}
        """

        try:
            response = self.clients.timestream_query.query(QueryString=query)
            results = []
            for row in response.get("Rows", []):
                results.append(
                    {
                        "agent_id": row["Data"][0].get("ScalarValue", "unknown"),
                        "avg_latency": float(row["Data"][1].get("ScalarValue", 0)),
                        "max_latency": float(row["Data"][2].get("ScalarValue", 0)),
                    }
                )
            return results
        except Exception as e:
            print(f"Error querying Timestream: {e}")
            return []

    def get_agent_metrics(self, agent_id: str, hours: int = 1) -> Dict[str, float]:
        """Get recent metrics for an agent."""
        query = f"""
        SELECT measure_name, AVG(measure_value::double) as avg_value
        FROM "{self.config.timestream_database}"."{self.config.timestream_latency_table}"
        WHERE agent_id = '{agent_id}'
            AND time >= ago({hours}h)
        GROUP BY measure_name
        """

        try:
            response = self.clients.timestream_query.query(QueryString=query)
            metrics = {}
            for row in response.get("Rows", []):
                measure = row["Data"][0].get("ScalarValue", "unknown")
                value = float(row["Data"][1].get("ScalarValue", 0))
                metrics[measure] = value
            return metrics
        except Exception as e:
            print(f"Error querying agent metrics: {e}")
            return {}

    # =========================================================================
    # S3 Operations
    # =========================================================================

    def store_raw_events(self, agent_id: str, events: List[Dict[str, Any]]) -> str:
        """Store raw events to S3."""
        import uuid

        date_prefix = datetime.utcnow().strftime("%Y/%m/%d/%H")
        s3_key = f"events/{agent_id}/{date_prefix}/{uuid.uuid4()}.json"

        self.clients.s3.put_object(
            Bucket=self.config.raw_data_bucket,
            Key=s3_key,
            Body=json.dumps(
                {
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "events": events,
                }
            ),
            ContentType="application/json",
        )

        return s3_key
