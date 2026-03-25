"""Tests for natural language query endpoints."""

import pytest


class TestNLQueryEndpoints:
    """Tests for natural language query endpoints."""

    def test_execute_query(self, client):
        """Test executing a natural language query."""
        response = client.post(
            "/api/v1/nlq",
            json={
                "query": "Show me all errors from the last hour",
                "context": {}
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "query" in data
        assert "parsed_intent" in data
        assert "results" in data
        assert "response" in data
        assert "suggestions" in data

    def test_execute_query_with_context(self, client):
        """Test executing a query with context."""
        response = client.post(
            "/api/v1/nlq",
            json={
                "query": "What is the error rate?",
                "context": {"agent_id": "test-agent"}
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "What is the error rate?"

    def test_execute_empty_query_fails(self, client):
        """Test executing an empty query fails."""
        response = client.post(
            "/api/v1/nlq",
            json={"query": "", "context": {}}
        )
        # Should return 422 for validation error or 400 for bad request
        assert response.status_code in [400, 422]

    def test_get_suggestions(self, client):
        """Test getting query suggestions."""
        response = client.get("/api/v1/nlq/suggestions")
        assert response.status_code == 200

        data = response.json()
        assert "general" in data
        assert "contextual" in data
        assert isinstance(data["general"], list)
        assert isinstance(data["contextual"], list)

    def test_get_suggestions_with_context(self, client):
        """Test getting contextual suggestions."""
        response = client.get("/api/v1/nlq/suggestions?context=agent_view")
        assert response.status_code == 200

        data = response.json()
        assert "contextual" in data

    def test_get_query_history(self, client):
        """Test getting query history."""
        response = client.get("/api/v1/nlq/history")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_query_history_with_limit(self, client):
        """Test getting limited query history."""
        response = client.get("/api/v1/nlq/history?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data) <= 5

    def test_save_query(self, client):
        """Test saving a query."""
        response = client.post(
            "/api/v1/nlq/saved",
            json={
                "name": "Daily Error Check",
                "query": "Show errors from the last 24 hours",
                "description": "Check for daily errors",
                "tags": ["daily", "errors"]
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "query_id" in data
        assert data["name"] == "Daily Error Check"
        assert data["query"] == "Show errors from the last 24 hours"
        assert "created_at" in data

    def test_get_saved_queries(self, client):
        """Test getting saved queries."""
        response = client.get("/api/v1/nlq/saved")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_delete_saved_query(self, client):
        """Test deleting a saved query."""
        # First create a query
        create_response = client.post(
            "/api/v1/nlq/saved",
            json={
                "name": "To Delete",
                "query": "test query"
            }
        )
        query_id = create_response.json()["query_id"]

        # Then delete it
        response = client.delete(f"/api/v1/nlq/saved/{query_id}")
        assert response.status_code == 200

    def test_get_query_examples(self, client):
        """Test getting query examples."""
        response = client.get("/api/v1/nlq/examples")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)

        # Should have categories
        for category, examples in data.items():
            assert isinstance(examples, list)
            for example in examples:
                assert "query" in example
                assert "description" in example


class TestNLQueryParsing:
    """Tests for NL query parsing functionality."""

    def test_parse_time_range_query(self, client):
        """Test parsing a query with time range."""
        response = client.post(
            "/api/v1/nlq",
            json={"query": "Show errors from the last 24 hours"}
        )
        assert response.status_code == 200

        data = response.json()
        parsed = data.get("parsed_intent", {})
        # Check that time range was extracted
        assert "entities" in parsed or "time_range" in data.get("results", {}).get("metadata", {})

    def test_parse_agent_specific_query(self, client):
        """Test parsing a query about specific agent."""
        response = client.post(
            "/api/v1/nlq",
            json={"query": "What is the latency for the billing agent?"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "parsed_intent" in data

    def test_parse_aggregation_query(self, client):
        """Test parsing a query with aggregations."""
        response = client.post(
            "/api/v1/nlq",
            json={"query": "Show average response time by agent"}
        )
        assert response.status_code == 200

        data = response.json()
        parsed = data.get("parsed_intent", {})
        # Should recognize aggregation intent
        assert "aggregations" in parsed or parsed.get("query_type") in ["metrics", "aggregation"]

    def test_parse_comparison_query(self, client):
        """Test parsing a comparison query."""
        response = client.post(
            "/api/v1/nlq",
            json={"query": "Compare error rates between production and staging"}
        )
        assert response.status_code == 200

        data = response.json()
        assert "parsed_intent" in data


class TestNLQuerySuggestions:
    """Tests for NL query suggestions."""

    def test_suggestions_include_common_queries(self, client):
        """Test that suggestions include common queries."""
        response = client.get("/api/v1/nlq/suggestions")
        assert response.status_code == 200

        data = response.json()
        general = data.get("general", [])

        # Should have some general suggestions
        assert len(general) > 0

    def test_follow_up_suggestions_after_query(self, client):
        """Test getting follow-up suggestions after a query."""
        # Execute a query first
        query_response = client.post(
            "/api/v1/nlq",
            json={"query": "Show me all errors"}
        )
        assert query_response.status_code == 200

        # Check that suggestions are included
        data = query_response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
