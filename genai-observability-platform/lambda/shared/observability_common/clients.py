"""
AWS client management for Lambda functions.
"""

import json
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

from .config import get_config


class AWSClients:
    """
    Centralized AWS client management with connection pooling.

    Clients are lazily initialized and cached for reuse across invocations.
    """

    _instance: Optional["AWSClients"] = None

    def __init__(self):
        self._config = get_config()
        self._boto_config = BotoConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )

        # Client cache
        self._kinesis = None
        self._dynamodb = None
        self._dynamodb_resource = None
        self._s3 = None
        self._sns = None
        self._lambda = None
        self._secrets = None
        self._timestream_write = None
        self._timestream_query = None
        self._opensearch = None

    @classmethod
    def get_instance(cls) -> "AWSClients":
        """Get singleton instance of AWSClients."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def kinesis(self):
        """Get Kinesis client."""
        if self._kinesis is None:
            self._kinesis = boto3.client("kinesis", config=self._boto_config)
        return self._kinesis

    @property
    def dynamodb(self):
        """Get DynamoDB client."""
        if self._dynamodb is None:
            self._dynamodb = boto3.client("dynamodb", config=self._boto_config)
        return self._dynamodb

    @property
    def dynamodb_resource(self):
        """Get DynamoDB resource."""
        if self._dynamodb_resource is None:
            self._dynamodb_resource = boto3.resource("dynamodb")
        return self._dynamodb_resource

    @property
    def s3(self):
        """Get S3 client."""
        if self._s3 is None:
            self._s3 = boto3.client("s3", config=self._boto_config)
        return self._s3

    @property
    def sns(self):
        """Get SNS client."""
        if self._sns is None:
            self._sns = boto3.client("sns", config=self._boto_config)
        return self._sns

    @property
    def lambda_client(self):
        """Get Lambda client."""
        if self._lambda is None:
            self._lambda = boto3.client("lambda", config=self._boto_config)
        return self._lambda

    @property
    def secrets(self):
        """Get Secrets Manager client."""
        if self._secrets is None:
            self._secrets = boto3.client("secretsmanager", config=self._boto_config)
        return self._secrets

    @property
    def timestream_write(self):
        """Get Timestream Write client."""
        if self._timestream_write is None:
            self._timestream_write = boto3.client(
                "timestream-write",
                config=BotoConfig(
                    retries={"max_attempts": 3, "mode": "adaptive"},
                    read_timeout=20,
                    max_pool_connections=5000,
                ),
            )
        return self._timestream_write

    @property
    def timestream_query(self):
        """Get Timestream Query client."""
        if self._timestream_query is None:
            self._timestream_query = boto3.client("timestream-query", config=self._boto_config)
        return self._timestream_query

    @property
    def opensearch(self):
        """Get OpenSearch client."""
        if self._opensearch is None:
            from opensearchpy import OpenSearch, RequestsHttpConnection
            from requests_aws4auth import AWS4Auth

            credentials = boto3.Session().get_credentials()
            region = self._config.aws_region

            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                "aoss",
                session_token=credentials.token,
            )

            endpoint = self._config.opensearch_endpoint
            if endpoint:
                host = endpoint.replace("https://", "").replace("http://", "")
                self._opensearch = OpenSearch(
                    hosts=[{"host": host, "port": 443}],
                    http_auth=awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                )
        return self._opensearch

    def get_secret(self, secret_arn: str) -> dict:
        """
        Retrieve a secret from Secrets Manager.

        Args:
            secret_arn: ARN of the secret

        Returns:
            Parsed secret value as dictionary
        """
        response = self.secrets.get_secret_value(SecretId=secret_arn)
        return json.loads(response["SecretString"])

    def get_dynamodb_table(self, table_name: str):
        """Get a DynamoDB table resource."""
        return self.dynamodb_resource.Table(table_name)


def get_clients() -> AWSClients:
    """Get the AWS clients singleton."""
    return AWSClients.get_instance()
