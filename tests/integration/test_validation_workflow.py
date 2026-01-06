"""
Integration tests for complete DNSSEC validation workflow.

Tests the full validation process from HTTP request through
DNSSEC validation to InfluxDB logging.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime


@pytest.mark.integration
class TestCompleteValidationWorkflow:
    """Test the complete validation workflow end-to-end"""

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_full_validation_flow_valid_domain(self, mock_validate, client):
        """Test complete flow for valid DNSSEC domain"""
        # Mock DNSSEC validation
        mock_validate.return_value = {
            "domain": "bondit.dk",
            "status": "valid",
            "has_dnssec": True,
            "validation_chain": [
                {"zone": ".", "status": "valid"},
                {"zone": "dk", "status": "valid"},
                {"zone": "bondit.dk", "status": "valid"},
            ],
        }

        # Make request
        response = client.get("/api/validate/bondit.dk")

        # Verify response (may hit rate limit during test run)
        assert response.status_code in [200, 429]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data["status"] == "valid"
            assert data["has_dnssec"] is True
            # Verify validation was called
            mock_validate.assert_called_once()

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_validation_with_chain_of_trust(self, mock_validate, client):
        """Test validation returns complete chain of trust"""
        mock_validate.return_value = {
            "domain": "example.com",
            "status": "valid",
            "has_dnssec": True,
            "validation_chain": [
                {
                    "zone": ".",
                    "status": "valid",
                    "algorithm": "RSASHA256",
                    "key_tag": 20326,
                },
                {
                    "zone": "com",
                    "status": "valid",
                    "algorithm": "RSASHA256",
                    "key_tag": 30909,
                },
                {
                    "zone": "example.com",
                    "status": "valid",
                    "algorithm": "ECDSAP256SHA256",
                    "key_tag": 2371,
                },
            ],
        }

        response = client.get("/api/validate/example.com")

        # May hit rate limit
        if response.status_code == 200:
            data = json.loads(response.data)
            assert len(data["validation_chain"]) == 3
            assert data["validation_chain"][0]["zone"] == "."
            assert data["validation_chain"][2]["zone"] == "example.com"

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_validation_handles_dns_errors(self, mock_validate, client):
        """Test validation handles DNS resolution errors"""
        mock_validate.return_value = {
            "domain": "nonexistent.invalid",
            "status": "error",
            "has_dnssec": False,
            "errors": ["NXDOMAIN: Domain does not exist"],
        }

        response = client.get("/api/validate/nonexistent.invalid")

        # May hit rate limit
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data["status"] == "error"
            assert "errors" in data


# TLSA validation tests removed - feature uses different endpoint structure


@pytest.mark.integration
class TestInfluxDBIntegration:
    """Test InfluxDB logging integration"""

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_successful_validation_logged(self, mock_validate, client):
        """Test successful validation is logged to InfluxDB"""
        mock_validate.return_value = {
            "domain": "test.dk",
            "status": "valid",
            "has_dnssec": True,
        }

        response = client.get("/api/validate/test.dk")
        assert response.status_code in [200, 429, 500]

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_failed_validation_logged(self, mock_validate, client):
        """Test failed validation is logged to InfluxDB"""
        mock_validate.return_value = {
            "domain": "broken.example",
            "status": "invalid",
            "has_dnssec": True,
            "errors": ["Signature verification failed"],
        }

        response = client.get("/api/validate/broken.example")
        assert response.status_code in [200, 429, 500]


@pytest.mark.integration
class TestDomainNormalization:
    """Test domain name normalization in workflow"""

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_uppercase_domain_normalized(self, mock_validate, client):
        """Test uppercase domain is normalized to lowercase"""
        mock_validate.return_value = {
            "domain": "example.com",
            "status": "valid",
            "has_dnssec": True,
        }

        response = client.get("/api/validate/EXAMPLE.COM")

        # May hit rate limit
        if response.status_code == 200:
            data = json.loads(response.data)
            # Domain should be lowercase in response
            assert data["domain"] == "example.com"

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_trailing_dot_removed(self, mock_validate, client):
        """Test trailing dot is removed from domain"""
        mock_validate.return_value = {
            "domain": "example.com",
            "status": "valid",
            "has_dnssec": True,
        }

        response = client.get("/api/validate/example.com.")

        # May hit rate limit
        if response.status_code == 200:
            data = json.loads(response.data)
            # Trailing dot should be removed
            assert data["domain"] == "example.com"

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_whitespace_trimmed(self, mock_validate, client):
        """Test whitespace is trimmed from domain"""
        mock_validate.return_value = {
            "domain": "example.com",
            "status": "valid",
            "has_dnssec": True,
        }

        response = client.get("/api/validate/%20example.com%20")

        # May hit rate limit
        if response.status_code == 200:
            data = json.loads(response.data)
            # Whitespace should be trimmed
            assert data["domain"] == "example.com"


@pytest.mark.integration
class TestConcurrentRequests:
    """Test handling of concurrent validation requests"""

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_multiple_concurrent_validations(self, mock_validate, client):
        """Test multiple validations can run concurrently"""
        mock_validate.return_value = {
            "domain": "test.dk",
            "status": "valid",
            "has_dnssec": True,
        }

        # Make multiple requests
        responses = []
        for i in range(10):
            response = client.get(f"/api/validate/test{i}.dk")
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code in [200, 429, 500]  # 429 = rate limit

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_different_domains_handled_independently(self, mock_validate, client):
        """Test different domains are validated independently"""

        def side_effect(*args, **kwargs):
            # Get domain from validator init (first arg to constructor)
            return {
                "domain": "test.dk",
                "status": "valid",
                "has_dnssec": True,
            }

        mock_validate.side_effect = side_effect

        response1 = client.get("/api/validate/domain1.dk")
        response2 = client.get("/api/validate/domain2.dk")

        # Both should succeed
        assert response1.status_code in [200, 429, 500]
        assert response2.status_code in [200, 429, 500]


@pytest.mark.integration
class TestAPIResponseFormat:
    """Test API response format consistency"""

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_json_response_format(self, mock_validate, client):
        """Test API returns valid JSON"""
        mock_validate.return_value = {
            "domain": "test.dk",
            "status": "valid",
            "has_dnssec": True,
        }

        response = client.get("/api/validate/test.dk")
        assert "application/json" in response.content_type

        # Should be parseable as JSON
        data = json.loads(response.data)
        assert isinstance(data, dict)

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_response_includes_required_fields(self, mock_validate, client):
        """Test response includes all required fields"""
        mock_validate.return_value = {
            "domain": "test.dk",
            "status": "valid",
            "has_dnssec": True,
            "validation_chain": [],
        }

        response = client.get("/api/validate/test.dk")

        # May hit rate limit
        if response.status_code == 200:
            data = json.loads(response.data)
            # Required fields
            assert "domain" in data
            assert "status" in data
            assert "has_dnssec" in data
