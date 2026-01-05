"""
Unit tests for TLSAValidator class.
Tests TLSA/DANE validation logic with mocked dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))

from tlsa_validator import TLSAValidator


@pytest.mark.unit
class TestTLSAValidatorInit:
    """Test TLSAValidator initialization."""

    def test_init_with_domain(self):
        """Test initialization with domain."""
        validator = TLSAValidator("mail.bondit.dk")
        assert validator.domain == "mail.bondit.dk"
        assert validator.cert_usage_types[0] == "PKIX-TA"
        assert validator.cert_usage_types[3] == "DANE-EE"

    def test_cert_usage_types(self):
        """Test certificate usage type mappings."""
        validator = TLSAValidator("test.dk")
        assert len(validator.cert_usage_types) == 4
        assert validator.cert_usage_types[2] == "DANE-TA"

    def test_selector_types(self):
        """Test selector type mappings."""
        validator = TLSAValidator("test.dk")
        assert len(validator.selector_types) == 2
        assert validator.selector_types[0] == "Cert"
        assert validator.selector_types[1] == "SPKI"

    def test_matching_types(self):
        """Test matching type mappings."""
        validator = TLSAValidator("test.dk")
        assert len(validator.matching_types) == 3
        assert validator.matching_types[1] == "SHA-256"
        assert validator.matching_types[2] == "SHA-512"


@pytest.mark.unit
class TestTLSAQuery:
    """Test TLSA DNS query methods."""

    @patch("dns.resolver.Resolver")
    def test_query_tlsa_records_success(self, mock_resolver_class):
        """Test successful TLSA record query."""
        validator = TLSAValidator("mail.bondit.dk")

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        # Mock TLSA record
        mock_rr = MagicMock()
        mock_rr.usage = 3
        mock_rr.selector = 1
        mock_rr.mtype = 1
        mock_rr.cert = bytes.fromhex("abcd" * 16)

        mock_rrset = MagicMock()
        mock_rrset.ttl = 3600
        mock_rrset.__iter__ = lambda self: iter([mock_rr])

        mock_answer = MagicMock()
        mock_answer.rrset = mock_rrset
        mock_resolver.resolve.return_value = mock_answer

        result = validator._query_tlsa_records(443, "tcp")

        assert len(result) == 1
        assert result[0]["usage"] == 3
        assert result[0]["selector"] == 1
        assert result[0]["mtype"] == 1

    @patch("dns.resolver.Resolver")
    def test_query_tlsa_no_records(self, mock_resolver_class):
        """Test TLSA query when no records exist."""
        import dns.resolver

        validator = TLSAValidator("example.com")

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        result = validator._query_tlsa_records(443, "tcp")

        assert result == []

    @patch("dns.resolver.Resolver")
    def test_query_tlsa_no_answer(self, mock_resolver_class):
        """Test TLSA query when DNS returns no answer."""
        import dns.resolver

        validator = TLSAValidator("example.com")

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        result = validator._query_tlsa_records(443, "tcp")

        assert result == []


@pytest.mark.unit
class TestTLSAValidation:
    """Test TLSA validation methods."""

    @patch.object(TLSAValidator, "_query_tlsa_records")
    def test_validate_tlsa_no_records(self, mock_query):
        """Test validation when no TLSA records found."""
        validator = TLSAValidator("example.com")
        mock_query.return_value = []

        result = validator.validate_tlsa()

        assert result["tlsa_status"] == "no_records"
        assert len(result["warnings"]) > 0

    @patch.object(TLSAValidator, "_get_tls_certificate")
    @patch.object(TLSAValidator, "_query_tlsa_records")
    def test_validate_tlsa_cert_unavailable(self, mock_query, mock_get_cert):
        """Test validation when certificate retrieval fails."""
        validator = TLSAValidator("example.com")

        mock_query.return_value = [
            {
                "name": "_443._tcp.example.com",
                "usage": 3,
                "selector": 1,
                "mtype": 1,
                "cert_assoc_data": "abcd",
                "ttl": 3600,
            }
        ]
        mock_get_cert.side_effect = Exception("Connection failed")

        result = validator.validate_tlsa()

        assert result["tlsa_status"] == "cert_unavailable"
        assert len(result["errors"]) > 0

    @patch.object(TLSAValidator, "_validate_dane_associations")
    @patch.object(TLSAValidator, "_get_tls_certificate")
    @patch.object(TLSAValidator, "_query_tlsa_records")
    def test_validate_tlsa_valid(self, mock_query, mock_get_cert, mock_validate):
        """Test successful TLSA validation."""
        validator = TLSAValidator("mail.bondit.dk")

        mock_query.return_value = [
            {
                "name": "_443._tcp.mail.bondit.dk",
                "usage": 3,
                "selector": 1,
                "mtype": 1,
                "cert_assoc_data": "abcd",
                "ttl": 3600,
            }
        ]
        mock_get_cert.return_value = {"subject": "CN=mail.bondit.dk"}
        mock_validate.return_value = {
            "valid_associations": [{"valid": True}],
            "invalid_associations": [],
            "status": "valid",
        }

        result = validator.validate_tlsa()

        assert result["tlsa_status"] == "valid"

    def test_validate_single_association_selector_0(self):
        """Test single association validation with full certificate."""
        validator = TLSAValidator("test.dk")

        tlsa_record = {
            "usage": 3,
            "selector": 0,  # Full cert
            "mtype": 1,  # SHA-256
            "cert_assoc_data": "test_hash",
        }

        cert_info = {
            "der_data": b"test_cert_data",
            "public_key_info": b"test_key",
        }

        result = validator._validate_single_association(tlsa_record, cert_info)

        assert "computed_hash" in result
        assert result["match_details"]["data_source"] == "full_certificate"

    def test_validate_single_association_selector_1(self):
        """Test single association validation with SPKI."""
        validator = TLSAValidator("test.dk")

        tlsa_record = {
            "usage": 3,
            "selector": 1,  # SPKI
            "mtype": 1,  # SHA-256
            "cert_assoc_data": "test_hash",
        }

        cert_info = {
            "der_data": b"test_cert_data",
            "public_key_info": b"test_key",
        }

        result = validator._validate_single_association(tlsa_record, cert_info)

        assert "computed_hash" in result
        assert result["match_details"]["data_source"] == "public_key_info"

    def test_validate_single_association_unsupported_selector(self):
        """Test validation with unsupported selector."""
        validator = TLSAValidator("test.dk")

        tlsa_record = {
            "usage": 3,
            "selector": 99,  # Unsupported
            "mtype": 1,
            "cert_assoc_data": "test_hash",
        }

        cert_info = {"der_data": b"test", "public_key_info": b"test"}

        result = validator._validate_single_association(tlsa_record, cert_info)

        assert result["valid"] is False
        assert "Unsupported selector" in result["reason"]

    def test_validate_single_association_unsupported_mtype(self):
        """Test validation with unsupported matching type."""
        validator = TLSAValidator("test.dk")

        tlsa_record = {
            "usage": 3,
            "selector": 1,
            "mtype": 99,  # Unsupported
            "cert_assoc_data": "test_hash",
        }

        cert_info = {"der_data": b"test", "public_key_info": b"test"}

        result = validator._validate_single_association(tlsa_record, cert_info)

        assert result["valid"] is False
        assert "Unsupported matching type" in result["reason"]

    def test_validate_dane_associations(self):
        """Test DANE association validation."""
        validator = TLSAValidator("test.dk")

        tlsa_records = [
            {"usage": 3, "selector": 1, "mtype": 1, "cert_assoc_data": "valid_hash"}
        ]

        cert_info = {"der_data": b"test", "public_key_info": b"test"}

        with patch.object(
            validator,
            "_validate_single_association",
            return_value={"valid": True, "reason": "Match"},
        ):
            result = validator._validate_dane_associations(tlsa_records, cert_info)

            assert result["status"] == "valid"
            assert len(result["valid_associations"]) == 1
            assert result["summary"]["success_rate"] == 100.0


@pytest.mark.unit
class TestTLSACertificate:
    """Test TLS certificate retrieval."""

    @patch("socket.create_connection")
    def test_get_tls_certificate_error(self, mock_socket):
        """Test certificate retrieval error handling."""
        validator = TLSAValidator("nonexistent.example")

        mock_socket.side_effect = Exception("Connection refused")

        with pytest.raises(Exception):
            validator._get_tls_certificate(443, 10)
