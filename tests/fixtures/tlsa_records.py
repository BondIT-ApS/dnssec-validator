"""
Mock TLSA record fixtures for DANE validation testing.
"""

from unittest.mock import MagicMock
import dns.name
import dns.rdatatype


def create_mock_tlsa_record(usage=3, selector=1, mtype=1, cert_data=None):
    """
    Create a mock TLSA record.

    Args:
        usage (int): Certificate usage (0-3)
        selector (int): Selector (0=Cert, 1=SPKI)
        mtype (int): Matching type (0=Full, 1=SHA-256, 2=SHA-512)
        cert_data (bytes): Certificate association data

    Returns:
        MagicMock: Mock TLSA record
    """
    if cert_data is None:
        # Default SHA-256 hash
        cert_data = bytes.fromhex("0123456789abcdef" * 4)  # 32 bytes for SHA-256

    tlsa_record = MagicMock()
    tlsa_record.usage = usage
    tlsa_record.selector = selector
    tlsa_record.mtype = mtype
    tlsa_record.cert = cert_data

    return tlsa_record


def create_mock_tlsa_rrset(domain, port=443, protocol="tcp", records=None):
    """
    Create a mock TLSA RRset.

    Args:
        domain (str): Domain name
        port (int): Port number
        protocol (str): Protocol (tcp/udp)
        records (list): List of TLSA records (or None to create default)

    Returns:
        MagicMock: Mock TLSA RRset
    """
    if records is None:
        records = [create_mock_tlsa_record()]

    rrset = MagicMock()
    rrset.name = dns.name.from_text(f"_{port}._{protocol}.{domain}")
    rrset.rdtype = dns.rdatatype.TLSA
    rrset.rdclass = dns.rdataclass.IN
    rrset.ttl = 3600

    rrset.__iter__ = lambda self: iter(records)
    rrset.__len__ = lambda self: len(records)
    rrset.rrset = records

    return rrset


# DANE-EE (usage=3) - Most common, domain-issued certificate
DANE_EE_TLSA = {
    "usage": 3,  # DANE-EE
    "selector": 1,  # SPKI
    "mtype": 1,  # SHA-256
    "cert_data": bytes.fromhex(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
    "description": "DANE-EE: Domain-issued certificate with SPKI SHA-256",
}

# DANE-TA (usage=2) - Trust anchor assertion
DANE_TA_TLSA = {
    "usage": 2,  # DANE-TA
    "selector": 0,  # Full certificate
    "mtype": 1,  # SHA-256
    "cert_data": bytes.fromhex("a" * 64),  # 32 bytes hex = 64 chars
    "description": "DANE-TA: Trust anchor assertion with full cert SHA-256",
}

# PKIX-EE (usage=1) - Service certificate constraint
PKIX_EE_TLSA = {
    "usage": 1,  # PKIX-EE
    "selector": 1,  # SPKI
    "mtype": 1,  # SHA-256
    "cert_data": bytes.fromhex("b" * 64),
    "description": "PKIX-EE: Service certificate constraint",
}

# PKIX-TA (usage=0) - CA constraint
PKIX_TA_TLSA = {
    "usage": 0,  # PKIX-TA
    "selector": 0,  # Full certificate
    "mtype": 1,  # SHA-256
    "cert_data": bytes.fromhex("c" * 64),
    "description": "PKIX-TA: CA constraint",
}

# SHA-512 variant
SHA512_TLSA = {
    "usage": 3,  # DANE-EE
    "selector": 1,  # SPKI
    "mtype": 2,  # SHA-512
    "cert_data": bytes.fromhex("d" * 128),  # 64 bytes hex = 128 chars
    "description": "DANE-EE with SHA-512 matching",
}

# Full certificate data (no hash)
FULL_CERT_TLSA = {
    "usage": 3,  # DANE-EE
    "selector": 0,  # Full certificate
    "mtype": 0,  # No hash
    "cert_data": b"MOCK_FULL_CERTIFICATE_DATA" * 10,  # Larger data
    "description": "DANE-EE with full certificate data",
}


# Mock certificate for TLSA validation
MOCK_CERTIFICATE = {
    "subject": "CN=mail.bondit.dk",
    "issuer": "CN=BondIT CA, O=BondIT ApS, C=DK",
    "serial_number": "123456789",
    "not_valid_before": "2024-01-01T00:00:00",
    "not_valid_after": "2025-12-31T23:59:59",
    "signature_algorithm": "sha256WithRSAEncryption",
    "public_key_algorithm": "RSAPublicKey",
    "der_data": b"MOCK_DER_CERTIFICATE_DATA",
    "spki_data": b"MOCK_SPKI_DATA",
    "cert_sha256": bytes.fromhex(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
    "spki_sha256": bytes.fromhex(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
    "cert_sha512": bytes.fromhex("d" * 128),
    "spki_sha512": bytes.fromhex("d" * 128),
}


def get_tlsa_fixture(fixture_type="dane_ee"):
    """
    Get TLSA fixture by type.

    Args:
        fixture_type (str): Type of TLSA fixture

    Returns:
        dict: TLSA fixture data
    """
    fixtures = {
        "dane_ee": DANE_EE_TLSA,
        "dane_ta": DANE_TA_TLSA,
        "pkix_ee": PKIX_EE_TLSA,
        "pkix_ta": PKIX_TA_TLSA,
        "sha512": SHA512_TLSA,
        "full_cert": FULL_CERT_TLSA,
    }
    return fixtures.get(fixture_type, DANE_EE_TLSA)


def get_mock_certificate():
    """Get mock certificate for testing."""
    return MOCK_CERTIFICATE.copy()
