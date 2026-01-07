"""
Unit tests for Google Analytics configuration and integration.
Tests the GA configuration, validation, and template injection.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import sys

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../app"))


class TestGoogleAnalyticsConfig(unittest.TestCase):
    """Test Google Analytics configuration and validation"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear any existing environment variables
        if "GA_ENABLED" in os.environ:
            del os.environ["GA_ENABLED"]
        if "GA_TRACKING_ID" in os.environ:
            del os.environ["GA_TRACKING_ID"]

    def tearDown(self):
        """Clean up after tests"""
        # Clear environment variables
        if "GA_ENABLED" in os.environ:
            del os.environ["GA_ENABLED"]
        if "GA_TRACKING_ID" in os.environ:
            del os.environ["GA_TRACKING_ID"]

    @patch("app.logger")
    def test_ga_disabled_by_default(self, mock_logger):
        """Test that GA is disabled by default"""
        from app import get_analytics_config

        config = get_analytics_config()

        self.assertFalse(config["ga_enabled"])
        self.assertEqual(config["ga_tracking_id"], "")
        mock_logger.debug.assert_called()

    @patch("app.logger")
    def test_ga_enabled_with_tracking_id(self, mock_logger):
        """Test GA enabled with valid tracking ID"""
        os.environ["GA_ENABLED"] = "true"
        os.environ["GA_TRACKING_ID"] = "G-TEST123456"

        from app import get_analytics_config

        config = get_analytics_config()

        self.assertTrue(config["ga_enabled"])
        self.assertEqual(config["ga_tracking_id"], "G-TEST123456")
        mock_logger.debug.assert_called_with(
            "Google Analytics enabled with tracking ID: G-TEST123456"
        )

    @patch("app.logger")
    def test_ga_enabled_without_tracking_id(self, mock_logger):
        """Test GA enabled but missing tracking ID logs error"""
        os.environ["GA_ENABLED"] = "true"
        # GA_TRACKING_ID not set

        from app import get_analytics_config

        config = get_analytics_config()

        # Should be disabled due to missing tracking ID
        self.assertFalse(config["ga_enabled"])
        self.assertEqual(config["ga_tracking_id"], "")

        # Should log an error
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        self.assertIn("GA_ENABLED is set to true", error_call)
        self.assertIn("GA_TRACKING_ID is missing", error_call)

    @patch("app.logger")
    def test_ga_enabled_with_empty_tracking_id(self, mock_logger):
        """Test GA enabled with empty tracking ID"""
        os.environ["GA_ENABLED"] = "true"
        os.environ["GA_TRACKING_ID"] = ""

        from app import get_analytics_config

        config = get_analytics_config()

        # Should be disabled due to empty tracking ID
        self.assertFalse(config["ga_enabled"])
        mock_logger.error.assert_called_once()

    @patch("app.logger")
    def test_ga_enabled_various_true_values(self, mock_logger):
        """Test GA enabled with various true values"""
        os.environ["GA_TRACKING_ID"] = "G-TEST123456"

        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]

        for value in true_values:
            os.environ["GA_ENABLED"] = value

            # Reload module to get fresh config
            import importlib
            import app as app_module

            importlib.reload(app_module)

            config = app_module.get_analytics_config()
            self.assertTrue(config["ga_enabled"], f"Failed for GA_ENABLED={value}")

    @patch("app.logger")
    def test_ga_disabled_various_false_values(self, mock_logger):
        """Test GA disabled with various false values"""
        os.environ["GA_TRACKING_ID"] = "G-TEST123456"

        false_values = ["false", "False", "FALSE", "0", "no", "No", "NO", ""]

        for value in false_values:
            os.environ["GA_ENABLED"] = value

            # Reload module to get fresh config
            import importlib
            import app as app_module

            importlib.reload(app_module)

            config = app_module.get_analytics_config()
            self.assertFalse(config["ga_enabled"], f"Failed for GA_ENABLED={value}")


class TestGoogleAnalyticsTemplateIntegration(unittest.TestCase):
    """Test Google Analytics template integration"""

    def setUp(self):
        """Set up test Flask app"""
        # Clear environment variables
        if "GA_ENABLED" in os.environ:
            del os.environ["GA_ENABLED"]
        if "GA_TRACKING_ID" in os.environ:
            del os.environ["GA_TRACKING_ID"]

    def tearDown(self):
        """Clean up after tests"""
        if "GA_ENABLED" in os.environ:
            del os.environ["GA_ENABLED"]
        if "GA_TRACKING_ID" in os.environ:
            del os.environ["GA_TRACKING_ID"]

    def test_inject_analytics_context_processor(self):
        """Test that inject_analytics context processor returns correct config"""
        os.environ["GA_ENABLED"] = "true"
        os.environ["GA_TRACKING_ID"] = "G-TEST123456"

        from app import inject_analytics

        result = inject_analytics()

        self.assertIn("ga_enabled", result)
        self.assertIn("ga_tracking_id", result)
        self.assertTrue(result["ga_enabled"])
        self.assertEqual(result["ga_tracking_id"], "G-TEST123456")

    def test_ga_config_available_in_templates(self):
        """Test that GA config is available in Flask templates"""
        os.environ["GA_ENABLED"] = "true"
        os.environ["GA_TRACKING_ID"] = "G-PROD123"

        # Import after setting env vars
        import importlib
        import app as app_module

        importlib.reload(app_module)

        with app_module.app.test_client() as client:
            response = client.get("/")
            self.assertEqual(response.status_code, 200)

            # Check that GA variables are in the response
            html = response.data.decode("utf-8")
            self.assertIn("window.GA_ENABLED = true", html)
            self.assertIn("G-PROD123", html)
            self.assertIn("analytics.js", html)
            self.assertIn("cookie-consent.js", html)

    def test_ga_disabled_in_templates(self):
        """Test that GA scripts are not loaded when disabled"""
        os.environ["GA_ENABLED"] = "false"

        # Import after setting env vars
        import importlib
        import app as app_module

        importlib.reload(app_module)

        with app_module.app.test_client() as client:
            response = client.get("/")
            self.assertEqual(response.status_code, 200)

            # Check that GA is disabled
            html = response.data.decode("utf-8")
            self.assertIn("window.GA_ENABLED = false", html)
            # Cookie consent should not be loaded when GA is disabled
            self.assertNotIn("cookie-consent.js", html)


class TestGoogleAnalyticsCSP(unittest.TestCase):
    """Test Content Security Policy for Google Analytics"""

    def test_csp_includes_ga_domains(self):
        """Test that CSP headers include Google Analytics domains"""
        import importlib
        import app as app_module

        importlib.reload(app_module)

        with app_module.app.test_client() as client:
            response = client.get("/")

            # Check CSP header
            csp_header = response.headers.get("Content-Security-Policy")
            self.assertIsNotNone(csp_header)

            # Check for GA domains in script-src
            self.assertIn("www.googletagmanager.com", csp_header)
            self.assertIn("www.google-analytics.com", csp_header)

            # Check for GA domains in connect-src
            self.assertIn("connect-src", csp_header)


if __name__ == "__main__":
    unittest.main()
