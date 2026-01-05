"""Tests for domain_utils module."""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from domain_utils import normalize_domain, extract_domain_from_url


class TestNormalizeDomain:
    """Test domain normalization functionality."""

    def test_normalize_domain_basic(self):
        """Test basic domain normalization."""
        assert normalize_domain("EXAMPLE.COM") == "example.com"
        assert normalize_domain("Example.Com") == "example.com"
        assert normalize_domain("example.com") == "example.com"

    def test_normalize_domain_with_spaces(self):
        """Test domain normalization with spaces."""
        assert normalize_domain(" example.com ") == "example.com"
        assert normalize_domain("exam ple.com") == "example.com"

    def test_normalize_domain_with_trailing_dot(self):
        """Test domain normalization with trailing dot."""
        assert normalize_domain("example.com.") == "example.com"

    def test_normalize_domain_subdomain(self):
        """Test subdomain normalization."""
        assert normalize_domain("www.example.com") == "www.example.com"
        assert normalize_domain("SUB.DOMAIN.example.com") == "sub.domain.example.com"


class TestExtractDomainFromUrl:
    """Test URL domain extraction functionality."""

    def test_extract_domain_from_http_url(self):
        """Test extraction from HTTP URLs."""
        assert extract_domain_from_url("http://example.com") == "example.com"
        assert (
            extract_domain_from_url("http://example.com/path") == "example.com"
        )
        assert (
            extract_domain_from_url("http://example.com/path?query=value")
            == "example.com"
        )

    def test_extract_domain_from_https_url(self):
        """Test extraction from HTTPS URLs."""
        assert extract_domain_from_url("https://example.com") == "example.com"
        assert (
            extract_domain_from_url("https://www.example.com/page")
            == "www.example.com"
        )

    def test_extract_domain_from_plain_domain(self):
        """Test extraction from plain domain names."""
        assert extract_domain_from_url("example.com") == "example.com"
        assert extract_domain_from_url("www.example.com") == "www.example.com"

    def test_extract_domain_with_port(self):
        """Test extraction with port numbers."""
        assert extract_domain_from_url("https://example.com:8080") == "example.com"
        assert (
            extract_domain_from_url("http://example.com:3000/path")
            == "example.com"
        )


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

        assert hasattr(domain_utils, "normalize_domain")
        assert hasattr(domain_utils, "extract_domain_from_url")
        assert callable(domain_utils.normalize_domain)
        assert callable(domain_utils.extract_domain_from_url)
