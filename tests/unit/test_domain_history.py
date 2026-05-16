"""
Unit tests for the SHOW_DOMAIN_CHECK_HISTORY feature: feature flag,
per-domain InfluxDB query helpers, and the /api/analytics/domain/<domain> endpoint.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../app"))


class TestDomainHistoryFeatureFlag(unittest.TestCase):
    """Test SHOW_DOMAIN_CHECK_HISTORY environment flag parsing."""

    def setUp(self):
        os.environ.pop("SHOW_DOMAIN_CHECK_HISTORY", None)

    def tearDown(self):
        os.environ.pop("SHOW_DOMAIN_CHECK_HISTORY", None)

    def test_disabled_by_default(self):
        import importlib
        import app as app_module

        importlib.reload(app_module)
        self.assertFalse(app_module.show_domain_check_history())

    def test_enabled_with_true_values(self):
        import importlib
        import app as app_module

        for value in ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]:
            os.environ["SHOW_DOMAIN_CHECK_HISTORY"] = value
            importlib.reload(app_module)
            self.assertTrue(
                app_module.show_domain_check_history(),
                f"Expected True for SHOW_DOMAIN_CHECK_HISTORY={value}",
            )

    def test_disabled_with_false_values(self):
        import importlib
        import app as app_module

        for value in ["false", "False", "0", "no", ""]:
            os.environ["SHOW_DOMAIN_CHECK_HISTORY"] = value
            importlib.reload(app_module)
            self.assertFalse(
                app_module.show_domain_check_history(),
                f"Expected False for SHOW_DOMAIN_CHECK_HISTORY={value}",
            )

    def test_context_processor_injects_flag(self):
        import importlib
        import app as app_module

        os.environ["SHOW_DOMAIN_CHECK_HISTORY"] = "true"
        importlib.reload(app_module)
        result = app_module.inject_domain_check_history()
        self.assertIn("show_domain_check_history", result)
        self.assertTrue(result["show_domain_check_history"])


class TestInfluxDomainQueries(unittest.TestCase):
    """Test that domain filter is applied to InfluxDB queries."""

    def _make_logger_with_capture(self):
        from models import InfluxDBLogger

        logger = InfluxDBLogger()
        captured = {}

        def fake_execute(flux_query):
            captured["query"] = flux_query
            return []

        logger._execute_query = fake_execute  # type: ignore[assignment]
        return logger, captured

    def test_get_requests_count_includes_domain_filter(self):
        logger, captured = self._make_logger_with_capture()
        logger.get_requests_count(hours=24, domain="example.com")
        self.assertIn('r.domain == "example.com"', captured["query"])

    def test_get_validation_ratio_includes_domain_filter(self):
        logger, captured = self._make_logger_with_capture()
        logger.get_validation_ratio(hours=24, domain="example.com")
        self.assertIn('r.domain == "example.com"', captured["query"])

    def test_get_hourly_requests_includes_domain_filter(self):
        logger, captured = self._make_logger_with_capture()
        logger.get_hourly_requests(hours=24, domain="example.com")
        self.assertIn('r.domain == "example.com"', captured["query"])

    def test_get_source_breakdown_includes_domain_filter(self):
        logger, captured = self._make_logger_with_capture()
        logger.get_source_breakdown(days=7, domain="example.com")
        self.assertIn('r.domain == "example.com"', captured["query"])

    def test_queries_without_domain_have_no_domain_filter(self):
        logger, captured = self._make_logger_with_capture()
        logger.get_requests_count(hours=24)
        self.assertNotIn("r.domain == ", captured["query"])


class TestDomainAnalyticsEndpoint(unittest.TestCase):
    """Test /api/analytics/domain/<domain> endpoint behavior."""

    def setUp(self):
        os.environ.pop("SHOW_DOMAIN_CHECK_HISTORY", None)
        # Disable rate limiting so test_client requests aren't throttled
        os.environ["FLASK_ENV"] = "testing"

    def tearDown(self):
        os.environ.pop("SHOW_DOMAIN_CHECK_HISTORY", None)

    def _reload_app(self):
        import importlib
        import app as app_module

        importlib.reload(app_module)
        # Disable rate limiter for tests
        app_module.limiter.enabled = False
        return app_module

    def test_endpoint_returns_404_when_feature_disabled(self):
        app_module = self._reload_app()
        with app_module.app.test_client() as client:
            response = client.get("/api/analytics/domain/example.com")
            self.assertEqual(response.status_code, 404)
            self.assertIn("disabled", response.get_json()["error"].lower())

    def test_endpoint_rejects_invalid_domain(self):
        os.environ["SHOW_DOMAIN_CHECK_HISTORY"] = "true"
        app_module = self._reload_app()
        with app_module.app.test_client() as client:
            response = client.get("/api/analytics/domain/not_a_valid_domain")
            self.assertEqual(response.status_code, 400)

    def test_endpoint_rejects_invalid_period(self):
        os.environ["SHOW_DOMAIN_CHECK_HISTORY"] = "true"
        app_module = self._reload_app()
        with patch.object(
            app_module.RequestLog, "get_domain_requests_count", return_value=0
        ):
            with app_module.app.test_client() as client:
                response = client.get("/api/analytics/domain/example.com?period=99h")
                self.assertEqual(response.status_code, 400)

    def test_endpoint_returns_aggregated_payload(self):
        os.environ["SHOW_DOMAIN_CHECK_HISTORY"] = "true"
        app_module = self._reload_app()

        with patch.object(
            app_module.RequestLog, "get_domain_requests_count", return_value=42
        ), patch.object(
            app_module.RequestLog,
            "get_domain_validation_ratio",
            return_value={
                "total": 42,
                "valid": {"count": 40, "percentage": 95.2},
                "invalid": {"count": 2, "percentage": 4.8},
                "error": {"count": 0, "percentage": 0},
            },
        ), patch.object(
            app_module.RequestLog,
            "get_domain_source_breakdown",
            return_value=[("external", 30), ("webapp", 12)],
        ), patch.object(
            app_module.RequestLog,
            "get_domain_hourly_requests",
            return_value=[("2026-05-16T10:00:00", 5), ("2026-05-16T11:00:00", 7)],
        ):
            with app_module.app.test_client() as client:
                response = client.get("/api/analytics/domain/example.com?period=24h")
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data["domain"], "example.com")
                self.assertEqual(data["period"], "24h")
                self.assertEqual(data["total_requests"], 42)
                self.assertEqual(data["sources"], {"external": 30, "webapp": 12})
                self.assertEqual(len(data["timeline"]), 2)
                self.assertEqual(data["timeline"][0]["requests"], 5)


class TestStatsTemplateRendering(unittest.TestCase):
    """Test that the stats template renders the feature flag and clickable counts correctly."""

    def setUp(self):
        os.environ.pop("SHOW_DOMAIN_CHECK_HISTORY", None)

    def tearDown(self):
        os.environ.pop("SHOW_DOMAIN_CHECK_HISTORY", None)

    def _reload_app(self):
        import importlib
        import app as app_module

        importlib.reload(app_module)
        app_module.limiter.enabled = False
        return app_module

    def test_stats_page_renders_flag_false_by_default(self):
        app_module = self._reload_app()
        with app_module.app.test_client() as client:
            response = client.get("/stats")
            self.assertEqual(response.status_code, 200)
            html = response.data.decode("utf-8")
            self.assertIn("const SHOW_DOMAIN_CHECK_HISTORY = false", html)

    def test_stats_page_renders_flag_true_when_enabled(self):
        os.environ["SHOW_DOMAIN_CHECK_HISTORY"] = "true"
        app_module = self._reload_app()
        with app_module.app.test_client() as client:
            response = client.get("/stats")
            self.assertEqual(response.status_code, 200)
            html = response.data.decode("utf-8")
            self.assertIn("const SHOW_DOMAIN_CHECK_HISTORY = true", html)


if __name__ == "__main__":
    unittest.main()
