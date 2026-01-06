"""
Unit tests for DNSSECValidator class.
Tests DNSSEC validation logic with mocked DNS responses.
"""

import pytest
import dns.name
import dns.resolver
import dns.dnssec
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

import sys
import os

# Add paths for imports
app_path = os.path.join(os.path.dirname(__file__), "..", "..", "app")
fixtures_path = os.path.join(os.path.dirname(__file__), "..", "fixtures")
sys.path.insert(0, app_path)
sys.path.insert(0, fixtures_path)

from dnssec_validator import DNSSECValidator
from dns_responses import (
    create_mock_dnskey_rrset,
    create_mock_ds_rrset,
    create_mock_rrsig_rrset,
    get_dns_response,
)
from test_domains import VALID_DOMAINS, UNSIGNED_DOMAINS


@pytest.mark.unit
class TestDNSSECValidatorInitialization:
    """Test DNSSECValidator initialization."""

    def test_init_with_valid_domain(self):
        """Test initialization with a valid domain name."""
        validator = DNSSECValidator("bondit.dk")
        assert validator.domain == "bondit.dk"
        assert validator.domain_name == dns.name.from_text("bondit.dk")
        assert validator.results["domain"] == "bondit.dk"
        assert validator.results["status"] == "unknown"
        assert "chain_of_trust" in validator.results
        assert "records" in validator.results

    def test_init_with_subdomain(self):
        """Test initialization with a subdomain."""
        validator = DNSSECValidator("www.bondit.dk")
        assert validator.domain == "www.bondit.dk"
        assert validator.domain_name == dns.name.from_text("www.bondit.dk")

    def test_init_with_fqdn(self):
        """Test initialization with fully qualified domain name (trailing dot)."""
        validator = DNSSECValidator("bondit.dk.")
        assert validator.domain == "bondit.dk."
        # dnspython should handle this correctly
        assert str(validator.domain_name).endswith(".")

    def test_results_structure(self):
        """Test that results structure is properly initialized."""
        validator = DNSSECValidator("bondit.dk")
        assert isinstance(validator.results, dict)
        assert validator.results["domain"] == "bondit.dk"
        assert validator.results["status"] == "unknown"
        assert isinstance(validator.results["chain_of_trust"], list)
        assert isinstance(validator.results["records"], dict)
        assert "dnskey" in validator.results["records"]
        assert "ds" in validator.results["records"]
        assert "rrsig" in validator.results["records"]
        assert isinstance(validator.results["errors"], list)


@pytest.mark.unit
class TestDNSSECValidationBasic:
    """Test basic DNSSEC validation scenarios."""

    @patch("dns.resolver.Resolver")
    def test_validate_valid_domain(self, mock_resolver_class):
        """Test validation of a domain with valid DNSSEC."""
        # Setup mock resolver
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        # Create mock responses
        dnskey_rrset = create_mock_dnskey_rrset("bondit.dk", flags=257, algorithm=13)
        ds_rrset = create_mock_ds_rrset("bondit.dk", key_tag=12345, algorithm=13)

        # Mock the resolve method to return appropriate responses
        def resolve_side_effect(zone, record_type):
            mock_answer = MagicMock()
            if record_type == "DNSKEY":
                mock_answer.rrset = dnskey_rrset
            elif record_type == "DS":
                mock_answer.rrset = ds_rrset
            else:
                raise dns.resolver.NoAnswer()
            return mock_answer

        mock_resolver.resolve.side_effect = resolve_side_effect

        # Mock dns.dnssec.key_id to return consistent key tag
        with patch("dns.dnssec.key_id", return_value=12345):
            # Create validator and validate
            validator = DNSSECValidator("bondit.dk")
            with patch.object(validator, "_add_tlsa_summary"):  # Skip TLSA check
                result = validator.validate()

            # Assertions
            assert result["domain"] == "bondit.dk"
            assert result["status"] == "valid"
            assert len(result["chain_of_trust"]) > 0
            assert result["chain_of_trust"][0]["status"] == "valid"

    @patch("dns.resolver.Resolver")
    def test_validate_unsigned_domain(self, mock_resolver_class):
        """Test validation of a domain without DNSSEC."""
        # Setup mock resolver
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        # Mock resolver to raise exception for DNSKEY query
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        # Create validator and validate
        validator = DNSSECValidator("example.org")
        with patch.object(validator, "_add_tlsa_summary"):
            result = validator.validate()

        # Assertions
        assert result["domain"] == "example.org"
        assert result["status"] == "insecure"
        assert len(result["chain_of_trust"]) > 0
        assert result["chain_of_trust"][0]["status"] == "insecure"
        assert "No DNSKEY records" in result["chain_of_trust"][0]["error"]

    @patch("dns.resolver.Resolver")
    def test_validate_broken_chain(self, mock_resolver_class):
        """Test validation of a domain with broken DNSSEC chain."""
        # Setup mock resolver
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        # Create mock responses - DNSKEY exists but no DS
        dnskey_rrset = create_mock_dnskey_rrset(
            "broken-dnssec.example", flags=257, algorithm=8
        )

        def resolve_side_effect(zone, record_type):
            mock_answer = MagicMock()
            if record_type == "DNSKEY":
                mock_answer.rrset = dnskey_rrset
            elif record_type == "DS":
                # No DS record - breaks the chain
                raise dns.resolver.NoAnswer()
            return mock_answer

        mock_resolver.resolve.side_effect = resolve_side_effect

        # Create validator and validate
        validator = DNSSECValidator("broken-dnssec.example")
        with patch.object(validator, "_add_tlsa_summary"):
            result = validator.validate()

        # Assertions
        assert result["domain"] == "broken-dnssec.example"
        assert result["status"] == "invalid"
        assert len(result["chain_of_trust"]) > 0
        assert result["chain_of_trust"][0]["status"] == "invalid"
        assert "no ds record" in result["chain_of_trust"][0]["error"].lower()

    @patch("dns.resolver.Resolver")
    def test_validate_mismatched_keys(self, mock_resolver_class):
        """Test validation with mismatched DS and DNSKEY key tags."""
        # Setup mock resolver
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        # Create mock responses with mismatched key tags
        dnskey_rrset = create_mock_dnskey_rrset("bogus.example", flags=257, algorithm=8)
        ds_rrset = create_mock_ds_rrset(
            "bogus.example", key_tag=11111, algorithm=8
        )  # Different key tag

        def resolve_side_effect(zone, record_type):
            mock_answer = MagicMock()
            if record_type == "DNSKEY":
                mock_answer.rrset = dnskey_rrset
            elif record_type == "DS":
                mock_answer.rrset = ds_rrset
            return mock_answer

        mock_resolver.resolve.side_effect = resolve_side_effect

        # Mock dns.dnssec.key_id to return different key tag
        with patch("dns.dnssec.key_id", return_value=22222):
            # Create validator and validate
            validator = DNSSECValidator("bogus.example")
            with patch.object(validator, "_add_tlsa_summary"):
                result = validator.validate()

            # Assertions
            assert result["domain"] == "bogus.example"
            assert result["status"] == "invalid"
            assert len(result["chain_of_trust"]) > 0
            assert result["chain_of_trust"][0]["status"] == "invalid"
            assert "do not match" in result["chain_of_trust"][0]["error"].lower()


@pytest.mark.unit
class TestDNSSECValidationWithFallback:
    """Test DNSSEC validation with subdomain fallback logic."""

    @patch("dnssec_validator.get_fallback_domains")
    @patch("dns.resolver.Resolver")
    def test_fallback_to_root_domain(self, mock_resolver_class, mock_get_fallback):
        """Test fallback from subdomain to root domain."""
        # Mock get_fallback_domains to return subdomain and root
        mock_get_fallback.return_value = ["www.bondit.dk", "bondit.dk"]

        # Setup mock resolver
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        # Track which validator instance (domain) is being used
        domain_attempts = []

        def resolve_side_effect(zone, record_type):
            zone_str = str(zone) if hasattr(zone, "__str__") else zone
            domain_attempts.append(zone_str)

            mock_answer = MagicMock()
            if "www" in zone_str:
                # First domain (www.bondit.dk) - fail with no DNSKEY
                raise dns.resolver.NoAnswer()
            else:
                # Second domain (bondit.dk) - return valid DNSSEC
                if record_type == "DNSKEY":
                    mock_answer.rrset = create_mock_dnskey_rrset(
                        "bondit.dk", flags=257, algorithm=13
                    )
                elif record_type == "DS":
                    mock_answer.rrset = create_mock_ds_rrset(
                        "bondit.dk", key_tag=12345, algorithm=13
                    )
                return mock_answer

        mock_resolver.resolve.side_effect = resolve_side_effect

        # Mock dns.dnssec.key_id
        with patch("dns.dnssec.key_id", return_value=12345):
            # Create validator and validate with fallback
            validator = DNSSECValidator("www.bondit.dk")
            with patch.object(validator, "_add_tlsa_summary"):
                result = validator.validate_with_fallback(
                    original_input="www.bondit.dk"
                )

            # Assertions - the fallback logic should have tried www first, then bondit.dk
            assert "fallback_info" in result
            assert result["fallback_info"]["original_input"] == "www.bondit.dk"
            # Check if fallback was used or multiple attempts were made
            assert result["fallback_info"]["total_attempts"] >= 1

    @patch("dnssec_validator.get_fallback_domains")
    @patch("dns.resolver.Resolver")
    def test_no_fallback_for_root_domain(self, mock_resolver_class, mock_get_fallback):
        """Test that root domain doesn't trigger fallback."""
        # Mock get_fallback_domains to return only the domain itself
        mock_get_fallback.return_value = ["bondit.dk"]

        # Setup mock resolver
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        # Mock valid DNSSEC response
        def resolve_side_effect(zone, record_type):
            mock_answer = MagicMock()
            if record_type == "DNSKEY":
                mock_answer.rrset = create_mock_dnskey_rrset(
                    "bondit.dk", flags=257, algorithm=13
                )
            elif record_type == "DS":
                mock_answer.rrset = create_mock_ds_rrset(
                    "bondit.dk", key_tag=12345, algorithm=13
                )
            return mock_answer

        mock_resolver.resolve.side_effect = resolve_side_effect

        with patch("dns.dnssec.key_id", return_value=12345):
            validator = DNSSECValidator("bondit.dk")
            with patch.object(validator, "_add_tlsa_summary"):
                result = validator.validate_with_fallback()

            # Assertions
            assert result["fallback_info"]["fallback_used"] is False
            assert result["fallback_info"]["validated_domain"] == "bondit.dk"


@pytest.mark.unit
class TestDNSSECQueryMethods:
    """Test DNS query methods."""

    @patch("dns.resolver.Resolver")
    def test_query_dnskey_success(self, mock_resolver_class):
        """Test successful DNSKEY query."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        mock_answer = MagicMock()
        mock_answer.rrset = create_mock_dnskey_rrset("bondit.dk")
        mock_resolver.resolve.return_value = mock_answer

        validator = DNSSECValidator("bondit.dk")
        result = validator._query_dnskey(dns.name.from_text("bondit.dk"))

        assert result is not None
        mock_resolver.resolve.assert_called_once_with(
            dns.name.from_text("bondit.dk"), "DNSKEY"
        )

    @patch("dns.resolver.Resolver")
    def test_query_dnskey_no_answer(self, mock_resolver_class):
        """Test DNSKEY query when no answer."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        validator = DNSSECValidator("example.org")
        result = validator._query_dnskey(dns.name.from_text("example.org"))

        assert result is None

    @patch("dns.resolver.Resolver")
    def test_query_ds_success(self, mock_resolver_class):
        """Test successful DS query."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        mock_answer = MagicMock()
        mock_answer.rrset = create_mock_ds_rrset("bondit.dk")
        mock_resolver.resolve.return_value = mock_answer

        validator = DNSSECValidator("bondit.dk")
        result = validator._query_ds(dns.name.from_text("bondit.dk"), None)

        assert result is not None
        mock_resolver.resolve.assert_called_once_with(
            dns.name.from_text("bondit.dk"), "DS"
        )

    @patch("dns.resolver.Resolver")
    def test_query_ds_no_answer(self, mock_resolver_class):
        """Test DS query when no answer."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        validator = DNSSECValidator("broken.example")
        result = validator._query_ds(dns.name.from_text("broken.example"), None)

        assert result is None


@pytest.mark.unit
class TestDNSSECErrorHandling:
    """Test error handling in DNSSEC validation."""

    @patch("dns.resolver.Resolver")
    def test_validation_with_network_error(self, mock_resolver_class):
        """Test validation when DNS query fails with network error."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = Exception("Network error")

        validator = DNSSECValidator("bondit.dk")
        with patch.object(validator, "_add_tlsa_summary"):
            result = validator.validate()

        # Network errors during DNS query result in insecure status
        assert result["status"] in ["error", "insecure"]
        assert len(result["errors"]) > 0 or len(result["chain_of_trust"]) > 0

    @patch("dns.resolver.Resolver")
    def test_validation_with_timeout(self, mock_resolver_class):
        """Test validation when DNS query times out."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.Timeout()

        validator = DNSSECValidator("bondit.dk")
        with patch.object(validator, "_add_tlsa_summary"):
            result = validator.validate()

        assert result["status"] in ["error", "insecure"]

    @patch("dns.resolver.Resolver")
    def test_validation_with_nxdomain(self, mock_resolver_class):
        """Test validation when domain doesn't exist."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        validator = DNSSECValidator("nonexistent.example")
        with patch.object(validator, "_add_tlsa_summary"):
            result = validator.validate()

        assert result["status"] in ["error", "insecure"]


@pytest.mark.unit
class TestDNSSECRecordStorage:
    """Test that DNSSEC records are properly stored in results."""

    @patch("dns.resolver.Resolver")
    def test_dnskey_records_stored(self, mock_resolver_class):
        """Test that DNSKEY records are stored in results."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        dnskey_rrset = create_mock_dnskey_rrset("bondit.dk", flags=257, algorithm=13)
        ds_rrset = create_mock_ds_rrset("bondit.dk", key_tag=12345, algorithm=13)

        def resolve_side_effect(zone, record_type):
            mock_answer = MagicMock()
            if record_type == "DNSKEY":
                mock_answer.rrset = dnskey_rrset
            elif record_type == "DS":
                mock_answer.rrset = ds_rrset
            return mock_answer

        mock_resolver.resolve.side_effect = resolve_side_effect

        with patch("dns.dnssec.key_id", return_value=12345):
            validator = DNSSECValidator("bondit.dk")
            with patch.object(validator, "_add_tlsa_summary"):
                result = validator.validate()

            # Check DNSKEY records are stored
            assert len(result["records"]["dnskey"]) > 0
            dnskey_record = result["records"]["dnskey"][0]
            assert "flags" in dnskey_record
            assert "protocol" in dnskey_record
            assert "algorithm" in dnskey_record
            assert "key_tag" in dnskey_record

    @patch("dns.resolver.Resolver")
    def test_ds_records_stored(self, mock_resolver_class):
        """Test that DS records are stored in results."""
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        dnskey_rrset = create_mock_dnskey_rrset("bondit.dk", flags=257, algorithm=13)
        ds_rrset = create_mock_ds_rrset("bondit.dk", key_tag=12345, algorithm=13)

        def resolve_side_effect(zone, record_type):
            mock_answer = MagicMock()
            if record_type == "DNSKEY":
                mock_answer.rrset = dnskey_rrset
            elif record_type == "DS":
                mock_answer.rrset = ds_rrset
            return mock_answer

        mock_resolver.resolve.side_effect = resolve_side_effect

        with patch("dns.dnssec.key_id", return_value=12345):
            validator = DNSSECValidator("bondit.dk")
            with patch.object(validator, "_add_tlsa_summary"):
                result = validator.validate()

            # Check DS records are stored
            assert len(result["records"]["ds"]) > 0
            ds_record = result["records"]["ds"][0]
            assert "key_tag" in ds_record
            assert "algorithm" in ds_record
            assert "digest_type" in ds_record
            assert "digest" in ds_record
