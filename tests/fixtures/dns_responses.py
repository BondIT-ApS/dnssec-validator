"""
Mock DNS response fixtures for DNSSEC validation testing.
"""

import dns.name
import dns.rdatatype
import dns.rdataclass
import dns.rrset
import dns.rdata
from unittest.mock import MagicMock


def create_mock_dnskey_rrset(domain, flags=257, algorithm=8, key_data="test_key"):
    """Create a mock DNSKEY RRset."""
    rrset = MagicMock()
    rrset.name = dns.name.from_text(domain)
    rrset.rdtype = dns.rdatatype.DNSKEY
    rrset.rdclass = dns.rdataclass.IN
    rrset.ttl = 3600

    # Create mock DNSKEY record
    dnskey = MagicMock()
    dnskey.flags = flags
    dnskey.protocol = 3
    dnskey.algorithm = algorithm
    dnskey.key = key_data.encode() if isinstance(key_data, str) else key_data

    rrset.__iter__ = lambda self: iter([dnskey])
    rrset.__len__ = lambda self: 1

    return rrset


def create_mock_ds_rrset(domain, key_tag=12345, algorithm=8, digest_type=2):
    """Create a mock DS RRset."""
    rrset = MagicMock()
    rrset.name = dns.name.from_text(domain)
    rrset.rdtype = dns.rdatatype.DS
    rrset.rdclass = dns.rdataclass.IN
    rrset.ttl = 3600

    # Create mock DS record
    ds = MagicMock()
    ds.key_tag = key_tag
    ds.algorithm = algorithm
    ds.digest_type = digest_type
    ds.digest = b"test_digest_hash"

    rrset.__iter__ = lambda self: iter([ds])
    rrset.__len__ = lambda self: 1

    return rrset


def create_mock_rrsig_rrset(
    domain,
    covered_type=dns.rdatatype.DNSKEY,
    algorithm=8,
    key_tag=12345,
    expiration=2147483647,
    inception=0,
):
    """Create a mock RRSIG RRset.

    Args:
        domain: Domain name
        covered_type: DNS record type covered by this signature
        algorithm: DNSSEC algorithm number
        key_tag: Key tag of the signing key
        expiration: Signature expiration timestamp (default: far future)
        inception: Signature inception timestamp (default: 0)
    """
    rrset = MagicMock()
    rrset.name = dns.name.from_text(domain)
    rrset.rdtype = dns.rdatatype.RRSIG
    rrset.rdclass = dns.rdataclass.IN
    rrset.ttl = 3600

    # Create mock RRSIG record
    rrsig = MagicMock()
    rrsig.type_covered = covered_type
    rrsig.algorithm = algorithm
    rrsig.labels = 2
    rrsig.original_ttl = 3600
    rrsig.expiration = expiration
    rrsig.inception = inception
    rrsig.key_tag = key_tag
    rrsig.signer = dns.name.from_text(domain)
    rrsig.signature = b"test_signature"

    rrset.__iter__ = lambda self: iter([rrsig])
    rrset.__len__ = lambda self: 1

    return rrset


# Valid DNSSEC chain responses
VALID_DNSSEC_CHAIN = {
    "bondit.dk": {
        "dnskey": create_mock_dnskey_rrset("bondit.dk", flags=257, algorithm=13),
        "ds": create_mock_ds_rrset("bondit.dk", key_tag=12345, algorithm=13),
        "rrsig": create_mock_rrsig_rrset("bondit.dk", algorithm=13, key_tag=12345),
        "status": "valid",
    },
    "cloudflare.com": {
        "dnskey": create_mock_dnskey_rrset("cloudflare.com", flags=257, algorithm=13),
        "ds": create_mock_ds_rrset("cloudflare.com", key_tag=2371, algorithm=13),
        "rrsig": create_mock_rrsig_rrset("cloudflare.com", algorithm=13, key_tag=2371),
        "status": "valid",
    },
}

# Unsigned domain (no DNSSEC)
UNSIGNED_DOMAIN = {
    "example.org": {
        "dnskey": None,
        "ds": None,
        "rrsig": None,
        "status": "insecure",
    }
}

# Broken DNSSEC chain
BROKEN_DNSSEC_CHAIN = {
    "broken-dnssec.example": {
        "dnskey": create_mock_dnskey_rrset(
            "broken-dnssec.example", flags=257, algorithm=8
        ),
        "ds": None,  # Missing DS record breaks the chain
        "rrsig": create_mock_rrsig_rrset(
            "broken-dnssec.example", algorithm=8, key_tag=99999
        ),
        "status": "invalid",
    }
}

# Bogus DNSSEC (signature verification fails)
BOGUS_DNSSEC = {
    "bogus.example": {
        "dnskey": create_mock_dnskey_rrset("bogus.example", flags=257, algorithm=8),
        "ds": create_mock_ds_rrset("bogus.example", key_tag=11111, algorithm=8),
        "rrsig": create_mock_rrsig_rrset(
            "bogus.example", algorithm=8, key_tag=22222
        ),  # Mismatched key tag
        "status": "bogus",
    }
}


def get_dns_response(domain, status="valid"):
    """
    Get mock DNS response for a domain.

    Args:
        domain (str): Domain name
        status (str): Expected status - 'valid', 'insecure', 'invalid', 'bogus'

    Returns:
        dict: Mock DNS response data
    """
    if status == "valid":
        return VALID_DNSSEC_CHAIN.get(domain, VALID_DNSSEC_CHAIN["bondit.dk"])
    elif status == "insecure":
        return UNSIGNED_DOMAIN.get(domain, UNSIGNED_DOMAIN["example.org"])
    elif status == "invalid":
        return BROKEN_DNSSEC_CHAIN.get(
            domain, BROKEN_DNSSEC_CHAIN["broken-dnssec.example"]
        )
    elif status == "bogus":
        return BOGUS_DNSSEC.get(domain, BOGUS_DNSSEC["bogus.example"])
    else:
        return None
