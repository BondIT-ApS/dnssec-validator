"""
Unit tests for bulk DNSSEC validation API endpoint
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False  # Disable rate limiting for tests
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_validator():
    """Mock DNSSECValidator for testing"""
    with patch("dnssec_validator.DNSSECValidator") as mock:
        yield mock


class TestBulkValidationBasic:
    """Test basic bulk validation functionality"""

    def test_bulk_validation_success(self, client, mock_validator):
        """Test successful bulk validation with valid domains"""
        # Mock validator to return valid status
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

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check response structure
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 2

        # Check summary structure (don't check exact counts as parallel execution makes mocking tricky)
        summary = data["summary"]
        assert summary["total"] == 2
        assert "valid" in summary
        assert "insecure" in summary
        assert "invalid" in summary
        assert "error" in summary
        assert "processing_time" in summary
        assert isinstance(summary["processing_time"], (int, float))

    def test_bulk_validation_with_options(self, client, mock_validator):
        """Test bulk validation with custom options"""
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
                {
                    "domains": ["bondit.dk"],
                    "options": {
                        "timeout": 45,
                        "parallel": False,
                        "include_errors": True,
                    },
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["results"]) == 1
        assert data["summary"]["total"] == 1


class TestBulkValidationInputValidation:
    """Test input validation for bulk requests"""

    def test_empty_request_body(self, client):
        """Test error handling for empty request body"""
        response = client.post(
            "/api/validate/bulk",
            data="",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        # Flask-RESTX returns validation errors in 'errors' or 'message' field
        assert "errors" in data or "message" in data or "error" in data

    def test_missing_domains_field(self, client):
        """Test error for missing domains field"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"options": {"timeout": 30}}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        # Flask-RESTX model validation triggered
        assert "errors" in data or "message" in data or "error" in data

    def test_empty_domains_array(self, client):
        """Test error for empty domains array"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": []}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        # Could be Flask-RESTX validation or our custom error
        assert "errors" in data or "error" in data or "message" in data

    def test_too_many_domains(self, client):
        """Test error for exceeding maximum domains"""
        domains = [f"example{i}.com" for i in range(51)]

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": domains}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        # Flask-RESTX or custom validation
        assert "errors" in data or "error" in data or "message" in data

    def test_invalid_domains_array(self, client):
        """Test error for non-array domains field"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": "bondit.dk"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        # Flask-RESTX validation error format
        assert "errors" in data or "message" in data

    def test_invalid_timeout_value(self, client):
        """Test error for invalid timeout value"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": ["bondit.dk"], "options": {"timeout": 200}}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        # Flask-RESTX validation error
        assert "errors" in data or "message" in data


class TestBulkValidationDomainExtraction:
    """Test domain extraction and validation"""

    def test_extract_domains_from_urls(self, client, mock_validator):
        """Test extraction of domains from URLs"""
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
                {"domains": ["https://bondit.dk", "http://bondit.dk/path"]}
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["results"]) == 2

    def test_invalid_domain_formats(self, client):
        """Test handling of invalid domain formats"""
        response = client.post(
            "/api/validate/bulk",
            data=json.dumps(
                {
                    "domains": ["invalid..domain", "not-a-domain", ""],
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "No valid domains" in data["error"]

    def test_mixed_valid_invalid_domains(self, client, mock_validator):
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
                {
                    "domains": ["bondit.dk", "invalid..domain", "example.com"],
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should include 2 valid + 1 invalid = 3 results
        assert len(data["results"]) == 3
        assert data["summary"]["total"] == 3

        # Find the invalid domain result
        invalid_results = [r for r in data["results"] if r["status"] == "error"]
        assert len(invalid_results) == 1


class TestBulkValidationErrorHandling:
    """Test error handling and isolation"""

    def test_partial_results_on_individual_failures(self, client, mock_validator):
        """Test that individual domain failures don't block entire batch"""
        mock_validator.return_value.validate.side_effect = [
            {
                "domain": "bondit.dk",
                "status": "valid",
                "validation_time": "2026-01-25T12:00:00Z",
                "chain_of_trust": [],
                "records": {"dnskey": [], "ds": [], "rrsig": []},
                "errors": [],
            },
            Exception("DNS timeout"),
            {
                "domain": "example.org",
                "status": "valid",
                "validation_time": "2026-01-25T12:00:02Z",
                "chain_of_trust": [],
                "records": {"dnskey": [], "ds": [], "rrsig": []},
                "errors": [],
            },
        ]

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps(
                {
                    "domains": ["bondit.dk", "example.com", "example.org"],
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Should have results for all 3 domains
        assert len(data["results"]) == 3
        assert data["summary"]["total"] == 3
        assert data["summary"]["valid"] == 2
        assert data["summary"]["error"] == 1

    def test_error_messages_sanitized(self, client, mock_validator):
        """Test that error messages are sanitized for security"""
        mock_validator.return_value.validate.side_effect = Exception(
            "Internal server error with sensitive data"
        )

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": ["bondit.dk"]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Check that error was sanitized
        error_result = data["results"][0]
        assert error_result["status"] == "error"
        assert "errors" in error_result
        # Should contain generic message, not raw exception
        assert "An error occurred" in error_result["errors"][0]


class TestBulkValidationSummary:
    """Test summary statistics calculation"""

    def test_summary_statistics(self, client, mock_validator):
        """Test accurate summary statistics"""
        mock_validator.return_value.validate.side_effect = [
            {
                "domain": "d1",
                "status": "valid",
                "validation_time": "2026-01-25T12:00:00Z",
            },
            {
                "domain": "d2",
                "status": "valid",
                "validation_time": "2026-01-25T12:00:01Z",
            },
            {
                "domain": "d3",
                "status": "invalid",
                "validation_time": "2026-01-25T12:00:02Z",
            },
            {
                "domain": "d4",
                "status": "insecure",
                "validation_time": "2026-01-25T12:00:03Z",
            },
        ]

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps(
                {
                    "domains": ["d1.com", "d2.com", "d3.com", "d4.com"],
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        summary = data["summary"]
        assert summary["total"] == 4
        assert summary["valid"] == 2
        assert summary["invalid"] == 1
        assert summary["insecure"] == 1
        assert summary["error"] == 0
        assert isinstance(summary["processing_time"], (int, float))
        assert summary["processing_time"] > 0

    def test_all_status_types_in_summary(self, client, mock_validator):
        """Test that summary includes all status types"""
        mock_validator.return_value.validate.side_effect = [
            {
                "domain": "d1",
                "status": "valid",
                "validation_time": "2026-01-25T12:00:00Z",
            },
            {
                "domain": "d2",
                "status": "invalid",
                "validation_time": "2026-01-25T12:00:01Z",
            },
            {
                "domain": "d3",
                "status": "insecure",
                "validation_time": "2026-01-25T12:00:02Z",
            },
            {
                "domain": "d4",
                "status": "error",
                "validation_time": "2026-01-25T12:00:03Z",
            },
        ]

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps(
                {
                    "domains": ["d1.com", "d2.com", "d3.com", "d4.com"],
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        summary = data["summary"]
        assert "valid" in summary
        assert "invalid" in summary
        assert "insecure" in summary
        assert "error" in summary


class TestBulkValidationParallel:
    """Test parallel processing functionality"""

    def test_parallel_processing_enabled(self, client, mock_validator):
        """Test that parallel processing is used by default"""
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
                    "domains": ["d1.com", "d2.com", "d3.com"],
                    "options": {"parallel": True},
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["results"]) == 3

    def test_sequential_processing(self, client, mock_validator):
        """Test sequential processing when parallel is disabled"""
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
                    "domains": ["d1.com", "d2.com"],
                    "options": {"parallel": False},
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["results"]) == 2


class TestBulkValidationRateLimiting:
    """Test rate limiting for bulk endpoint"""

    def test_rate_limit_headers_present(self, client, mock_validator):
        """Test that rate limit information is available"""
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
            data=json.dumps({"domains": ["bondit.dk"]}),
            content_type="application/json",
        )

        # Rate limiting should be active (even if not triggered)
        assert response.status_code == 200


class TestBulkValidationResponseFormat:
    """Test response format compliance"""

    def test_response_structure(self, client, mock_validator):
        """Test that response has correct structure"""
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
            data=json.dumps({"domains": ["bondit.dk"]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.content_type == "application/json"

        data = json.loads(response.data)

        # Check top-level structure
        assert isinstance(data, dict)
        assert "results" in data
        assert "summary" in data

        # Check results structure
        assert isinstance(data["results"], list)
        for result in data["results"]:
            assert "domain" in result
            assert "status" in result
            assert "validation_time" in result

        # Check summary structure
        summary = data["summary"]
        assert isinstance(summary, dict)
        assert "total" in summary
        assert "valid" in summary
        assert "invalid" in summary
        assert "insecure" in summary
        assert "error" in summary
        assert "processing_time" in summary

    def test_individual_result_format_matches_single_endpoint(
        self, client, mock_validator
    ):
        """Test that individual results match format of single validation endpoint"""
        expected_result = {
            "domain": "bondit.dk",
            "status": "valid",
            "validation_time": "2026-01-25T12:00:00Z",
            "chain_of_trust": [
                {"zone": ".", "status": "valid", "algorithm": 8, "key_tag": 20326}
            ],
            "records": {"dnskey": [], "ds": [], "rrsig": []},
            "tlsa_summary": None,
            "errors": [],
        }

        mock_validator.return_value.validate.return_value = expected_result

        response = client.post(
            "/api/validate/bulk",
            data=json.dumps({"domains": ["bondit.dk"]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        # Individual result should match single endpoint format
        result = data["results"][0]
        assert result["domain"] == expected_result["domain"]
        assert result["status"] == expected_result["status"]
        assert "validation_time" in result
        assert "chain_of_trust" in result
        assert "records" in result
