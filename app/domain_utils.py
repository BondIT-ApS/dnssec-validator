"""
Domain utilities for URL parsing and subdomain fallback logic.
"""

import re
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def extract_domain_from_input(user_input):
    """
    Extract domain name from user input which might be:
    - A plain domain: bondit.services
    - A subdomain: argocd.bondit.services
    - A URL: https://argocd.bondit.services/path?query=1

    Returns:
        str: The extracted domain name in lowercase
    """
    if not user_input:
        return None

    # Clean and normalize input
    user_input = user_input.strip().replace(" ", "").lower()

    # If it looks like a URL, parse it
    if user_input.startswith(("http://", "https://", "ftp://")):
        try:
            parsed = urlparse(user_input)
            domain = parsed.hostname
            if domain:
                return domain
        except Exception as e:
            logger.debug(f"Failed to parse URL {user_input}: {e}")

    # If it contains protocol-like patterns but isn't a valid URL, try to extract
    if "://" in user_input:
        try:
            # Try to extract everything after ://
            parts = user_input.split("://", 1)
            if len(parts) == 2:
                # Extract domain part before first /
                domain_part = parts[1].split("/")[0]
                # Remove port if present
                domain_part = domain_part.split(":")[0]
                if domain_part and is_valid_domain_format(domain_part):
                    return domain_part
        except Exception as e:
            logger.debug(
                f"Failed to extract domain from URL-like input {user_input}: {e}"
            )

    # Otherwise, treat as direct domain input
    # Remove any trailing paths, queries, etc.
    domain = user_input.split("/")[0].split("?")[0].split("#")[0]

    # Remove port if present
    domain = domain.split(":")[0]

    return domain if is_valid_domain_format(domain) else None


def is_valid_domain_format(domain):
    """
    Check if a string has a valid domain format.

    Args:
        domain (str): Domain to validate

    Returns:
        bool: True if domain format is valid
    """
    if not domain:
        return False

    # Basic domain validation regex
    # Allows letters, numbers, hyphens, dots
    # Must end with at least 2-letter TLD
    domain_pattern = (
        r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$"
    )

    return (
        len(domain) <= 253  # RFC limit
        and "." in domain  # Must have at least one dot
        and not domain.startswith(".")  # Can't start with dot
        and not domain.endswith(
            "."
        )  # Can't end with dot (we'll handle root zones separately)
        and not ".." in domain  # No consecutive dots
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
    3. Validates the format

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

    # Extract domain
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
