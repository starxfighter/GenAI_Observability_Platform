"""
Glue ETL Job: Token Aggregation
Aggregates token usage data from S3 cold storage into RDS for analytics.
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

# Get RDS credentials from Secrets Manager
secrets_client = boto3.client('secretsmanager')
secret_response = secrets_client.get_secret_value(SecretId=args['RDS_SECRET_ARN'])
rds_credentials = json.loads(secret_response['SecretString'])

# JDBC connection properties
jdbc_url = f"jdbc:postgresql://{args['RDS_ENDPOINT']}:5432/observability"
jdbc_properties = {
    "user": rds_credentials['username'],
    "password": rds_credentials['password'],
    "driver": "org.postgresql.Driver"
}

# Calculate date range (previous day)
execution_date = datetime.fromisoformat(args['EXECUTION_DATE'].replace('Z', '+00:00'))
process_date = (execution_date - timedelta(days=1)).strftime('%Y/%m/%d')

print(f"Processing token data for date: {process_date}")

# Read raw event data from S3
s3_path = f"s3://{args['S3_BUCKET']}/raw/events/{process_date}/"

try:
    raw_df = spark.read.json(s3_path)

    # Filter to LLM events only
    llm_events = raw_df.filter(
        (F.col("event_type") == "llm_start") |
        (F.col("event_type") == "llm_end")
    )

    # Aggregate token usage by agent, model, and hour
    token_aggregation = llm_events.groupBy(
        F.col("agent_id"),
        F.col("attributes.model").alias("model"),
        F.date_trunc("hour", F.col("timestamp")).alias("hour")
    ).agg(
        F.sum(F.col("attributes.token_usage.prompt_tokens")).alias("total_prompt_tokens"),
        F.sum(F.col("attributes.token_usage.completion_tokens")).alias("total_completion_tokens"),
        F.sum(F.col("attributes.token_usage.total_tokens")).alias("total_tokens"),
        F.count("*").alias("request_count"),
        F.avg(F.col("attributes.duration_ms")).alias("avg_latency_ms"),
        F.max(F.col("attributes.duration_ms")).alias("max_latency_ms"),
        F.min(F.col("attributes.duration_ms")).alias("min_latency_ms")
    )

    # Calculate costs based on model pricing
    # Pricing per 1M tokens (approximate)
    pricing = {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }

    # Add cost calculation UDF
    @F.udf(returnType=FloatType())
    def calculate_cost(model, prompt_tokens, completion_tokens):
        if model in pricing:
            input_cost = (prompt_tokens / 1_000_000) * pricing[model]["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing[model]["output"]
            return float(input_cost + output_cost)
        return 0.0

    # Add estimated cost column
    token_aggregation = token_aggregation.withColumn(
        "estimated_cost_usd",
        calculate_cost(
            F.col("model"),
            F.col("total_prompt_tokens"),
            F.col("total_completion_tokens")
        )
    )

    # Add metadata columns
    token_aggregation = token_aggregation.withColumn(
        "created_at", F.current_timestamp()
    ).withColumn(
        "process_date", F.lit(process_date)
    )

    # Write to RDS
    token_aggregation.write.jdbc(
        url=jdbc_url,
        table="token_usage_hourly",
        mode="append",
        properties=jdbc_properties
    )

    # Also create daily summary
    daily_summary = token_aggregation.groupBy(
        F.col("agent_id"),
        F.col("model")
    ).agg(
        F.sum("total_prompt_tokens").alias("total_prompt_tokens"),
        F.sum("total_completion_tokens").alias("total_completion_tokens"),
        F.sum("total_tokens").alias("total_tokens"),
        F.sum("request_count").alias("total_requests"),
        F.sum("estimated_cost_usd").alias("total_cost_usd"),
        F.avg("avg_latency_ms").alias("avg_latency_ms")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    daily_summary.write.jdbc(
        url=jdbc_url,
        table="token_usage_daily",
        mode="append",
        properties=jdbc_properties
    )

    print(f"Successfully processed {token_aggregation.count()} hourly records")
    print(f"Successfully processed {daily_summary.count()} daily records")

except Exception as e:
    print(f"Error processing token data: {str(e)}")
    raise

job.commit()
