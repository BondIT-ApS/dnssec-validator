"""
Unit tests for the response caching feature.

Covers:
- get_cache_config env parsing (enabled/disabled, backend, TTL clamping)
- _is_cacheable_result skips errors but accepts successful results
- _extract_min_dns_ttl picks the smallest record TTL
- validate_with_cache integration: miss -> set -> hit -> "cached" marker
- /api/cache/stats endpoint exposes hit/miss/set/skip counters
- /api/cache/invalidate endpoints clear entries
- Validation endpoint returns the cached result on the second call
"""

import importlib
import os
import sys
import unittest
from unittest.mock import patch

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../app"))


CACHE_ENV_VARS = (
    "CACHE_ENABLED",
    "CACHE_BACKEND",
    "CACHE_DEFAULT_TIMEOUT",
    "CACHE_RESPECT_DNS_TTL",
    "CACHE_REDIS_URL",
)


def _clear_cache_env():
    for var in CACHE_ENV_VARS:
        os.environ.pop(var, None)


def _reload_app():
    """Reload the app module so environment changes take effect."""
    import app as app_module  # noqa: F401  (re-imported below)

    importlib.reload(app_module)
    return app_module


class TestCacheConfig(unittest.TestCase):
    """Tests for ``get_cache_config`` env parsing."""

    def setUp(self):
        _clear_cache_env()

    def tearDown(self):
        _clear_cache_env()

    def test_defaults_disabled_null_backend(self):
        app_module = _reload_app()
        config, enabled, respect_dns_ttl = app_module.get_cache_config()
        self.assertFalse(enabled)
        # When disabled we always fall back to NullCache
        self.assertEqual(config["CACHE_TYPE"], "NullCache")
        self.assertEqual(config["CACHE_DEFAULT_TIMEOUT"], 300)
        self.assertTrue(respect_dns_ttl)

    def test_enabled_simple_backend(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_BACKEND"] = "simple"
        os.environ["CACHE_DEFAULT_TIMEOUT"] = "600"
        app_module = _reload_app()
        config, enabled, _ = app_module.get_cache_config()
        self.assertTrue(enabled)
        self.assertEqual(config["CACHE_TYPE"], "SimpleCache")
        self.assertEqual(config["CACHE_DEFAULT_TIMEOUT"], 600)

    def test_enabled_redis_backend_with_url(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_BACKEND"] = "redis"
        os.environ["CACHE_REDIS_URL"] = "redis://example:6379/0"
        app_module = _reload_app()
        config, enabled, _ = app_module.get_cache_config()
        self.assertTrue(enabled)
        self.assertEqual(config["CACHE_TYPE"], "RedisCache")
        self.assertEqual(config["CACHE_REDIS_URL"], "redis://example:6379/0")

    def test_unknown_backend_falls_back_to_simple(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_BACKEND"] = "memcached-typo"
        app_module = _reload_app()
        config, enabled, _ = app_module.get_cache_config()
        self.assertTrue(enabled)
        self.assertEqual(config["CACHE_TYPE"], "SimpleCache")

    def test_invalid_timeout_defaults_to_300(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_DEFAULT_TIMEOUT"] = "not-a-number"
        app_module = _reload_app()
        config, _, _ = app_module.get_cache_config()
        self.assertEqual(config["CACHE_DEFAULT_TIMEOUT"], 300)

    def test_respect_dns_ttl_false(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_RESPECT_DNS_TTL"] = "false"
        app_module = _reload_app()
        _, _, respect_dns_ttl = app_module.get_cache_config()
        self.assertFalse(respect_dns_ttl)


class TestCacheableResult(unittest.TestCase):
    """Tests for ``_is_cacheable_result`` filtering."""

    def setUp(self):
        _clear_cache_env()

    def tearDown(self):
        _clear_cache_env()

    def test_valid_result_is_cacheable(self):
        app_module = _reload_app()
        self.assertTrue(
            app_module._is_cacheable_result({"status": "valid", "domain": "bondit.dk"})
        )

    def test_insecure_result_is_cacheable(self):
        app_module = _reload_app()
        self.assertTrue(
            app_module._is_cacheable_result(
                {"status": "insecure", "domain": "example.com"}
            )
        )

    def test_error_status_is_not_cacheable(self):
        app_module = _reload_app()
        self.assertFalse(
            app_module._is_cacheable_result({"status": "error", "errors": ["boom"]})
        )

    def test_populated_errors_are_not_cacheable(self):
        app_module = _reload_app()
        self.assertFalse(
            app_module._is_cacheable_result(
                {"status": "valid", "errors": ["non-empty"]}
            )
        )

    def test_non_dict_is_not_cacheable(self):
        app_module = _reload_app()
        self.assertFalse(app_module._is_cacheable_result(None))
        self.assertFalse(app_module._is_cacheable_result(["nope"]))


class TestMinDNSTTL(unittest.TestCase):
    """Tests for ``_extract_min_dns_ttl`` and ``_resolve_timeout``."""

    def setUp(self):
        _clear_cache_env()

    def tearDown(self):
        _clear_cache_env()

    def test_extracts_smallest_record_ttl(self):
        app_module = _reload_app()
        result = {
            "records": {
                "dnskey": [{"ttl": 3600}],
                "ds": [{"ttl": 7200}],
                "rrsig": [{"original_ttl": 60}],
            }
        }
        self.assertEqual(app_module._extract_min_dns_ttl(result), 60)

    def test_returns_none_when_no_ttl(self):
        app_module = _reload_app()
        self.assertIsNone(app_module._extract_min_dns_ttl({"records": {}}))

    def test_resolve_timeout_clamps_to_min_ttl(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_DEFAULT_TIMEOUT"] = "300"
        os.environ["CACHE_RESPECT_DNS_TTL"] = "true"
        app_module = _reload_app()
        result = {"records": {"dnskey": [{"ttl": 30}]}}
        self.assertEqual(app_module._resolve_timeout(result), 30)

    def test_resolve_timeout_uses_default_when_ttl_larger(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_DEFAULT_TIMEOUT"] = "300"
        os.environ["CACHE_RESPECT_DNS_TTL"] = "true"
        app_module = _reload_app()
        result = {"records": {"dnskey": [{"ttl": 99999}]}}
        self.assertEqual(app_module._resolve_timeout(result), 300)

    def test_resolve_timeout_ignores_ttl_when_disabled(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_DEFAULT_TIMEOUT"] = "300"
        os.environ["CACHE_RESPECT_DNS_TTL"] = "false"
        app_module = _reload_app()
        result = {"records": {"dnskey": [{"ttl": 30}]}}
        self.assertEqual(app_module._resolve_timeout(result), 300)


class TestValidateWithCache(unittest.TestCase):
    """End-to-end tests around ``validate_with_cache`` semantics."""

    def setUp(self):
        _clear_cache_env()

    def tearDown(self):
        _clear_cache_env()

    def _enabled_app(self):
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_BACKEND"] = "simple"
        os.environ["CACHE_DEFAULT_TIMEOUT"] = "120"
        app_module = _reload_app()
        # Ensure a clean slate for every test.
        app_module.cache.clear()
        app_module.cache_stats.reset()
        return app_module

    def test_disabled_bypasses_cache(self):
        app_module = _reload_app()  # disabled by default

        calls = []

        def fn():
            calls.append(1)
            return {"status": "valid", "domain": "x.com"}

        first = app_module.validate_with_cache("x.com", "basic", fn)
        second = app_module.validate_with_cache("x.com", "basic", fn)
        self.assertEqual(len(calls), 2)
        # No "cached" marker because we never went through the cache.
        self.assertNotIn("cached", first)
        self.assertNotIn("cached", second)
        stats = app_module.cache_stats.as_dict()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)

    def test_miss_then_hit_marks_cached(self):
        app_module = self._enabled_app()

        calls = []

        def fn():
            calls.append(1)
            return {"status": "valid", "domain": "y.com"}

        first = app_module.validate_with_cache("y.com", "basic", fn)
        second = app_module.validate_with_cache("y.com", "basic", fn)
        self.assertEqual(len(calls), 1, "Validator must run only once")
        self.assertFalse(first.get("cached", False))
        self.assertTrue(second.get("cached"))
        stats = app_module.cache_stats.as_dict()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["sets"], 1)
        self.assertEqual(stats["skipped"], 0)

    def test_error_results_not_cached(self):
        app_module = self._enabled_app()

        calls = []

        def fn():
            calls.append(1)
            return {"status": "error", "errors": ["boom"]}

        app_module.validate_with_cache("z.com", "basic", fn)
        app_module.validate_with_cache("z.com", "basic", fn)
        self.assertEqual(len(calls), 2)
        stats = app_module.cache_stats.as_dict()
        self.assertEqual(stats["sets"], 0)
        self.assertEqual(stats["skipped"], 2)

    def test_basic_and_detailed_use_separate_keys(self):
        app_module = self._enabled_app()

        def basic():
            return {"status": "valid", "kind": "basic"}

        def detailed():
            return {"status": "valid", "kind": "detailed"}

        b1 = app_module.validate_with_cache("k.com", "basic", basic)
        d1 = app_module.validate_with_cache("k.com", "detailed", detailed)
        self.assertEqual(b1["kind"], "basic")
        self.assertEqual(d1["kind"], "detailed")

        # Cache should now return them separately.
        b2 = app_module.validate_with_cache(
            "k.com", "basic", lambda: {"status": "valid", "kind": "WRONG"}
        )
        d2 = app_module.validate_with_cache(
            "k.com", "detailed", lambda: {"status": "valid", "kind": "WRONG"}
        )
        self.assertEqual(b2["kind"], "basic")
        self.assertEqual(d2["kind"], "detailed")

    def test_invalidate_domain_removes_entries(self):
        app_module = self._enabled_app()

        def fn():
            return {"status": "valid", "domain": "foo.test"}

        app_module.validate_with_cache("foo.test", "basic", fn)
        app_module.validate_with_cache("foo.test", "detailed", fn)
        removed = app_module.invalidate_cached_domain("foo.test")
        self.assertGreaterEqual(removed, 1)

        calls = []

        def fn2():
            calls.append(1)
            return {"status": "valid", "domain": "foo.test"}

        app_module.validate_with_cache("foo.test", "basic", fn2)
        self.assertEqual(len(calls), 1, "Cache entry should have been invalidated")


class TestCacheHTTPEndpoints(unittest.TestCase):
    """HTTP tests for the cache namespace and validate-endpoint integration."""

    def setUp(self):
        _clear_cache_env()
        os.environ["CACHE_ENABLED"] = "true"
        os.environ["CACHE_BACKEND"] = "simple"
        os.environ["CACHE_DEFAULT_TIMEOUT"] = "120"
        # Disable rate limiting to avoid flakiness when running many requests.
        os.environ["RATE_LIMIT_API_MINUTE"] = "10000"
        os.environ["RATE_LIMIT_API_HOUR"] = "10000"
        self.app_module = _reload_app()
        self.app_module.cache.clear()
        self.app_module.cache_stats.reset()
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        _clear_cache_env()
        os.environ.pop("RATE_LIMIT_API_MINUTE", None)
        os.environ.pop("RATE_LIMIT_API_HOUR", None)

    def test_stats_endpoint_initial_state(self):
        response = self.client.get("/api/cache/stats")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["enabled"])
        self.assertEqual(data["backend"], "SimpleCache")
        self.assertEqual(data["hits"], 0)
        self.assertEqual(data["misses"], 0)

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_validate_endpoint_returns_cached_result(self, mock_validate):
        mock_validate.return_value = {
            "domain": "bondit.dk",
            "status": "valid",
            "records": {"dnskey": [{"ttl": 3600}]},
        }

        # First call: miss
        r1 = self.client.get("/api/validate/bondit.dk")
        self.assertEqual(r1.status_code, 200)
        # Second call: hit
        r2 = self.client.get("/api/validate/bondit.dk")
        self.assertEqual(r2.status_code, 200)

        # Validator should have been called once.
        self.assertEqual(mock_validate.call_count, 1)

        # Second response is marked as cached.
        self.assertTrue(r2.get_json().get("cached", False))

        stats = self.client.get("/api/cache/stats").get_json()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_invalidate_domain_endpoint(self, mock_validate):
        mock_validate.return_value = {"domain": "bondit.dk", "status": "valid"}

        self.client.get("/api/validate/bondit.dk")
        # Invalidate
        inv = self.client.post("/api/cache/invalidate/bondit.dk")
        self.assertEqual(inv.status_code, 200)
        # Second validate should miss again -> validator called twice total.
        self.client.get("/api/validate/bondit.dk")
        self.assertEqual(mock_validate.call_count, 2)

    @patch("dnssec_validator.DNSSECValidator.validate")
    def test_invalidate_all_endpoint(self, mock_validate):
        mock_validate.return_value = {"domain": "bondit.dk", "status": "valid"}

        self.client.get("/api/validate/bondit.dk")
        clear = self.client.post("/api/cache/invalidate")
        self.assertEqual(clear.status_code, 200)
        stats = self.client.get("/api/cache/stats").get_json()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)
        # Next validate must hit the validator again.
        self.client.get("/api/validate/bondit.dk")
        self.assertEqual(mock_validate.call_count, 2)

    def test_invalidate_domain_endpoint_rejects_bad_input(self):
        response = self.client.post("/api/cache/invalidate/!!!not-a-domain!!!")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
