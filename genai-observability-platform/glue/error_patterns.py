"""
Glue ETL Job: Error Pattern Aggregation
Analyzes error events to identify patterns and populate the error_patterns table
for LLM investigation queries.
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
import hashlib

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

print(f"Processing error patterns for date: {process_date}")

# Read raw event data from S3
s3_path = f"s3://{args['S3_BUCKET']}/raw/events/{process_date}/"

try:
    raw_df = spark.read.json(s3_path)

    # Filter to error events
    error_events = raw_df.filter(
        (F.col("attributes.status") == "error") |
        (F.col("attributes.error").isNotNull()) |
        (F.col("event_type") == "error")
    )

    # UDF to generate error fingerprint
    @F.udf(returnType=StringType())
    def generate_fingerprint(error_type, error_message, agent_id, event_type):
        # Normalize error message (remove specific values)
        normalized = (error_message or "").lower()
        # Remove UUIDs, numbers, timestamps
        import re
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<uuid>', normalized)
        normalized = re.sub(r'\b\d+\b', '<num>', normalized)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '<date>', normalized)

        fingerprint_input = f"{agent_id}:{event_type}:{error_type}:{normalized}"
        return hashlib.md5(fingerprint_input.encode()).hexdigest()[:16]

    # Add fingerprint and extract error details
    errors_with_fingerprint = error_events.withColumn(
        "error_fingerprint",
        generate_fingerprint(
            F.col("attributes.error.type"),
            F.col("attributes.error.message"),
            F.col("agent_id"),
            F.col("event_type")
        )
    ).withColumn(
        "error_type", F.coalesce(F.col("attributes.error.type"), F.lit("Unknown"))
    ).withColumn(
        "error_message", F.coalesce(F.col("attributes.error.message"), F.lit("No message"))
    )

    # Aggregate errors by fingerprint
    error_aggregation = errors_with_fingerprint.groupBy(
        "error_fingerprint",
        "agent_id",
        "event_type",
        "error_type"
    ).agg(
        F.count("*").alias("occurrence_count"),
        F.first("error_message").alias("sample_error_message"),
        F.min("timestamp").alias("first_seen"),
        F.max("timestamp").alias("last_seen"),
        F.collect_set("trace_id").alias("affected_traces"),
        F.collect_set(F.col("attributes.model")).alias("affected_models")
    )

    # Calculate frequency and impact
    total_events = raw_df.count()

    error_patterns = error_aggregation.withColumn(
        "frequency_percentage",
        (F.col("occurrence_count") / F.lit(total_events)) * 100
    ).withColumn(
        "affected_trace_count",
        F.size(F.col("affected_traces"))
    ).withColumn(
        "affected_models_list",
        F.concat_ws(",", F.col("affected_models"))
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    ).withColumn(
        "resolution_status", F.lit("unresolved")
    )

    # Select columns for RDS
    error_patterns_output = error_patterns.select(
        "error_fingerprint",
        "agent_id",
        "event_type",
        "error_type",
        "sample_error_message",
        "occurrence_count",
        "frequency_percentage",
        "affected_trace_count",
        "affected_models_list",
        "first_seen",
        "last_seen",
        "date",
        "resolution_status",
        "created_at"
    )

    error_patterns_output.write.jdbc(
        url=jdbc_url,
        table="error_patterns_daily",
        mode="append",
        properties=jdbc_properties
    )

    # Update master error patterns table (upsert logic)
    # First read existing patterns
    existing_patterns = spark.read.jdbc(
        url=jdbc_url,
        table="error_patterns",
        properties=jdbc_properties
    )

    # Merge new patterns
    new_patterns = error_patterns_output.join(
        existing_patterns,
        "error_fingerprint",
        "left_anti"
    ).select(
        "error_fingerprint",
        "agent_id",
        "event_type",
        "error_type",
        "sample_error_message",
        "occurrence_count",
        F.col("first_seen").alias("first_occurrence"),
        F.col("last_seen").alias("last_occurrence"),
        "resolution_status",
        F.lit(None).alias("resolution_notes"),
        F.lit(None).alias("resolved_at"),
        "created_at"
    )

    if new_patterns.count() > 0:
        new_patterns.write.jdbc(
            url=jdbc_url,
            table="error_patterns",
            mode="append",
            properties=jdbc_properties
        )

    # Update occurrence counts for existing patterns
    # This is done via a separate update query
    updates = error_patterns_output.join(
        existing_patterns.select("error_fingerprint", F.col("occurrence_count").alias("existing_count")),
        "error_fingerprint",
        "inner"
    ).select(
        "error_fingerprint",
        (F.col("occurrence_count") + F.col("existing_count")).alias("total_count"),
        F.col("last_seen").alias("last_occurrence")
    )

    # Write updates to a staging table for later SQL UPDATE
    if updates.count() > 0:
        updates.write.jdbc(
            url=jdbc_url,
            table="error_patterns_updates_staging",
            mode="overwrite",
            properties=jdbc_properties
        )

    # Create error trend analysis
    error_trends = errors_with_fingerprint.groupBy(
        F.date_trunc("hour", F.col("timestamp")).alias("hour"),
        "error_type"
    ).agg(
        F.count("*").alias("error_count"),
        F.countDistinct("agent_id").alias("affected_agents"),
        F.countDistinct("trace_id").alias("affected_traces")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    error_trends.write.jdbc(
        url=jdbc_url,
        table="error_trends_hourly",
        mode="append",
        properties=jdbc_properties
    )

    print(f"Successfully processed error patterns for {process_date}")
    print(f"Error pattern records: {error_patterns_output.count()}")
    print(f"New patterns: {new_patterns.count()}")
    print(f"Error trend records: {error_trends.count()}")

except Exception as e:
    print(f"Error processing error patterns: {str(e)}")
    raise

job.commit()
