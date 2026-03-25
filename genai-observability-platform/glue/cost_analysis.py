"""
Glue ETL Job: Cost Analysis
Calculates and aggregates cost data across agents, teams, and projects.
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

print(f"Processing cost analysis for date: {process_date}")

# LLM pricing configuration (per 1M tokens)
MODEL_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
}

# Read raw event data from S3
s3_path = f"s3://{args['S3_BUCKET']}/raw/events/{process_date}/"

try:
    raw_df = spark.read.json(s3_path)

    # Read agent metadata from RDS for team/project mapping
    agents_df = spark.read.jdbc(
        url=jdbc_url,
        table="agents",
        properties=jdbc_properties
    ).select("agent_id", "team_id", "project_id", "cost_center")

    # Filter to LLM completion events with token data
    llm_events = raw_df.filter(
        (F.col("event_type") == "llm_end") &
        (F.col("attributes.token_usage").isNotNull())
    )

    # Join with agent metadata
    llm_with_metadata = llm_events.join(
        agents_df,
        llm_events.agent_id == agents_df.agent_id,
        "left"
    )

    # Calculate costs UDF
    pricing_broadcast = spark.sparkContext.broadcast(MODEL_PRICING)

    @F.udf(returnType=FloatType())
    def calc_cost(model, prompt_tokens, completion_tokens):
        pricing = pricing_broadcast.value
        if model and model in pricing:
            input_cost = (prompt_tokens or 0) / 1_000_000 * pricing[model]["input"]
            output_cost = (completion_tokens or 0) / 1_000_000 * pricing[model]["output"]
            return float(input_cost + output_cost)
        # Default to Claude Sonnet pricing if unknown
        input_cost = (prompt_tokens or 0) / 1_000_000 * 3.0
        output_cost = (completion_tokens or 0) / 1_000_000 * 15.0
        return float(input_cost + output_cost)

    # Add cost column
    llm_with_cost = llm_with_metadata.withColumn(
        "cost_usd",
        calc_cost(
            F.col("attributes.model"),
            F.col("attributes.token_usage.prompt_tokens"),
            F.col("attributes.token_usage.completion_tokens")
        )
    )

    # Aggregate by agent
    agent_costs = llm_with_cost.groupBy(
        llm_events.agent_id,
        "team_id",
        "project_id",
        "cost_center",
        F.col("attributes.model").alias("model")
    ).agg(
        F.sum("cost_usd").alias("total_cost_usd"),
        F.sum(F.col("attributes.token_usage.prompt_tokens")).alias("total_prompt_tokens"),
        F.sum(F.col("attributes.token_usage.completion_tokens")).alias("total_completion_tokens"),
        F.count("*").alias("request_count")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    agent_costs.write.jdbc(
        url=jdbc_url,
        table="cost_by_agent_daily",
        mode="append",
        properties=jdbc_properties
    )

    # Aggregate by team
    team_costs = llm_with_cost.groupBy(
        "team_id"
    ).agg(
        F.sum("cost_usd").alias("total_cost_usd"),
        F.sum(F.col("attributes.token_usage.total_tokens")).alias("total_tokens"),
        F.countDistinct(llm_events.agent_id).alias("active_agents"),
        F.count("*").alias("total_requests")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    team_costs.write.jdbc(
        url=jdbc_url,
        table="cost_by_team_daily",
        mode="append",
        properties=jdbc_properties
    )

    # Aggregate by project
    project_costs = llm_with_cost.groupBy(
        "project_id"
    ).agg(
        F.sum("cost_usd").alias("total_cost_usd"),
        F.sum(F.col("attributes.token_usage.total_tokens")).alias("total_tokens"),
        F.countDistinct(llm_events.agent_id).alias("active_agents"),
        F.count("*").alias("total_requests")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    project_costs.write.jdbc(
        url=jdbc_url,
        table="cost_by_project_daily",
        mode="append",
        properties=jdbc_properties
    )

    # Aggregate by cost center (for chargeback)
    cost_center_costs = llm_with_cost.groupBy(
        "cost_center"
    ).agg(
        F.sum("cost_usd").alias("total_cost_usd"),
        F.sum(F.col("attributes.token_usage.total_tokens")).alias("total_tokens"),
        F.countDistinct(llm_events.agent_id).alias("active_agents"),
        F.countDistinct("team_id").alias("active_teams"),
        F.count("*").alias("total_requests")
    ).withColumn(
        "date", F.lit(process_date)
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    cost_center_costs.write.jdbc(
        url=jdbc_url,
        table="cost_by_cost_center_daily",
        mode="append",
        properties=jdbc_properties
    )

    # Calculate running monthly totals
    month_start = process_date[:7] + "/01"
    monthly_costs = spark.read.jdbc(
        url=jdbc_url,
        table=f"(SELECT cost_center, SUM(total_cost_usd) as mtd_cost FROM cost_by_cost_center_daily WHERE date >= '{month_start}' GROUP BY cost_center) AS monthly",
        properties=jdbc_properties
    )

    # Check for budget alerts
    budgets_df = spark.read.jdbc(
        url=jdbc_url,
        table="cost_budgets",
        properties=jdbc_properties
    )

    budget_alerts = monthly_costs.join(
        budgets_df,
        "cost_center"
    ).filter(
        F.col("mtd_cost") > F.col("monthly_budget") * F.col("alert_threshold")
    ).withColumn(
        "alert_type", F.lit("BUDGET_THRESHOLD")
    ).withColumn(
        "created_at", F.current_timestamp()
    )

    if budget_alerts.count() > 0:
        budget_alerts.write.jdbc(
            url=jdbc_url,
            table="cost_alerts",
            mode="append",
            properties=jdbc_properties
        )

    print(f"Successfully processed cost analysis for {process_date}")
    print(f"Agent cost records: {agent_costs.count()}")
    print(f"Team cost records: {team_costs.count()}")
    print(f"Budget alerts: {budget_alerts.count()}")

except Exception as e:
    print(f"Error processing cost analysis: {str(e)}")
    raise

job.commit()
