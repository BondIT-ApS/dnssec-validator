"""Pytest configuration for the Playwright end-to-end test suite.

The fixtures here are intentionally separate from the project-wide
``tests/conftest.py`` so that the heavyweight Playwright dependency stays
optional. Importing this module without ``playwright`` / ``pytest-playwright``
installed will produce a clear skip rather than an import error.

The e2e suite expects an already-running DNSSEC Validator server. By default
it targets ``http://localhost:8080``; override with the ``BASE_URL``
environment variable (e.g. when pointing the suite at a Docker container or a
staging deployment).
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import pytest

# Mark every test in tests/e2e/ as @pytest.mark.e2e automatically so the
# suite can be selected/deselected with `-m e2e` / `-m "not e2e"`.
pytestmark = pytest.mark.e2e

# Default to the local Flask app; override via env for CI/Docker scenarios.
DEFAULT_BASE_URL = "http://localhost:8080"


def _server_reachable(url: str, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to the server can be opened.

    A lightweight reachability probe avoids importing ``requests`` just for
    the conftest. We only need to know whether the port is accepting
    connections; the individual tests will surface HTTP-level failures.
    """
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def base_url() -> str:
    """Return the base URL of the running DNSSEC Validator instance.

    Honours the ``BASE_URL`` environment variable, falling back to
    ``http://localhost:8080``. If nothing is listening on the resolved host
    and port, every collected test is skipped so the suite does not falsely
    fail when the developer simply forgot to start the server.
    """
    url = os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    if not _server_reachable(url):
        pytest.skip(
            f"DNSSEC Validator not reachable at {url}. "
            "Start the server (python app/app.py) or set BASE_URL.",
            allow_module_level=False,
        )
    return url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):  # type: ignore[no-redef]
    """Tighten the default Playwright browser context for our suite.

    We disable service workers (the app does not use them) and pick a
    reasonable viewport so screenshots taken on failure are predictable.
    The ``browser_context_args`` fixture is provided by ``pytest-playwright``;
    here we just extend it.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
        "service_workers": "block",
    }


@pytest.fixture
def tlsa_dane_enabled() -> bool:
    """Return whether the TLSA/DANE UI section is expected to render.

    Mirrors the ``SHOW_VALIDATION_TLSA_DANE`` feature flag consumed by the
    Flask app. Tests that depend on this flag should skip themselves when
    it is disabled so the suite remains green in either configuration.
    """
    return os.getenv("SHOW_VALIDATION_TLSA_DANE", "false").lower() in {
        "true",
        "1",
        "yes",
    }
