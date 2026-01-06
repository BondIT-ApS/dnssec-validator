"""Tests for BondIT attribution footer functionality."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from unittest.mock import patch


class TestAttributionHelper:
    """Test the show_attribution helper function."""

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "true"})
    def test_attribution_enabled_with_true(self):
        """Test attribution is enabled with 'true' value."""
        # Need to import after setting env var
        import importlib
        import app

        importlib.reload(app)
        assert app.show_attribution() is True

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "false"})
    def test_attribution_disabled_with_false(self):
        """Test attribution is disabled with 'false' value."""
        import importlib
        import app

        importlib.reload(app)
        assert app.show_attribution() is False

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "1"})
    def test_attribution_enabled_with_one(self):
        """Test attribution is enabled with '1' value."""
        import importlib
        import app

        importlib.reload(app)
        assert app.show_attribution() is True

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "yes"})
    def test_attribution_enabled_with_yes(self):
        """Test attribution is enabled with 'yes' value."""
        import importlib
        import app

        importlib.reload(app)
        assert app.show_attribution() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_attribution_enabled_by_default(self):
        """Test attribution is enabled by default when env var not set."""
        # Clear the env var
        if "SHOW_BONDIT_ATTRIBUTION" in os.environ:
            del os.environ["SHOW_BONDIT_ATTRIBUTION"]

        import importlib
        import app

        importlib.reload(app)
        assert app.show_attribution() is True

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "0"})
    def test_attribution_disabled_with_zero(self):
        """Test attribution is disabled with '0' value."""
        import importlib
        import app

        importlib.reload(app)
        assert app.show_attribution() is False

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "no"})
    def test_attribution_disabled_with_no(self):
        """Test attribution is disabled with 'no' value."""
        import importlib
        import app

        importlib.reload(app)
        assert app.show_attribution() is False


class TestAttributionInTemplates:
    """Test that attribution is properly injected into templates."""

    def test_context_processor_exists(self):
        """Test that the context processor is registered."""
        import app as flask_app

        # Get context processors
        context_processors = flask_app.app.template_context_processors[None]
        processor_names = [func.__name__ for func in context_processors]

        assert "inject_attribution" in processor_names

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "true"})
    def test_context_processor_returns_true(self):
        """Test context processor returns correct value when enabled."""
        import importlib
        import app as flask_app

        importlib.reload(flask_app)

        result = flask_app.inject_attribution()
        assert "show_attribution" in result
        assert result["show_attribution"] is True

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "false"})
    def test_context_processor_returns_false(self):
        """Test context processor returns correct value when disabled."""
        import importlib
        import app as flask_app

        importlib.reload(flask_app)

        result = flask_app.inject_attribution()
        assert "show_attribution" in result
        assert result["show_attribution"] is False


class TestAttributionIntegration:
    """Integration tests for attribution footer in web pages."""

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "true"})
    def test_attribution_in_index_page(self):
        """Test attribution footer appears in index page when enabled."""
        import importlib
        import app as flask_app

        importlib.reload(flask_app)

        client = flask_app.app.test_client()
        response = client.get("/")

        assert response.status_code == 200
        html = response.data.decode("utf-8")

        # Check for attribution footer content
        assert "Made with ❤️, ☕, and 🧱 by" in html or "Made with" in html
        assert "BondIT ApS" in html
        assert "https://bondit.dk" in html
        assert "https://github.com/BondIT-ApS/dnssec-validator" in html

    @patch.dict(os.environ, {"SHOW_BONDIT_ATTRIBUTION": "false"})
    def test_attribution_not_in_index_when_disabled(self):
        """Test attribution footer does not appear when disabled."""
        import importlib
        import app as flask_app

        importlib.reload(flask_app)

        client = flask_app.app.test_client()
        response = client.get("/")

        assert response.status_code == 200
        html = response.data.decode("utf-8")

        # Attribution should not be present
        # Note: We check for the specific footer structure, not just the text
        # as BondIT may appear elsewhere on the page
        assert '<footer style="text-align: center' not in html or (
            "Built with" not in html and "bondit.dk" not in html
        )
