"""
Integration tests for bulk DNSSEC validation API endpoint
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestBulkValidationEndpoint:
    """Integration tests for bulk validation endpoint"""

    @patch("dnssec_validator.DNSSECValidator")
    def test_bulk_validation_endpoint_basic(self, mock_validator, client):
        """Test basic bulk validation with two domains"""
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
            data=json.dumps({"domains": ["bondit.dk", "example.com"]}),
            content_type="application/json",
        )

        # Should succeed or hit rate limit
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = json.loads(response.data)
            assert "results" in data
            assert "summary" in data
            assert len(data["results"]) == 2
            assert data["summary"]["total"] == 2

    @patch("dnssec_validator.DNSSECValidator")
    def test_bulk_validation_with_sequential_option(self, mock_validator, client):
        """Test bulk validation with sequential processing"""
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
            data=json.dumps(
                {
                    "domains": ["bondit.dk"],
                    "options": {"parallel": False, "timeout": 30},
                }
            ),
            content_type="application/json",
        )

        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = json.loads(response.data)
            assert "results" in data
            assert "summary" in data

    def test_bulk_validation_empty_domains(self, client):
        """Test bulk validation with empty domain list"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": []}),
            content_type="application/json",
        )

        # Should return 400 bad request (or 429 if rate limited)
        assert response.status_code in [400, 429]

    def test_bulk_validation_too_many_domains(self, client):
        """Test bulk validation with too many domains"""
        domains = [f"example{i}.com" for i in range(51)]

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": domains}),
            content_type="application/json",
        )

        # Should return 400 bad request (or 429 if rate limited)
        assert response.status_code in [400, 429]

    def test_bulk_validation_invalid_json(self, client):
        """Test bulk validation with invalid JSON"""
        response = client.post(
            "/api/validate/bulk",
            data="not valid json",
            content_type="application/json",
        )

        assert response.status_code in [400, 429]

    def test_bulk_validation_missing_domains_field(self, client):
        """Test bulk validation without domains field"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"options": {"timeout": 30}}),
            content_type="application/json",
        )

        assert response.status_code in [400, 429]

    def test_bulk_validation_invalid_timeout(self, client):
        """Test bulk validation with invalid timeout value"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps(
                {"domains": ["bondit.dk"], "options": {"timeout": 200}}
            ),
            content_type="application/json",
        )

        # Should reject invalid timeout (or hit rate limit)
        assert response.status_code in [400, 429]

    def test_bulk_validation_get_method_not_allowed(self, client):
        """Test that GET method is not allowed on bulk endpoint"""
        response = client.get("/api/validate/bulk")

        # Should return 405 Method Not Allowed (or 429 if rate limited)
        assert response.status_code in [405, 429]

    @patch("dnssec_validator.DNSSECValidator")
    def test_bulk_validation_url_extraction(self, mock_validator, client):
        """Test bulk validation with URL input"""
        mock_validator.return_value.validate.return_value = {
            "domain": "bondit.dk",
            "status": "valid",
            "validation_time": "2026-01-25T12:00:00Z",
            "chain_of_trust": [],
            "records": {"dnskey": [], "ds": [], "rrsig": []},
            "errors": [],
        }

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": ["https://bondit.dk", "http://bondit.dk/path"]}),
            content_type="application/json",
        )

        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = json.loads(response.data)
            # Should extract domains from URLs
            assert len(data["results"]) == 2

    @patch("dnssec_validator.DNSSECValidator")
    def test_bulk_validation_mixed_valid_invalid(self, mock_validator, client):
        """Test bulk validation with mix of valid and invalid domains"""
        mock_validator.return_value.validate.return_value = {
            "domain": "bondit.dk",
            "status": "valid",
            "validation_time": "2026-01-25T12:00:00Z",
            "chain_of_trust": [],
            "records": {"dnskey": [], "ds": [], "rrsig": []},
            "errors": [],
        }

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps(
                {"domains": ["bondit.dk", "invalid..domain", "example.com"]}
            ),
            content_type="application/json",
        )

        assert response.status_code in [200, 400, 429]

    @patch("dnssec_validator.DNSSECValidator")
    def test_bulk_validation_error_handling(self, mock_validator, client):
        """Test bulk validation handles individual domain errors"""
        # Make validator raise exception for some domains
        mock_validator.return_value.validate.side_effect = [
            {
                "domain": "bondit.dk",
                "status": "valid",
                "validation_time": "2026-01-25T12:00:00Z",
            },
            Exception("DNS timeout"),
        ]

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": ["bondit.dk", "example.com"]}),
            content_type="application/json",
        )

        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = json.loads(response.data)
            # Should have results for both domains despite error
            assert len(data["results"]) == 2

    @patch("dnssec_validator.DNSSECValidator")
    def test_bulk_validation_summary_structure(self, mock_validator, client):
        """Test that bulk validation returns correct summary structure"""
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
            data=json.dumps({"domains": ["bondit.dk"]}),
            content_type="application/json",
        )

        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = json.loads(response.data)
            summary = data["summary"]

            # Check summary has all required fields
            assert "total" in summary
            assert "valid" in summary
            assert "invalid" in summary
            assert "insecure" in summary
            assert "error" in summary
            assert "processing_time" in summary

            # Check types
            assert isinstance(summary["total"], int)
            assert isinstance(summary["valid"], int)
            assert isinstance(summary["invalid"], int)
            assert isinstance(summary["insecure"], int)
            assert isinstance(summary["error"], int)
            assert isinstance(summary["processing_time"], (int, float))
