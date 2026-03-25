"""
Glue ETL Job: Trace Reconstruction
Reconstructs complete traces from individual events and stores in RDS for
historical analysis and LLM investigation.
"""
import sys
from datetime import datetime, timedelta
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
import boto3
import json

# Get job arguments
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'S3_BUCKET',
    'RDS_ENDPOINT',
    'RDS_SECRET_ARN',
    'ENVIRONMENT',
    'EXECUTION_DATE'
])

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Get RDS credentials
secrets_client = boto3.client('secretsmanager')
secret_response = secrets_client.get_secret_value(SecretId=args['RDS_SECRET_ARN'])
rds_credentials = json.loads(secret_response['SecretString'])

jdbc_url = f"jdbc:postgresql://{args['RDS_ENDPOINT']}:5432/observability"
jdbc_properties = {
    "user": rds_credentials['username'],
    "password": rds_credentials['password'],
    "driver": "org.postgresql.Driver"
}

# Calculate date range
execution_date = datetime.fromisoformat(args['EXECUTION_DATE'].replace('Z', '+00:00'))
process_date = (execution_date - timedelta(days=1)).strftime('%Y/%m/%d')

print(f"Processing trace reconstruction for date: {process_date}")

# Read raw event data from S3
s3_path = f"s3://{args['S3_BUCKET']}/raw/events/{process_date}/"

try:
    raw_df = spark.read.json(s3_path)

    # Define window for ordering events within a trace
    trace_window = Window.partitionBy("trace_id").orderBy("timestamp")

    # Add sequence number to events
    events_sequenced = raw_df.withColumn(
        "sequence_number", F.row_number().over(trace_window)
    )

    # Reconstruct traces by aggregating events
    traces = events_sequenced.groupBy("trace_id", "agent_id").agg(
        F.min("timestamp").alias("start_time"),
        F.max("timestamp").alias("end_time"),
        F.count("*").alias("event_count"),

        # Count by event type
        F.sum(F.when(F.col("event_type") == "llm_start", 1).otherwise(0)).alias("llm_call_count"),
        F.sum(F.when(F.col("event_type") == "tool_start", 1).otherwise(0)).alias("tool_call_count"),

        # Aggregate token usage
        F.sum(F.col("attributes.token_usage.prompt_tokens")).alias("total_prompt_tokens"),
        F.sum(F.col("attributes.token_usage.completion_tokens")).alias("total_completion_tokens"),
        F.sum(F.col("attributes.token_usage.total_tokens")).alias("total_tokens"),

        # Collect errors
        F.collect_list(
            F.when(
                F.col("attributes.error").isNotNull(),
                F.struct(
                    F.col("event_type"),
                    F.col("attributes.error.type").alias("error_type"),
                    F.col("attributes.error.message").alias("error_message"),
                    F.col("timestamp")
                )
            )
        ).alias("errors"),

        # Collect models used
        F.collect_set(F.col("attributes.model")).alias("models_used"),

        # Collect tools used
        F.collect_set(F.col("attributes.tool_name")).alias("tools_used"),

        # Get the root span name
        F.first(
            F.when(F.col("parent_span_id").isNull(), F.col("name"))
        ).alias("root_span_name"),

        # Get final status
        F.last(F.col("attributes.status")).alias("final_status"),

        # Collect all events as JSON for full trace reconstruction
        F.collect_list(
            F.struct(
                F.col("event_id"),
                F.col("event_type"),
                F.col("span_id"),
                F.col("parent_span_id"),
                F.col("name"),
                F.col("timestamp"),
                F.col("attributes"),
                F.col("sequence_number")
            )
        ).alias("events_json")
    )

    # Calculate trace duration
    traces = traces.withColumn(
        "duration_ms",
        (F.unix_timestamp(F.col("end_time")) - F.unix_timestamp(F.col("start_time"))) * 1000
    )

    # Determine trace status
    traces = traces.withColumn(
        "status",
        F.when(F.size(F.col("errors")) > 0, "error")
        .when(F.col("final_status") == "success", "success")
        .otherwise("unknown")
    )

    # Calculate error count
    traces = traces.withColumn(
        "error_count",
        F.size(F.col("errors"))
    )

    # Convert arrays to strings for RDS storage
    traces = traces.withColumn(
        "models_used_str",
        F.concat_ws(",", F.col("models_used"))
    ).withColumn(
        "tools_used_str",
        F.concat_ws(",", F.col("tools_used"))
    ).withColumn(
        "errors_json",
        F.to_json(F.col("errors"))
    ).withColumn(
        "full_trace_json",
        F.to_json(F.col("events_json"))
    )

    # Add metadata
    traces = traces.withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    # Select columns for traces_archive table
    traces_output = traces.select(
        "trace_id",
        "agent_id",
        "root_span_name",
        "start_time",
        "end_time",
        "duration_ms",
        "status",
        "event_count",
        "llm_call_count",
        "tool_call_count",
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_tokens",
        "error_count",
        "models_used_str",
        "tools_used_str",
        "errors_json",
        "full_trace_json",
        "date",
        "created_at"
    )

    # Write to RDS
    traces_output.write.jdbc(
        url=jdbc_url,
        table="traces_archive",
        mode="append",
        properties=jdbc_properties
    )

    # Create trace summary statistics
    trace_stats = traces.groupBy("agent_id").agg(
        F.count("*").alias("total_traces"),
        F.sum(F.when(F.col("status") == "success", 1).otherwise(0)).alias("successful_traces"),
        F.sum(F.when(F.col("status") == "error", 1).otherwise(0)).alias("failed_traces"),
        F.avg("duration_ms").alias("avg_duration_ms"),
        F.percentile_approx(F.col("duration_ms"), 0.50).alias("p50_duration_ms"),
        F.percentile_approx(F.col("duration_ms"), 0.95).alias("p95_duration_ms"),
        F.percentile_approx(F.col("duration_ms"), 0.99).alias("p99_duration_ms"),
        F.avg("event_count").alias("avg_events_per_trace"),
        F.avg("llm_call_count").alias("avg_llm_calls_per_trace"),
        F.avg("tool_call_count").alias("avg_tool_calls_per_trace"),
        F.sum("total_tokens").alias("total_tokens")
    ).withColumn(
        "success_rate",
        F.col("successful_traces") / F.col("total_traces")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    trace_stats.write.jdbc(
        url=jdbc_url,
        table="trace_statistics_daily",
        mode="append",
        properties=jdbc_properties
    )

    # Identify slow traces (P95 outliers) for investigation
    p95_threshold = traces.select(
        F.percentile_approx(F.col("duration_ms"), 0.95)
    ).collect()[0][0]

    slow_traces = traces.filter(
        F.col("duration_ms") > p95_threshold
    ).select(
        "trace_id",
        "agent_id",
        "duration_ms",
        "llm_call_count",
        "tool_call_count",
        "error_count",
        F.lit("slow_trace").alias("anomaly_type"),
        F.lit(process_date).alias("date"),
        F.current_timestamp().alias("created_at")
    )

    if slow_traces.count() > 0:
        slow_traces.write.jdbc(
            url=jdbc_url,
            table="trace_anomalies",
            mode="append",
            properties=jdbc_properties
        )

    print(f"Successfully processed trace reconstruction for {process_date}")
    print(f"Total traces archived: {traces_output.count()}")
    print(f"Agent statistics records: {trace_stats.count()}")
    print(f"Slow trace anomalies: {slow_traces.count()}")

except Exception as e:
    print(f"Error processing trace reconstruction: {str(e)}")
    raise

job.commit()
