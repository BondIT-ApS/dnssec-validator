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
    to_ascii,
    to_unicode,
    normalize_idn_domain,
    IDNConversionError,
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
        assert hasattr(domain_utils, "to_ascii")
        assert hasattr(domain_utils, "to_unicode")
        assert hasattr(domain_utils, "normalize_idn_domain")
        assert callable(domain_utils.extract_domain_from_input)
        assert callable(domain_utils.normalize_domain_input)
        assert callable(domain_utils.is_valid_domain_format)


class TestIDNConversion:
    """Tests for internationalized domain name (IDN) handling."""

    # Sample IDN domains covering several scripts called out in the issue.
    # Rather than hardcoding the punycode form (which depends on the precise
    # `idna` library version and is easy to get wrong by hand), we compute
    # the expected A-label dynamically using the same library the production
    # code uses, then assert round-trip and shape properties.
    UNICODE_DOMAINS = [
        "ドメイン.テスト",  # Japanese
        "домен.тест",  # Cyrillic
        "αλφαβητο.δοκιμή",  # Greek
        "العربية.اختبار",  # Arabic
    ]

    @staticmethod
    def _expected_ascii(unicode_domain):
        """Compute the canonical A-label for a Unicode domain via ``idna``."""
        import idna  # local import to keep top-of-module imports lean

        return idna.encode(unicode_domain, uts46=True).decode("ascii").lower()

    def test_to_ascii_converts_unicode_to_punycode(self):
        """Unicode IDN input must produce a valid A-label starting xn--."""
        for unicode_form in self.UNICODE_DOMAINS:
            ascii_form = to_ascii(unicode_form)
            assert ascii_form == self._expected_ascii(unicode_form)
            # Every label in an IDN should be ACE-prefixed since none of the
            # test domains have ASCII-only labels.
            for label in ascii_form.split("."):
                assert label.startswith("xn--")

    def test_to_ascii_passes_through_ascii_domains(self):
        """ASCII input should be returned unchanged (lowercased)."""
        assert to_ascii("example.com") == "example.com"
        assert to_ascii("Example.COM") == "example.com"
        # An A-label that's already in punycode form should round-trip.
        encoded = self._expected_ascii("ドメイン.テスト")
        assert to_ascii(encoded) == encoded

    def test_to_ascii_rejects_invalid_idn(self):
        """Garbage Unicode input should raise IDNConversionError."""
        with pytest.raises(IDNConversionError):
            to_ascii("")
        with pytest.raises(IDNConversionError):
            # Pure emoji is not a valid IDN under UTS-46
            to_ascii("💩.💩")

    def test_to_unicode_decodes_punycode(self):
        """A-label input should decode back to its Unicode form."""
        for unicode_form in self.UNICODE_DOMAINS:
            ascii_form = self._expected_ascii(unicode_form)
            assert to_unicode(ascii_form) == unicode_form

    def test_to_unicode_passes_through_plain_ascii(self):
        """Domains without ACE prefix should remain unchanged."""
        assert to_unicode("example.com") == "example.com"
        assert to_unicode("www.bondit.dk") == "www.bondit.dk"

    def test_normalize_idn_domain_returns_both_forms(self):
        """normalize_idn_domain returns both representations."""
        for unicode_form in self.UNICODE_DOMAINS:
            ascii_form = self._expected_ascii(unicode_form)
            result = normalize_idn_domain(unicode_form)
            assert result == {"unicode": unicode_form, "ascii": ascii_form}

            # Round-trip from punycode input must yield the same dict
            assert normalize_idn_domain(ascii_form) == result

    def test_extract_domain_from_unicode_input(self):
        """extract_domain_from_input should accept Unicode and return A-label."""
        for unicode_form in self.UNICODE_DOMAINS:
            assert extract_domain_from_input(unicode_form) == self._expected_ascii(
                unicode_form
            )

    def test_extract_domain_from_unicode_url(self):
        """Unicode hostnames embedded in URLs should be extracted and encoded."""
        extracted = extract_domain_from_input("https://ドメイン.テスト/path?x=1")
        assert extracted == self._expected_ascii("ドメイン.テスト")

    def test_normalize_domain_input_with_unicode(self):
        """normalize_domain_input must accept Unicode input."""
        domain, input_type = normalize_domain_input("ドメイン.テスト")
        assert domain == self._expected_ascii("ドメイン.テスト")
        assert input_type == "domain"

    def test_invalid_idn_returns_none(self):
        """Invalid IDN input should yield None rather than raising."""
        assert extract_domain_from_input("💩.💩") is None

    def test_is_valid_domain_format_accepts_punycode(self):
        """A-labels (xn--...) are valid domain formats."""
        for unicode_form in self.UNICODE_DOMAINS:
            ascii_form = self._expected_ascii(unicode_form)
            assert is_valid_domain_format(ascii_form)

    def test_is_valid_domain_format_rejects_raw_unicode(self):
        """Raw Unicode (U-label) is *not* a valid format at the regex layer."""
        # Callers should convert to A-label first via ``to_ascii``.
        for unicode_form in self.UNICODE_DOMAINS:
            assert not is_valid_domain_format(unicode_form)
