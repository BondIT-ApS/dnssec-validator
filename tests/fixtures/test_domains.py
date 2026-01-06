"""
Test domain fixtures for DNSSEC validation testing.
"""

# Valid DNSSEC-signed domains (production examples)
VALID_DOMAINS = [
    "bondit.dk",
    "cloudflare.com",
    "dns.google",
    "ietf.org",
]

# Unsigned domains (no DNSSEC)
UNSIGNED_DOMAINS = [
    "example.org",  # Intentionally unsigned
    "example.com",  # Intentionally unsigned
]

# Domains with known DNSSEC issues
INVALID_DOMAINS = [
    "broken-dnssec.example",  # Mock broken DNSSEC
    "bogus.example",  # Mock bogus DNSSEC
]

# Subdomains for fallback testing
SUBDOMAIN_TEST_CASES = [
    {
        "input": "www.bondit.dk",
        "subdomain": "www.bondit.dk",
        "root": "bondit.dk",
        "fallback_expected": True,
    },
    {
        "input": "api.service.bondit.dk",
        "subdomain": "api.service.bondit.dk",
        "intermediate": "service.bondit.dk",
        "root": "bondit.dk",
        "fallback_expected": True,
    },
    {
        "input": "bondit.dk",
        "subdomain": None,
        "root": "bondit.dk",
        "fallback_expected": False,
    },
]

# Invalid/malformed domain inputs
MALFORMED_DOMAINS = [
    "",  # Empty
    ".",  # Just a dot
    "..",  # Multiple dots
    "invalid domain with spaces",  # Spaces
    "domain..com",  # Double dots
    "-invalid.com",  # Starts with hyphen
    "invalid-.com",  # Ends with hyphen
    "a" * 256,  # Too long (>255 chars)
    "xn--invalid",  # Invalid punycode
]

# Special characters and edge cases
EDGE_CASE_DOMAINS = [
    "xn--n3h.com",  # Valid punycode (☃.com)
    "1.2.3.4",  # IP address (not a domain)
    "localhost",  # Single label
    "_dmarc.example.com",  # Underscore prefix (valid for DNS records)
]

# TLSA/DANE test domains
TLSA_TEST_DOMAINS = {
    "with_tlsa": {
        "domain": "mail.bondit.dk",
        "port": 25,
        "protocol": "tcp",
        "expected_status": "valid",
    },
    "without_tlsa": {
        "domain": "www.example.com",
        "port": 443,
        "protocol": "tcp",
        "expected_status": "no_records",
    },
    "invalid_tlsa": {
        "domain": "broken-tlsa.example",
        "port": 443,
        "protocol": "tcp",
        "expected_status": "invalid",
    },
}


def get_test_domain(category="valid", index=0):
    """
    Get a test domain from a specific category.

    Args:
        category (str): Category - 'valid', 'unsigned', 'invalid', 'malformed'
        index (int): Index in the category list (default: 0)

    Returns:
        str: Test domain name
    """
    categories = {
        "valid": VALID_DOMAINS,
        "unsigned": UNSIGNED_DOMAINS,
        "invalid": INVALID_DOMAINS,
        "malformed": MALFORMED_DOMAINS,
        "edge_case": EDGE_CASE_DOMAINS,
    }

    domains = categories.get(category, VALID_DOMAINS)
    if 0 <= index < len(domains):
        return domains[index]
    return domains[0] if domains else "bondit.dk"
