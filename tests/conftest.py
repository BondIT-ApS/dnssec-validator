"""
Pytest configuration and shared fixtures for DNSSEC Validator tests.
"""

import os
import sys
from unittest.mock import MagicMock, Mock

import pytest

# Add app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


@pytest.fixture(scope="session")
def app_root():
    """Return path to app directory."""
    return os.path.join(os.path.dirname(__file__), "..", "app")


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client for testing."""
    mock_client = MagicMock()
    mock_client.health.return_value = Mock(status="pass", message="OK")

    # Mock write API
    mock_write_api = MagicMock()
    mock_client.write_api.return_value = mock_write_api

    # Mock query API
    mock_query_api = MagicMock()
    mock_client.query_api.return_value = mock_query_api

    return mock_client


@pytest.fixture
def mock_influxdb_logger(monkeypatch, mock_influxdb_client):
    """Mock InfluxDBLogger for testing."""
    from models import InfluxDBLogger

    # Create logger instance
    logger = InfluxDBLogger()

    # Mock the client property to return our mock
    monkeypatch.setattr(logger, "_client", mock_influxdb_client)
    monkeypatch.setattr(
        logger, "_write_api", mock_influxdb_client.write_api.return_value
    )
    monkeypatch.setattr(
        logger, "_query_api", mock_influxdb_client.query_api.return_value
    )

    return logger


@pytest.fixture
def test_config():
    """Test configuration for Flask app."""
    return {
        "TESTING": True,
        "DEBUG": True,
        "RATELIMIT_ENABLED": False,
        "RATELIMIT_STORAGE_URL": "memory://",
        "SHOW_BONDIT_ATTRIBUTION": "true",
        "INFLUX_URL": "http://test-influx:8086",
        "INFLUX_TOKEN": "test-token",
        "INFLUX_ORG": "test-org",
        "INFLUX_BUCKET": "test-bucket",
    }


@pytest.fixture
def flask_app(test_config, monkeypatch):
    """Create Flask app instance for testing."""
    # Set environment variables for testing
    for key, value in test_config.items():
        monkeypatch.setenv(key, str(value))

    # Mock InfluxDB client to prevent real connections
    mock_client = MagicMock()
    mock_client.health.return_value = Mock(status="pass", message="OK")
    monkeypatch.setattr("models.InfluxDBClient", lambda **kwargs: mock_client)

    # Import after setting env vars
    import app as flask_app_module

    app_instance = flask_app_module.app
    app_instance.config.update(test_config)

    yield app_instance


@pytest.fixture
def client(flask_app):
    """Create Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def runner(flask_app):
    """Create Flask CLI test runner."""
    return flask_app.test_cli_runner()


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    """Reset environment variables before each test."""
    # This runs automatically before each test
    yield
    # Cleanup happens automatically with monkeypatch
