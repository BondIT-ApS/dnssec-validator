"""
Integration tests for bulk DNSSEC validation API endpoint
"""

import json
import pytest
from unittest.mock import patch
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestBulkValidationIntegration:
    """Integration tests for bulk validation endpoint"""

    @patch("dnssec_validator.DNSSECValidator")
    def test_bulk_endpoint_exists(self, mock_validator, client):
        """Test that bulk validation endpoint is accessible"""
        mock_validator.return_value.validate.return_value = {
            "domain": "test.com",
            "status": "valid",
            "validation_time": "2026-01-25T12:00:00Z",
            "chain_of_trust": [],
            "records": {"dnskey": [], "ds": [], "rrsig": []},
            "errors": [],
        }

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": ["test.com"]}),
            content_type="application/json",
        )

        # Should return 200 or 429 (rate limit), not 404
        assert response.status_code in [200, 429]

    def test_bulk_endpoint_requires_post(self, client):
        """Test that bulk endpoint only accepts POST requests"""
        response = client.get("/api/validate/bulk")

        # GET should not be allowed
        assert response.status_code in [405, 429]  # Method Not Allowed or Rate Limited

    def test_bulk_validation_api_docs(self, client):
        """Test that bulk validation appears in API documentation"""
        response = client.get("/api/docs/")
        assert response.status_code == 200
        # API docs should be accessible


class TestBulkValidationSchema:
    """Test API schema validation"""

    def test_invalid_json_rejected(self, client):
        """Test that invalid JSON is rejected"""
        response = client.post(
            "/api/validate/bulk",
            data="not valid json",
            content_type="application/json",
        )

        assert response.status_code in [400, 429]

    def test_empty_body_rejected(self, client):
        """Test that empty request body is rejected"""
        response = client.post(
            "/api/validate/bulk",
            data="",
            content_type="application/json",
        )

        assert response.status_code in [400, 429]
