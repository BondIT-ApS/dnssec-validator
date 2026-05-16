"""
Unit tests for CAAValidator class.
Tests CAA (RFC 8659) validation logic with mocked DNS responses.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))

from caa_validator import (  # noqa: E402  pylint: disable=wrong-import-position
    CAAValidator,
    KNOWN_CAA_TAGS,
    ISSUANCE_TAGS,
)


def _make_caa_rr(tag, value, flags=0):
    """Helper to build a mock CAA rdata object."""
    rr = MagicMock()
    rr.flags = flags
    rr.tag = tag.encode("ascii") if isinstance(tag, str) else tag
    rr.value = value.encode("utf-8") if isinstance(value, str) else value
    return rr


def _make_answer(rrs, ttl=300):
    """Helper to build a mock dnspython answer object."""
    rrset = MagicMock()
    rrset.ttl = ttl
    rrset.__iter__ = lambda self: iter(rrs)
    answer = MagicMock()
    answer.rrset = rrset
    return answer


@pytest.mark.unit
class TestCAAValidatorInit:
    """Test CAAValidator initialization and constants."""

    def test_init_with_domain(self):
        validator = CAAValidator("bondit.dk")
        assert validator.domain == "bondit.dk"

    def test_init_strips_trailing_dot(self):
        validator = CAAValidator("bondit.dk.")
        assert validator.domain == "bondit.dk"

    def test_known_tags_present(self):
        assert "issue" in KNOWN_CAA_TAGS
        assert "issuewild" in KNOWN_CAA_TAGS
        assert "iodef" in KNOWN_CAA_TAGS

    def test_issuance_tags(self):
        assert "issue" in ISSUANCE_TAGS
        assert "issuewild" in ISSUANCE_TAGS
        assert "iodef" not in ISSUANCE_TAGS


@pytest.mark.unit
class TestCAAQuery:
    """Test CAA DNS query methods."""

    @patch("dns.resolver.Resolver")
    def test_query_caa_records_success(self, mock_resolver_class):
        validator = CAAValidator("bondit.dk")
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        rr = _make_caa_rr("issue", "letsencrypt.org", flags=0)
        mock_resolver.resolve.return_value = _make_answer([rr])

        records = validator._query_caa_records("bondit.dk")

        assert len(records) == 1
        assert records[0]["tag"] == "issue"
        assert records[0]["value"] == "letsencrypt.org"
        assert records[0]["critical"] is False
        assert records[0]["flags"] == 0

    @patch("dns.resolver.Resolver")
    def test_query_caa_records_critical_flag(self, mock_resolver_class):
        validator = CAAValidator("bondit.dk")
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        rr = _make_caa_rr("issue", "digicert.com", flags=128)
        mock_resolver.resolve.return_value = _make_answer([rr])

        records = validator._query_caa_records("bondit.dk")

        assert records[0]["critical"] is True
        assert records[0]["flags"] == 128

    @patch("dns.resolver.Resolver")
    def test_query_caa_nxdomain(self, mock_resolver_class):
        import dns.resolver

        validator = CAAValidator("example.test")
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        assert validator._query_caa_records("example.test") == []

    @patch("dns.resolver.Resolver")
    def test_query_caa_noanswer(self, mock_resolver_class):
        import dns.resolver

        validator = CAAValidator("example.test")
        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        assert validator._query_caa_records("example.test") == []


@pytest.mark.unit
class TestCAAInheritance:
    """Test RFC 8659 tree-climbing inheritance."""

    def test_inheritance_no_records_at_target_uses_parent(self):
        validator = CAAValidator("sub.example.dk")

        sub_records = []
        parent_records = [
            {
                "name": "example.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            }
        ]

        call_results = {"sub.example.dk.": sub_records, "example.dk.": parent_records}

        def fake_query(domain, timeout=10):
            # dnspython names append a trailing dot - normalise.
            key = domain if domain.endswith(".") else domain + "."
            return call_results.get(key, [])

        with patch.object(validator, "_query_caa_records", side_effect=fake_query):
            records, checked, inherited = validator._query_caa_with_inheritance()

        assert len(records) == 1
        assert checked == "example.dk"
        assert inherited is True

    def test_inheritance_returns_target_records_when_present(self):
        validator = CAAValidator("bondit.dk")

        target_records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            }
        ]

        with patch.object(validator, "_query_caa_records", return_value=target_records):
            records, checked, inherited = validator._query_caa_with_inheritance()

        assert records == target_records
        assert checked == "bondit.dk"
        assert inherited is False

    def test_inheritance_stops_at_root(self):
        validator = CAAValidator("nothing.invalid")

        with patch.object(validator, "_query_caa_records", return_value=[]):
            records, _, _ = validator._query_caa_with_inheritance()

        assert records == []


@pytest.mark.unit
class TestCAAAnalysis:
    """Test CAA record analysis logic."""

    def test_analyze_records_basic_issue(self):
        validator = CAAValidator("bondit.dk")
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            }
        ]
        analysis = validator._analyze_records(records)
        assert analysis["issuance_allowed"] is True
        assert analysis["authorized_cas"][0]["ca"] == "letsencrypt.org"
        # Without explicit issuewild, wildcard inherits issue policy.
        assert analysis["wildcard_authorized_cas"][0]["ca"] == "letsencrypt.org"

    def test_analyze_records_issuewild_separate(self):
        validator = CAAValidator("bondit.dk")
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            },
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issuewild",
                "value": "digicert.com",
                "ttl": 300,
            },
        ]
        analysis = validator._analyze_records(records)
        assert analysis["authorized_cas"][0]["ca"] == "letsencrypt.org"
        assert analysis["wildcard_authorized_cas"][0]["ca"] == "digicert.com"
        assert analysis["wildcard_issuance_allowed"] is True

    def test_analyze_records_blocking_issue(self):
        validator = CAAValidator("bondit.dk")
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": ";",
                "ttl": 300,
            }
        ]
        analysis = validator._analyze_records(records)
        assert analysis["issuance_allowed"] is False
        assert analysis["authorized_cas"] == []

    def test_analyze_records_issuewild_blocks_wildcards(self):
        validator = CAAValidator("bondit.dk")
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            },
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issuewild",
                "value": ";",
                "ttl": 300,
            },
        ]
        analysis = validator._analyze_records(records)
        assert analysis["issuance_allowed"] is True
        assert analysis["wildcard_issuance_allowed"] is False
        assert analysis["wildcard_authorized_cas"] == []

    def test_analyze_records_iodef(self):
        validator = CAAValidator("bondit.dk")
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "iodef",
                "value": "mailto:security@bondit.dk",
                "ttl": 300,
            }
        ]
        analysis = validator._analyze_records(records)
        assert analysis["iodef_targets"][0]["target"] == "mailto:security@bondit.dk"

    def test_extract_ca_name_with_params(self):
        result = CAAValidator._extract_ca_name(
            "letsencrypt.org;validationmethods=dns-01"
        )
        assert result == "letsencrypt.org"

    def test_extract_ca_name_bare_semicolon(self):
        assert CAAValidator._extract_ca_name(";") is None

    def test_extract_ca_name_empty(self):
        assert CAAValidator._extract_ca_name("") is None

    def test_decode_tag_bytes(self):
        assert CAAValidator._decode_tag(b"ISSUE") == "issue"

    def test_decode_value_bytes(self):
        assert CAAValidator._decode_value(b"letsencrypt.org") == "letsencrypt.org"


@pytest.mark.unit
class TestCAAValidateCAA:
    """Test the top-level validate_caa method."""

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_validate_caa_no_records(self, mock_query):
        mock_query.return_value = ([], "bondit.dk", False)
        validator = CAAValidator("bondit.dk")
        result = validator.validate_caa()
        assert result["caa_status"] == "no_records"
        assert result["caa_records"] == []
        assert len(result["warnings"]) > 0

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_validate_caa_valid(self, mock_query):
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            }
        ]
        mock_query.return_value = (records, "bondit.dk", False)
        validator = CAAValidator("bondit.dk")
        result = validator.validate_caa()
        assert result["caa_status"] == "valid"
        assert result["issuance_allowed"] is True
        authorized_ca_names = [ca["ca"] for ca in result["authorized_cas"]]
        assert authorized_ca_names == ["letsencrypt.org"]

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_validate_caa_restricted(self, mock_query):
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": ";",
                "ttl": 300,
            }
        ]
        mock_query.return_value = (records, "bondit.dk", False)
        validator = CAAValidator("bondit.dk")
        result = validator.validate_caa()
        assert result["caa_status"] == "restricted"
        assert result["issuance_allowed"] is False

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_validate_caa_error_handled(self, mock_query):
        mock_query.side_effect = RuntimeError("dns boom")
        validator = CAAValidator("bondit.dk")
        result = validator.validate_caa()
        assert result["caa_status"] == "error"
        assert len(result["errors"]) > 0

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_validate_caa_inherited_flag(self, mock_query):
        records = [
            {
                "name": "example.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            }
        ]
        mock_query.return_value = (records, "example.dk", True)
        validator = CAAValidator("sub.example.dk")
        result = validator.validate_caa()
        assert result["inherited"] is True
        assert result["checked_domain"] == "example.dk"


@pytest.mark.unit
class TestCAASyntaxValidation:
    """Test CAA syntax validation."""

    def test_unknown_tag_warning(self):
        validator = CAAValidator("bondit.dk")
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "futuretag",
                "value": "x",
                "ttl": 300,
            }
        ]
        warnings = validator._validate_syntax(records)
        assert any("Unknown CAA tag" in w for w in warnings)

    def test_reserved_flags_warning(self):
        validator = CAAValidator("bondit.dk")
        records = [
            {
                "name": "bondit.dk",
                "flags": 0x40,  # Reserved bit set
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            }
        ]
        warnings = validator._validate_syntax(records)
        assert any("Reserved CAA flag" in w for w in warnings)


@pytest.mark.unit
class TestCAADetailedAnalysis:
    """Test the detailed analysis output."""

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_detailed_analysis_keys(self, mock_query):
        mock_query.return_value = ([], "bondit.dk", False)
        validator = CAAValidator("bondit.dk")
        detailed = validator.get_detailed_analysis()

        assert "detailed_analysis" in detailed
        assert "record_analysis" in detailed["detailed_analysis"]
        assert "security_assessment" in detailed["detailed_analysis"]
        assert "recommendations" in detailed["detailed_analysis"]
        assert "troubleshooting" in detailed["detailed_analysis"]

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_detailed_analysis_no_records_recommendations(self, mock_query):
        mock_query.return_value = ([], "bondit.dk", False)
        validator = CAAValidator("bondit.dk")
        detailed = validator.get_detailed_analysis()
        recs = detailed["detailed_analysis"]["recommendations"]
        assert any("Add CAA records" in r for r in recs)

    @patch.object(CAAValidator, "_query_caa_with_inheritance")
    def test_detailed_analysis_score_for_valid(self, mock_query):
        records = [
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "issue",
                "value": "letsencrypt.org",
                "ttl": 300,
            },
            {
                "name": "bondit.dk",
                "flags": 0,
                "critical": False,
                "tag": "iodef",
                "value": "mailto:security@bondit.dk",
                "ttl": 300,
            },
        ]
        mock_query.return_value = (records, "bondit.dk", False)
        validator = CAAValidator("bondit.dk")
        detailed = validator.get_detailed_analysis()
        assessment = detailed["detailed_analysis"]["security_assessment"]
        assert assessment["overall_score"] > 0
        assert any("authorize" in s.lower() for s in assessment["strengths"])

    def test_describe_tag_known(self):
        assert "wildcard" in CAAValidator._describe_tag("issuewild").lower()

    def test_describe_tag_unknown(self):
        assert "Unknown" in CAAValidator._describe_tag("xyz")
