"""Tests for domain_utils module."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from domain_utils import (
    extract_domain_from_input,
    normalize_domain_input,
    is_valid_domain_format,
    extract_root_domain,
    has_subdomain,
)


class TestExtractDomainFromInput:
    """Test domain extraction from various input formats."""

    def test_extract_from_http_url(self):
        """Test extraction from HTTP URLs."""
        assert extract_domain_from_input("http://example.com") == "example.com"
        assert extract_domain_from_input("http://example.com/path") == "example.com"
        assert (
            extract_domain_from_input("http://example.com/path?query=value")
            == "example.com"
        )

    def test_extract_from_https_url(self):
        """Test extraction from HTTPS URLs."""
        assert extract_domain_from_input("https://example.com") == "example.com"
        assert (
            extract_domain_from_input("https://www.example.com/page")
            == "www.example.com"
        )

    def test_extract_from_plain_domain(self):
        """Test extraction from plain domain names."""
        assert extract_domain_from_input("example.com") == "example.com"
        assert extract_domain_from_input("www.example.com") == "www.example.com"

    def test_extract_with_port(self):
        """Test extraction with port numbers."""
        assert extract_domain_from_input("https://example.com:8080") == "example.com"
        assert (
            extract_domain_from_input("http://example.com:3000/path") == "example.com"
        )

    def test_extract_with_spaces(self):
        """Test extraction with spaces (should be removed)."""
        assert extract_domain_from_input(" example.com ") == "example.com"
        assert extract_domain_from_input("exam ple.com") == "example.com"

    def test_extract_uppercase(self):
        """Test that domains are lowercased."""
        assert extract_domain_from_input("EXAMPLE.COM") == "example.com"
        assert extract_domain_from_input("Example.Com") == "example.com"


class TestNormalizeDomainInput:
    """Test domain input normalization."""

    def test_normalize_plain_domain(self):
        """Test normalization of plain domain input."""
        domain, input_type = normalize_domain_input("example.com")
        assert domain == "example.com"
        assert input_type == "domain"

    def test_normalize_url_input(self):
        """Test normalization of URL input."""
        domain, input_type = normalize_domain_input("https://example.com/path")
        assert domain == "example.com"
        assert input_type == "url"

    def test_normalize_invalid_input(self):
        """Test normalization of invalid input."""
        domain, input_type = normalize_domain_input("")
        assert domain is None
        assert input_type == "invalid"

        domain, input_type = normalize_domain_input("not-a-domain")
        assert domain is None
        assert input_type == "invalid"


class TestIsValidDomainFormat:
    """Test domain format validation."""

    def test_valid_domains(self):
        """Test validation of valid domain formats."""
        assert is_valid_domain_format("example.com")
        assert is_valid_domain_format("www.example.com")
        assert is_valid_domain_format("sub.domain.example.com")
        assert is_valid_domain_format("example.co.uk")

    def test_invalid_domains(self):
        """Test validation rejects invalid domain formats."""
        assert not is_valid_domain_format("")
        assert not is_valid_domain_format("example")
        assert not is_valid_domain_format(".example.com")
        assert not is_valid_domain_format("example.com.")
        assert not is_valid_domain_format("example..com")


class TestExtractRootDomain:
    """Test root domain extraction."""

    def test_extract_from_subdomain(self):
        """Test extraction of root domain from subdomains."""
        assert extract_root_domain("www.example.com") == "example.com"
        assert extract_root_domain("api.v1.example.com") == "example.com"

    def test_already_root_domain(self):
        """Test that root domains are returned unchanged."""
        assert extract_root_domain("example.com") == "example.com"

    def test_two_part_tld(self):
        """Test handling of two-part TLDs."""
        assert extract_root_domain("www.example.co.uk") == "example.co.uk"


class TestHasSubdomain:
    """Test subdomain detection."""

    def test_has_subdomain(self):
        """Test detection of subdomains."""
        assert has_subdomain("www.example.com")
        assert has_subdomain("api.example.com")

    def test_no_subdomain(self):
        """Test detection when no subdomain present."""
        assert not has_subdomain("example.com")


class TestHealthCheck:
    """Basic smoke tests to ensure modules load."""

    def test_module_imports(self):
        """Test that all core modules can be imported."""
        import domain_utils
        import models

        assert domain_utils is not None
        assert models is not None

    def test_domain_utils_has_required_functions(self):
        """Test that domain_utils has required functions."""
        import domain_utils

        assert hasattr(domain_utils, "extract_domain_from_input")
        assert hasattr(domain_utils, "normalize_domain_input")
        assert hasattr(domain_utils, "is_valid_domain_format")
        assert callable(domain_utils.extract_domain_from_input)
        assert callable(domain_utils.normalize_domain_input)
        assert callable(domain_utils.is_valid_domain_format)
