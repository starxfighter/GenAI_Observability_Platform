"""
Glue ETL Job: Tool Analytics
Aggregates tool usage data to identify patterns and performance metrics.
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

print(f"Processing tool analytics for date: {process_date}")

# Read raw event data from S3
s3_path = f"s3://{args['S3_BUCKET']}/raw/events/{process_date}/"

try:
    raw_df = spark.read.json(s3_path)

    # Filter to tool events
    tool_events = raw_df.filter(
        (F.col("event_type") == "tool_start") |
        (F.col("event_type") == "tool_end")
    )

    # Aggregate tool usage by agent and tool name
    tool_usage = tool_events.filter(F.col("event_type") == "tool_end").groupBy(
        F.col("agent_id"),
        F.col("attributes.tool_name").alias("tool_name"),
        F.date_trunc("hour", F.col("timestamp")).alias("hour")
    ).agg(
        F.count("*").alias("invocation_count"),
        F.sum(F.when(F.col("attributes.status") == "success", 1).otherwise(0)).alias("success_count"),
        F.sum(F.when(F.col("attributes.status") == "error", 1).otherwise(0)).alias("error_count"),
        F.avg(F.col("attributes.duration_ms")).alias("avg_duration_ms"),
        F.max(F.col("attributes.duration_ms")).alias("max_duration_ms"),
        F.min(F.col("attributes.duration_ms")).alias("min_duration_ms"),
        F.stddev(F.col("attributes.duration_ms")).alias("stddev_duration_ms")
    )

    # Calculate success rate
    tool_usage = tool_usage.withColumn(
        "success_rate",
        F.col("success_count") / F.col("invocation_count")
    ).withColumn(
        "created_at", F.current_timestamp()
    ).withColumn(
        "process_date", F.lit(process_date)
    )

    # Write hourly tool usage to RDS
    tool_usage.write.jdbc(
        url=jdbc_url,
        table="tool_usage_hourly",
        mode="append",
        properties=jdbc_properties
    )

    # Create tool performance summary
    tool_performance = tool_events.filter(F.col("event_type") == "tool_end").groupBy(
        F.col("agent_id"),
        F.col("attributes.tool_name").alias("tool_name")
    ).agg(
        F.count("*").alias("total_invocations"),
        F.sum(F.when(F.col("attributes.status") == "success", 1).otherwise(0)).alias("total_successes"),
        F.sum(F.when(F.col("attributes.status") == "error", 1).otherwise(0)).alias("total_errors"),
        F.avg(F.col("attributes.duration_ms")).alias("avg_duration_ms"),
        F.percentile_approx(F.col("attributes.duration_ms"), 0.50).alias("p50_duration_ms"),
        F.percentile_approx(F.col("attributes.duration_ms"), 0.95).alias("p95_duration_ms"),
        F.percentile_approx(F.col("attributes.duration_ms"), 0.99).alias("p99_duration_ms")
    ).withColumn(
        "success_rate",
        F.col("total_successes") / F.col("total_invocations")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    tool_performance.write.jdbc(
        url=jdbc_url,
        table="tool_performance_daily",
        mode="append",
        properties=jdbc_properties
    )

    # Identify tool execution patterns (sequences)
    window_spec = Window.partitionBy("trace_id").orderBy("timestamp")

    tool_sequences = tool_events.filter(F.col("event_type") == "tool_start").withColumn(
        "sequence_position", F.row_number().over(window_spec)
    ).withColumn(
        "prev_tool", F.lag("attributes.tool_name").over(window_spec)
    ).filter(
        F.col("prev_tool").isNotNull()
    ).groupBy(
        F.col("agent_id"),
        F.col("prev_tool").alias("from_tool"),
        F.col("attributes.tool_name").alias("to_tool")
    ).agg(
        F.count("*").alias("transition_count")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    tool_sequences.write.jdbc(
        url=jdbc_url,
        table="tool_transitions",
        mode="append",
        properties=jdbc_properties
    )

    print(f"Successfully processed tool analytics for {process_date}")
    print(f"Hourly records: {tool_usage.count()}")
    print(f"Performance records: {tool_performance.count()}")
    print(f"Transition records: {tool_sequences.count()}")

except Exception as e:
    print(f"Error processing tool analytics: {str(e)}")
    raise

job.commit()
