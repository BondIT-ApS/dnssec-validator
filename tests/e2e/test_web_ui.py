"""Smoke and structural checks for the DNSSEC Validator web UI.

These tests verify that the main page renders the expected controls, that
navigation links resolve, and that the Swagger UI is reachable. They do not
trigger DNS validation; for that flow see ``test_validation_flow.py``.
"""

from __future__ import annotations

import re

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="Install requirements-e2e.txt to run the Playwright suite.",
)

Page = playwright_sync_api.Page  # type: ignore[attr-defined]
expect = playwright_sync_api.expect  # type: ignore[attr-defined]


@pytest.mark.e2e
def test_index_page_renders_core_controls(page: Page, base_url: str) -> None:
    """The landing page must expose the domain input and submit button."""
    page.goto(f"{base_url}/")

    expect(page).to_have_title("DNSSEC Validator")
    expect(page.locator("h1")).to_contain_text("DNSSEC Validator")

    domain_input = page.locator("#domain-input")
    expect(domain_input).to_be_visible()
    # Placeholder is set in the template; assert it mentions a domain example.
    expect(domain_input).to_have_attribute(
        "placeholder", re.compile(r"domain", re.IGNORECASE)
    )
    # The required attribute must be present so the browser blocks empty
    # submissions before they ever hit the API.
    expect(domain_input).to_have_attribute("required", "")

    submit = page.locator("#dnssec-form button[type='submit']")
    expect(submit).to_be_visible()
    expect(submit).to_have_text("Validate DNSSEC")


@pytest.mark.e2e
def test_navigation_links_present(page: Page, base_url: str) -> None:
    """Analytics and API Docs links must be wired up on the header."""
    page.goto(f"{base_url}/")

    analytics_link = page.locator("nav a[href='/stats']")
    api_docs_link = page.locator("nav a[href='/api/docs/']")

    expect(analytics_link).to_be_visible()
    expect(analytics_link).to_contain_text("Analytics")
    expect(api_docs_link).to_be_visible()
    expect(api_docs_link).to_contain_text("API Docs")


@pytest.mark.e2e
def test_api_docs_page_loads_swagger_ui(page: Page, base_url: str) -> None:
    """The Swagger UI served by Flask-RESTX should render its container."""
    response = page.goto(f"{base_url}/api/docs/")
    assert response is not None
    assert response.ok, f"API docs returned HTTP {response.status}"

    # Flask-RESTX renders Swagger UI inside a #swagger-ui div, and the
    # toolbar typically contains the literal text "Swagger".
    expect(page.locator("#swagger-ui")).to_be_visible(timeout=10_000)


@pytest.mark.e2e
def test_health_endpoint_returns_ok(page: Page, base_url: str) -> None:
    """A quick HTTP-level sanity check via Playwright's request API."""
    response = page.request.get(f"{base_url}/health/simple")
    assert response.ok, f"/health/simple returned HTTP {response.status}"


@pytest.mark.e2e
def test_empty_submission_is_blocked_by_browser(page: Page, base_url: str) -> None:
    """Submitting an empty form must not trigger a network request.

    The ``required`` attribute on ``#domain-input`` should keep the browser
    from posting; we assert by listening for any ``/api/validate/`` request
    in the next short window.
    """
    page.goto(f"{base_url}/")

    requests: list[str] = []
    page.on(
        "request",
        lambda req: (requests.append(req.url) if "/api/validate/" in req.url else None),
    )

    page.locator("#dnssec-form button[type='submit']").click()
    page.wait_for_timeout(500)

    assert not requests, (
        "Empty form submission unexpectedly fired a validation request: " f"{requests}"
    )
