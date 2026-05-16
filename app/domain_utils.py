"""
Domain utilities for URL parsing, IDN handling, and subdomain fallback logic.

This module handles both ASCII and internationalized (Unicode) domain names.
Unicode input (e.g. ``ドメイン.テスト``) is transparently converted to its
A-label (punycode) form so that downstream DNS queries — which only accept
ASCII — work correctly. The IDNA 2008 ``idna`` package is used for the
conversion (the standard library ``idna`` codec only supports IDNA 2003).
"""

import re
from urllib.parse import urlparse
import logging

import idna

logger = logging.getLogger(__name__)

# A domain may already be supplied in its punycode (A-label) form. Such labels
# always begin with the ACE prefix "xn--" (case-insensitive).
_ACE_PREFIX = "xn--"


class IDNConversionError(ValueError):
    """Raised when an internationalized domain name cannot be encoded/decoded."""


def _contains_non_ascii(value):
    """Return True if *value* contains any non-ASCII character."""
    if not value:
        return False
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return True
    return False


def to_ascii(domain):
    """Convert a (possibly Unicode) domain to its IDNA 2008 A-label form.

    Already-ASCII domains are returned unchanged (lowercased). Punycode-encoded
    inputs (``xn--*``) are also accepted and returned as-is.

    Args:
        domain (str): Domain in either Unicode (U-label) or ASCII (A-label)
            form. May include subdomains.

    Returns:
        str: ASCII representation suitable for DNS queries.

    Raises:
        IDNConversionError: If the input cannot be encoded as a valid IDN.
    """
    if not domain:
        raise IDNConversionError("Empty domain")

    domain = domain.strip().rstrip(".")
    if not domain:
        raise IDNConversionError("Empty domain")

    # Fast path: pure ASCII input — no conversion needed beyond lowercasing.
    if not _contains_non_ascii(domain):
        return domain.lower()

    try:
        # ``uts46=True`` performs case-folding and basic Unicode normalization
        # so that e.g. uppercase Cyrillic input round-trips correctly.
        encoded = idna.encode(domain, uts46=True).decode("ascii")
    except idna.IDNAError as exc:
        raise IDNConversionError(
            f"Invalid internationalized domain '{domain}': {exc}"
        ) from exc
    except UnicodeError as exc:
        raise IDNConversionError(f"Unable to encode domain '{domain}': {exc}") from exc

    return encoded.lower()


def to_unicode(domain):
    """Convert a domain to its Unicode (U-label) representation.

    ASCII domains without any ``xn--`` labels are returned unchanged. Domains
    containing ACE-prefixed labels are decoded to their Unicode form.

    Args:
        domain (str): Domain in either Unicode or ASCII form.

    Returns:
        str: Unicode representation. Falls back to the lowercased input if
            decoding fails (so callers always get *some* string back).
    """
    if not domain:
        return domain

    domain = domain.strip().rstrip(".").lower()

    # No ACE prefix anywhere and input is already ASCII → nothing to decode.
    if _ACE_PREFIX not in domain and not _contains_non_ascii(domain):
        return domain

    try:
        return idna.decode(domain)
    except idna.IDNAError as exc:
        logger.debug("Unable to decode IDN domain '%s': %s", domain, exc)
        return domain


def normalize_idn_domain(domain):
    """Return both the Unicode and ASCII (punycode) form of a domain.

    Args:
        domain (str): Domain in either form.

    Returns:
        dict: ``{"unicode": <U-label>, "ascii": <A-label>}``.

    Raises:
        IDNConversionError: If the domain cannot be converted.
    """
    ascii_form = to_ascii(domain)
    unicode_form = to_unicode(ascii_form)
    return {"unicode": unicode_form, "ascii": ascii_form}


def extract_domain_from_input(user_input):
    """
    Extract domain name from user input which might be:
    - A plain domain: bondit.services
    - A subdomain: argocd.bondit.services
    - A URL: https://argocd.bondit.services/path?query=1
    - An internationalized domain: ドメイン.テスト or its punycode form
      xn--eckwd4c7c.xn--zckzah

    Unicode input is converted to its A-label (punycode) form so that the
    returned domain can be used directly for DNS queries.

    Returns:
        str: The extracted domain name in ASCII (A-label) lowercase form,
            or None if extraction/validation fails.
    """
    if not user_input:
        return None

    # Preserve Unicode characters — only strip whitespace and lowercase
    # ASCII letters. Calling ``.lower()`` is safe for Unicode too.
    user_input = user_input.strip().replace(" ", "").lower()

    domain = None

    # If it looks like a URL, parse it
    if user_input.startswith(("http://", "https://", "ftp://")):
        try:
            parsed = urlparse(user_input)
            if parsed.hostname:
                domain = parsed.hostname
        except Exception as e:  # pylint: disable=broad-except
            logger.debug("Failed to parse URL %s: %s", user_input, e)

    # If it contains protocol-like patterns but isn't a valid URL, try to extract
    if domain is None and "://" in user_input:
        try:
            parts = user_input.split("://", 1)
            if len(parts) == 2:
                # Extract domain part before first /
                domain_part = parts[1].split("/")[0]
                # Remove port if present
                domain_part = domain_part.split(":")[0]
                if domain_part:
                    domain = domain_part
        except Exception as e:  # pylint: disable=broad-except
            logger.debug(
                "Failed to extract domain from URL-like input %s: %s",
                user_input,
                e,
            )

    # Otherwise, treat as direct domain input
    if domain is None:
        # Remove any trailing paths, queries, etc.
        domain = user_input.split("/")[0].split("?")[0].split("#")[0]
        # Remove port if present
        domain = domain.split(":")[0]

    if not domain:
        return None

    # Convert to ASCII (A-label) form for downstream DNS use. If the input is
    # invalid as an IDN, return None so callers can produce a clear 400 error.
    try:
        ascii_domain = to_ascii(domain)
    except IDNConversionError as exc:
        logger.debug("IDN conversion failed for %s: %s", domain, exc)
        return None

    return ascii_domain if is_valid_domain_format(ascii_domain) else None


def is_valid_domain_format(domain):
    """
    Check if a string has a valid domain format.

    Accepts both plain ASCII domains and IDN A-labels (``xn--...``). Pure
    Unicode (U-label) input is *not* considered valid here — call
    :func:`to_ascii` first to normalize.

    Args:
        domain (str): Domain to validate

    Returns:
        bool: True if domain format is valid
    """
    if not domain:
        return False

    # Reject pure Unicode input — A-labels are required at this layer.
    if _contains_non_ascii(domain):
        return False

    # Basic domain validation regex
    # Allows letters, numbers, hyphens, dots. Punycode labels are accepted
    # via the general ``[a-z0-9-]`` character class (they start with ``xn--``).
    domain_pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z0-9-]{2,}$"

    return (
        len(domain) <= 253  # RFC limit
        and "." in domain  # Must have at least one dot
        and not domain.startswith(".")  # Can't start with dot
        and not domain.endswith(
            "."
        )  # Can't end with dot (we'll handle root zones separately)
        and ".." not in domain  # No consecutive dots
        and re.match(domain_pattern, domain) is not None
    )


def extract_root_domain(domain):
    """
    Extract root domain from a subdomain.

    Examples:
        argocd.bondit.services -> bondit.services
        www.example.com -> example.com
        api.v1.mysite.org -> mysite.org
        bondit.services -> bondit.services (unchanged)

    Args:
        domain (str): Full domain including potential subdomains

    Returns:
        str: Root domain or None if extraction fails
    """
    if not domain or not is_valid_domain_format(domain):
        return None

    parts = domain.split(".")

    # If already a root domain (2 parts), return as-is
    if len(parts) <= 2:
        return domain

    # For 3+ parts, take the last 2 parts as root domain
    # This is a simple heuristic and may not work for all TLDs
    # For production, consider using a library like tldextract
    root_candidate = ".".join(parts[-2:])

    # Special handling for common two-part TLDs
    # This is simplified - in production you'd want a comprehensive TLD list
    two_part_tlds = {
        "co.uk",
        "co.nz",
        "com.au",
        "co.jp",
        "co.in",
        "co.za",
        "org.uk",
        "net.uk",
        "ac.uk",
        "gov.uk",
        "edu.au",
    }

    if len(parts) >= 3 and root_candidate in two_part_tlds:
        # Take last 3 parts for two-part TLD
        if len(parts) >= 3:
            root_candidate = ".".join(parts[-3:])

    return root_candidate if is_valid_domain_format(root_candidate) else domain


def has_subdomain(domain):
    """
    Check if a domain has subdomains.

    Args:
        domain (str): Domain to check

    Returns:
        bool: True if domain appears to have subdomains
    """
    if not domain or not is_valid_domain_format(domain):
        return False

    parts = domain.split(".")

    # Simple heuristic: more than 2 parts likely indicates subdomains
    # This is simplified and doesn't account for complex TLD structures
    return len(parts) > 2


def normalize_domain_input(user_input):
    """
    Normalize user input to extract and clean domain name.

    This function:
    1. Extracts domain from URLs
    2. Cleans and normalizes the domain
    3. Converts internationalized (Unicode) input to its A-label form
    4. Validates the format

    Args:
        user_input (str): Raw user input

    Returns:
        tuple: (normalized_domain, original_input_type)
        Where input_type is one of: 'domain', 'url', 'invalid'
    """
    if not user_input:
        return None, "invalid"

    original_input = user_input.strip()

    # Determine input type
    input_type = "domain"
    if original_input.startswith(("http://", "https://", "ftp://")):
        input_type = "url"
    elif "://" in original_input:
        input_type = "url"  # URL-like but malformed

    # Extract domain (this also performs IDN normalization)
    domain = extract_domain_from_input(original_input)

    if not domain or not is_valid_domain_format(domain):
        return None, "invalid"

    return domain, input_type


def get_fallback_domains(domain):
    """
    Get list of domains to try in fallback order.

    For subdomain.example.com, returns:
    ['subdomain.example.com', 'example.com']

    Args:
        domain (str): Original domain

    Returns:
        list: Ordered list of domains to try
    """
    if not domain:
        return []

    domains_to_try = [domain]

    # Add root domain if this is a subdomain
    if has_subdomain(domain):
        root_domain = extract_root_domain(domain)
        if root_domain and root_domain != domain:
            domains_to_try.append(root_domain)

    return domains_to_try
