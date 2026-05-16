"""End-to-end coverage of the domain validation user flow.

These tests drive the form like a real user would, intercepting the
``/api/validate/<domain>`` request so the suite stays deterministic and
independent of live DNSSEC infrastructure. A separate test exercises the
TLSA/DANE section, which is gated by the ``SHOW_VALIDATION_TLSA_DANE``
feature flag.
"""

from __future__ import annotations

import json
import re

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api",
    reason="Install requirements-e2e.txt to run the Playwright suite.",
)

Page = playwright_sync_api.Page  # type: ignore[attr-defined]
Route = playwright_sync_api.Route  # type: ignore[attr-defined]
expect = playwright_sync_api.expect  # type: ignore[attr-defined]


def _success_payload(domain: str, include_tlsa: bool = False) -> dict:
    """Return a synthetic but realistic ``/api/validate`` success body."""
    payload = {
        "domain": domain,
        "status": "valid",
        "validation_time": "2026-05-16T12:00:00Z",
        "chain_of_trust": [
            {
                "zone": ".",
                "status": "valid",
                "algorithm": "ECDSAP256SHA256",
                "key_tag": "20326",
            },
            {
                "zone": "dk",
                "status": "valid",
                "algorithm": "RSASHA256",
                "key_tag": "12345",
            },
            {
                "zone": domain,
                "status": "valid",
                "algorithm": "ECDSAP256SHA256",
                "key_tag": "67890",
            },
        ],
        "records": {
            "dnskey": [
                {
                    "zone": domain,
                    "algorithm": "ECDSAP256SHA256",
                    "key_tag": "67890",
                    "flags": "257",
                }
            ]
        },
        "errors": [],
    }
    if include_tlsa:
        payload["tlsa_summary"] = {
            "status": "valid",
            "records_found": 1,
            "dane_status": "secure",
            "message": "TLSA record matches presented certificate.",
        }
    return payload


def _install_mock(page: Page, base_url: str, payload: dict) -> None:
    """Route the validation API call to a static JSON payload."""
    pattern = re.compile(re.escape(base_url) + r"/api/validate/.+")

    def handler(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(payload),
        )

    page.route(pattern, handler)


@pytest.mark.e2e
def test_validation_flow_renders_chain_of_trust(page: Page, base_url: str) -> None:
    """Submitting a domain should render status, chain of trust and DNSKEYs."""
    domain = "bondit.dk"
    _install_mock(page, base_url, _success_payload(domain))

    page.goto(f"{base_url}/")
    page.locator("#domain-input").fill(domain)
    page.locator("#dnssec-form button[type='submit']").click()

    results = page.locator("#results-container")
    expect(results).to_contain_text(f"Validation Results for {domain}", timeout=10_000)
    expect(results.locator("span.status-valid").first).to_contain_text("VALID")
    expect(results).to_contain_text("Chain of Trust")
    expect(results.locator(".chain-item")).to_have_count(4)
    expect(results).to_contain_text("DNSKEY Records")
    expect(results).to_contain_text("View Detailed Analysis")


@pytest.mark.e2e
def test_validation_flow_normalizes_url_input(page: Page, base_url: str) -> None:
    """The client must strip ``https://`` / ``www.`` before calling the API."""
    domain = "bondit.dk"
    captured: list[str] = []

    def handler(route: Route) -> None:
        captured.append(route.request.url)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(_success_payload(domain)),
        )

    page.route(re.compile(r".+/api/validate/.+"), handler)

    page.goto(f"{base_url}/")
    page.locator("#domain-input").fill("https://www.BondIT.dk/path?x=1")
    page.locator("#dnssec-form button[type='submit']").click()

    page.wait_for_function(
        "() => document.querySelector('#results-container').innerText"
        ".includes('Validation Results for')",
        timeout=10_000,
    )

    assert captured, "Validation API was never called"
    assert captured[-1].endswith(
        "/api/validate/bondit.dk"
    ), f"Expected normalized domain in API URL, got: {captured[-1]}"


@pytest.mark.e2e
def test_validation_flow_displays_api_errors(page: Page, base_url: str) -> None:
    """A non-2xx API response must surface as a human-readable error."""
    page.route(
        re.compile(r".+/api/validate/.+"),
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body=json.dumps(
                {
                    "domain": "broken.example",
                    "status": "error",
                    "validation_time": "2026-05-16T12:00:00Z",
                    "chain_of_trust": [],
                    "errors": ["Upstream DNS resolver timed out"],
                }
            ),
        ),
    )

    page.goto(f"{base_url}/")
    page.locator("#domain-input").fill("broken.example")
    page.locator("#dnssec-form button[type='submit']").click()

    results = page.locator("#results-container")
    expect(results).to_contain_text("ERROR", timeout=10_000)
    expect(results).to_contain_text("Upstream DNS resolver timed out")


@pytest.mark.e2e
def test_validation_flow_handles_network_failure(page: Page, base_url: str) -> None:
    """If the fetch itself fails the UI must display an error message."""
    page.route(
        re.compile(r".+/api/validate/.+"),
        lambda route: route.abort("failed"),
    )

    page.goto(f"{base_url}/")
    page.locator("#domain-input").fill("offline.example")
    page.locator("#dnssec-form button[type='submit']").click()

    expect(page.locator("#results-container")).to_contain_text("Error:", timeout=10_000)


@pytest.mark.e2e
def test_tlsa_dane_section_visibility_matches_feature_flag(
    page: Page, base_url: str, tlsa_dane_enabled: bool
) -> None:
    """The TLSA/DANE section must only render when the feature flag is on."""
    domain = "bondit.dk"
    _install_mock(page, base_url, _success_payload(domain, include_tlsa=True))

    page.goto(f"{base_url}/")
    page.locator("#domain-input").fill(domain)
    page.locator("#dnssec-form button[type='submit']").click()

    results = page.locator("#results-container")
    expect(results).to_contain_text(f"Validation Results for {domain}", timeout=10_000)

    tlsa_heading = results.get_by_role("heading", name=re.compile(r"TLSA/DANE"))

    if tlsa_dane_enabled:
        expect(tlsa_heading).to_be_visible()
        expect(results).to_contain_text("DANE Status:")
    else:
        expect(tlsa_heading).to_have_count(0)
