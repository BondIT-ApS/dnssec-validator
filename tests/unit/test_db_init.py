"""
Unit tests for db_init module.
Tests InfluxDB database initialization.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))


@pytest.mark.unit
class TestDatabaseInitialization:
    """Test database initialization functions."""

    @patch("db_init.influx_logger")
    def test_initialize_database_success(self, mock_logger):
        """Test successful database initialization."""
        from db_init import initialize_database

        mock_client = MagicMock()
        mock_health = Mock(status="pass", message="OK")
        mock_client.health.return_value = mock_health
        mock_logger.client = mock_client
        mock_logger.get_database_info.return_value = {
            "bucket_name": "test-bucket",
            "bucket_id": "123",
        }

        result = initialize_database()

        assert result is True

    @patch("db_init.influx_logger")
    def test_initialize_database_no_client(self, mock_logger):
        """Test initialization when client connection fails."""
        from db_init import initialize_database

        mock_logger.client = None

        result = initialize_database()

        assert result is False

    @patch("db_init.influx_logger")
    def test_initialize_database_health_fail(self, mock_logger):
        """Test initialization when health check fails."""
        from db_init import initialize_database

        mock_client = MagicMock()
        mock_health = Mock(status="fail", message="Unhealthy")
        mock_client.health.return_value = mock_health
        mock_logger.client = mock_client

        result = initialize_database()

        assert result is False

    @patch("db_init.influx_logger")
    @patch("db_init.time.sleep")
    def test_initialize_database_with_recreate(self, mock_sleep, mock_logger):
        """Test database initialization with recreate flag."""
        from db_init import initialize_database

        mock_client = MagicMock()
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_logger.client = mock_client
        mock_logger.url = "http://test:8086"
        mock_logger.org = "test-org"
        mock_logger.bucket = "test-bucket"
        mock_logger.get_database_info.return_value = {
            "bucket_name": "test",
            "bucket_id": "123",
            "description": "Test bucket",
            "created_at": "2024-01-01",
        }
        mock_logger.recreate_database.return_value = True

        with patch.dict(
            os.environ, {"INFLUX_DB_RECREATE": "true", "INFLUX_DB_INIT_WAIT": "0"}
        ):
            result = initialize_database()

        assert result is True
        mock_logger.recreate_database.assert_called_once()

    @patch("db_init.influx_logger")
    @patch("db_init.time.sleep")
    def test_initialize_database_with_truncate(self, mock_sleep, mock_logger):
        """Test database initialization with truncate flag."""
        from db_init import initialize_database

        mock_client = MagicMock()
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_logger.client = mock_client
        mock_logger.url = "http://test:8086"
        mock_logger.org = "test-org"
        mock_logger.bucket = "test-bucket"
        mock_logger.get_database_info.return_value = {
            "bucket_name": "test",
            "bucket_id": "123",
        }
        mock_logger.truncate_database.return_value = True

        with patch.dict(
            os.environ, {"INFLUX_DB_TRUNCATE": "true", "INFLUX_DB_INIT_WAIT": "0"}
        ):
            result = initialize_database()

        assert result is True
        mock_logger.truncate_database.assert_called_once()

    @patch("db_init.influx_logger")
    @patch("db_init.time.sleep")
    def test_initialize_database_recreate_fails(self, mock_sleep, mock_logger):
        """Test initialization when recreate fails."""
        from db_init import initialize_database

        mock_client = MagicMock()
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_logger.client = mock_client
        mock_logger.url = "http://test:8086"
        mock_logger.org = "test-org"
        mock_logger.bucket = "test-bucket"
        mock_logger.get_database_info.return_value = {
            "bucket_name": "test",
            "bucket_id": "123",
        }
        mock_logger.recreate_database.return_value = False

        with patch.dict(
            os.environ, {"INFLUX_DB_RECREATE": "true", "INFLUX_DB_INIT_WAIT": "0"}
        ):
            result = initialize_database()

        assert result is False

    @patch("db_init.influx_logger")
    @patch("db_init.time.sleep")
    def test_initialize_database_truncate_fails(self, mock_sleep, mock_logger):
        """Test initialization when truncate fails."""
        from db_init import initialize_database

        mock_client = MagicMock()
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_logger.client = mock_client
        mock_logger.url = "http://test:8086"
        mock_logger.org = "test-org"
        mock_logger.bucket = "test-bucket"
        mock_logger.get_database_info.return_value = {
            "bucket_name": "test",
            "bucket_id": "123",
        }
        mock_logger.truncate_database.return_value = False

        with patch.dict(
            os.environ, {"INFLUX_DB_TRUNCATE": "true", "INFLUX_DB_INIT_WAIT": "0"}
        ):
            result = initialize_database()

        assert result is False

    def test_print_environment_variables(self):
        """Test printing environment variables."""
        from db_init import print_environment_variables

        with patch.dict(
            os.environ,
            {
                "INFLUX_URL": "http://test:8086",
                "INFLUX_ORG": "test-org",
                "INFLUX_BUCKET": "test-bucket",
                "INFLUX_TOKEN": "secret_token_12345678",
            },
        ):
            # Should not raise exception
            print_environment_variables()

    @patch("db_init.influx_logger")
    def test_initialize_database_error_in_info(self, mock_logger):
        """Test initialization when get_database_info returns error."""
        from db_init import initialize_database

        mock_client = MagicMock()
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_logger.client = mock_client
        mock_logger.get_database_info.return_value = {"error": "Bucket not found"}

        result = initialize_database()

        # Should still succeed if connection works
        assert result is True
