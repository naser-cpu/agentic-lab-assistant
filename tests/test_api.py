"""Tests for API endpoints."""

import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, test_client):
        """Health endpoint should return 200."""
        response = test_client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_returns_status(self, test_client):
        """Health endpoint should return status field."""
        response = test_client.get("/health")
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_200(self, test_client):
        """Root endpoint should return 200."""
        response = test_client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_root_returns_api_info(self, test_client):
        """Root endpoint should return API info."""
        response = test_client.get("/")
        data = response.json()
        assert data["name"] == "Agentic Lab Assistant"
        assert "version" in data


class TestRequestsEndpoint:
    """Tests for the requests endpoint."""

    def test_create_request_returns_201(self, test_client, sample_request_data):
        """Creating a request should return 201."""
        response = test_client.post("/requests", json=sample_request_data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_request_returns_id(self, test_client, sample_request_data):
        """Creating a request should return request_id."""
        response = test_client.post("/requests", json=sample_request_data)
        data = response.json()
        assert "request_id" in data
        assert "status" in data
        assert data["status"] == "queued"

    def test_create_request_validation(self, test_client):
        """Creating a request with invalid data should return 422."""
        response = test_client.post("/requests", json={"text": ""})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_request_priority_normal(self, test_client):
        """Creating a request with normal priority should work."""
        response = test_client.post(
            "/requests",
            json={"text": "Test request", "priority": "normal"},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_request_priority_high(self, test_client):
        """Creating a request with high priority should work."""
        response = test_client.post(
            "/requests",
            json={"text": "Test request", "priority": "high"},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_get_request_returns_404_for_unknown(self, test_client):
        """Getting an unknown request should return 404."""
        response = test_client.get("/requests/00000000-0000-0000-0000-000000000000")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_request_returns_status(self, test_client, sample_request_data):
        """Getting a request should return its status."""
        # Create request
        create_response = test_client.post("/requests", json=sample_request_data)
        request_id = create_response.json()["request_id"]

        # Get status
        response = test_client.get(f"/requests/{request_id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["request_id"] == request_id
        assert data["status"] in ["queued", "running", "done", "failed"]


class TestRequestSchemas:
    """Tests for request/response schema validation."""

    def test_priority_enum_values(self, test_client):
        """Priority should only accept valid enum values."""
        # Valid values
        for priority in ["normal", "high"]:
            response = test_client.post(
                "/requests",
                json={"text": "Test", "priority": priority},
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Invalid value
        response = test_client.post(
            "/requests",
            json={"text": "Test", "priority": "invalid"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_text_min_length(self, test_client):
        """Text should have minimum length of 1."""
        response = test_client.post(
            "/requests",
            json={"text": "", "priority": "normal"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
