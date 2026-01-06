"""
Unit tests for models (InfluxDB logger).
Tests database operations with mocked InfluxDB client.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))


@pytest.mark.unit
class TestInfluxDBLogger:
    """Test InfluxDBLogger class."""

    def test_init_default_config(self):
        """Test logger initialization with default configuration."""
        with patch.dict(os.environ, {}, clear=True):
            from models import InfluxDBLogger

            logger = InfluxDBLogger()
            assert logger.url == "http://localhost:8086"
            assert logger.token == "dev-token"
            assert logger.org == "dnssec-validator"
            assert logger.bucket == "requests"

    def test_init_custom_config(self):
        """Test logger initialization with custom configuration."""
        with patch.dict(
            os.environ,
            {
                "INFLUX_URL": "http://custom:8086",
                "INFLUX_TOKEN": "custom-token",
                "INFLUX_ORG": "custom-org",
                "INFLUX_BUCKET": "custom-bucket",
            },
        ):
            from models import InfluxDBLogger

            logger = InfluxDBLogger()
            assert logger.url == "http://custom:8086"
            assert logger.token == "custom-token"
            assert logger.org == "custom-org"
            assert logger.bucket == "custom-bucket"

    @patch("models.InfluxDBClient")
    def test_client_property_success(self, mock_influx_client_class):
        """Test client property creates and returns client."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_health = Mock(status="pass", message="OK")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        client = logger.client

        assert client is not None
        mock_influx_client_class.assert_called_once()
        mock_client.health.assert_called_once()

    @patch("models.InfluxDBClient")
    def test_client_property_health_fail(self, mock_influx_client_class):
        """Test client property when health check fails."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_health = Mock(status="fail", message="Unhealthy")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        client = logger.client

        assert client is not None
        mock_client.health.assert_called_once()

    @patch("models.InfluxDBClient")
    def test_client_property_connection_error(self, mock_influx_client_class):
        """Test client property when connection fails."""
        from models import InfluxDBLogger

        mock_influx_client_class.side_effect = Exception("Connection failed")

        logger = InfluxDBLogger()
        client = logger.client

        assert client is None

    def test_log_request_no_client(self):
        """Test log_request when client is not available."""
        from models import InfluxDBLogger

        logger = InfluxDBLogger()
        logger._write_api = None

        result = logger.log_request(
            ip_address="192.168.1.1",
            domain="bondit.dk",
            http_status=200,
            dnssec_status="valid",
            source="api",
        )

        assert result is False

    @patch("models.InfluxDBClient")
    def test_log_request_success(self, mock_influx_client_class):
        """Test successful request logging."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        result = logger.log_request(
            ip_address="192.168.1.1",
            domain="bondit.dk",
            http_status=200,
            dnssec_status="valid",
            source="api",
            user_agent="TestAgent/1.0",
            client="webapp",
            request_type="basic",
        )

        assert result is True
        mock_write_api.write.assert_called_once()

    @patch("models.InfluxDBClient")
    def test_log_request_with_internal_flag(self, mock_influx_client_class):
        """Test request logging with internal flag."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        result = logger.log_request(
            ip_address="127.0.0.1",
            domain="test.dk",
            http_status=200,
            dnssec_status="valid",
            source="api",
            internal=True,
        )

        assert result is True

    @patch("models.InfluxDBClient")
    def test_log_request_error(self, mock_influx_client_class):
        """Test log_request error handling."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_write_api = MagicMock()
        mock_write_api.write.side_effect = Exception("Write error")
        mock_client.write_api.return_value = mock_write_api
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        result = logger.log_request(
            ip_address="192.168.1.1",
            domain="bondit.dk",
            http_status=200,
            dnssec_status="valid",
            source="api",
        )

        assert result is False

    @patch("models.InfluxDBClient")
    def test_get_requests_count(self, mock_influx_client_class):
        """Test getting request count."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_query_api = MagicMock()

        # Mock query results
        mock_record = Mock()
        mock_record.values = {"_value": 42}
        mock_table = Mock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]

        mock_client.query_api.return_value = mock_query_api
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        count = logger.get_requests_count(hours=24)

        assert count == 42
        mock_query_api.query.assert_called_once()

    @patch("models.InfluxDBClient")
    def test_get_requests_count_with_source(self, mock_influx_client_class):
        """Test getting request count filtered by source."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_query_api = MagicMock()
        mock_record = Mock()
        mock_record.values = {"_value": 10}
        mock_table = Mock()
        mock_table.records = [mock_record]
        mock_query_api.query.return_value = [mock_table]
        mock_client.query_api.return_value = mock_query_api
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        count = logger.get_requests_count(days=7, source="api")

        assert count == 10

    @patch("models.InfluxDBClient")
    def test_get_requests_count_no_query_api(self, mock_influx_client_class):
        """Test getting request count when query API not available."""
        from models import InfluxDBLogger

        logger = InfluxDBLogger()
        logger._query_api = None

        count = logger.get_requests_count(hours=1)

        assert count == 0

    @patch("models.InfluxDBClient")
    def test_get_top_domains(self, mock_influx_client_class):
        """Test getting top domains."""
        from models import InfluxDBLogger

        mock_client = MagicMock()
        mock_query_api = MagicMock()

        mock_record1 = Mock()
        mock_record1.values = {"domain": "bondit.dk", "_value": 50}
        mock_record2 = Mock()
        mock_record2.values = {"domain": "example.com", "_value": 30}

        mock_table = Mock()
        mock_table.records = [mock_record1, mock_record2]
        mock_query_api.query.return_value = [mock_table]

        mock_client.query_api.return_value = mock_query_api
        mock_health = Mock(status="pass")
        mock_client.health.return_value = mock_health
        mock_influx_client_class.return_value = mock_client

        logger = InfluxDBLogger()
        top_domains = logger.get_top_domains(limit=10, days=30)

        assert len(top_domains) == 2
        assert top_domains[0] == ("bondit.dk", 50)
        assert top_domains[1] == ("example.com", 30)


@pytest.mark.unit
class TestRequestLogCompatibility:
    """Test RequestLog compatibility layer."""

    @patch("models.influx_logger")
    def test_log_request(self, mock_logger):
        """Test RequestLog.log_request calls influx_logger."""
        from models import RequestLog

        mock_logger.log_request.return_value = True

        result = RequestLog.log_request(
            ip_address="192.168.1.1",
            domain="bondit.dk",
            http_status=200,
            dnssec_status="valid",
            source="api",
        )

        assert result is True
        mock_logger.log_request.assert_called_once()

    @patch("models.influx_logger")
    def test_get_requests_count(self, mock_logger):
        """Test RequestLog.get_requests_count calls influx_logger."""
        from models import RequestLog

        mock_logger.get_requests_count.return_value = 100

        result = RequestLog.get_requests_count(hours=24)

        assert result == 100
        mock_logger.get_requests_count.assert_called_once_with(24, None, None)

    @patch("models.influx_logger")
    def test_get_top_domains(self, mock_logger):
        """Test RequestLog.get_top_domains calls influx_logger."""
        from models import RequestLog

        mock_logger.get_top_domains.return_value = [("bondit.dk", 50)]

        result = RequestLog.get_top_domains(limit=10, days=30)

        assert len(result) == 1
        assert result[0] == ("bondit.dk", 50)

    @patch("models.influx_logger")
    def test_cleanup_old_logs(self, mock_logger):
        """Test RequestLog.cleanup_old_logs calls influx_logger."""
        from models import RequestLog

        mock_logger.cleanup_old_logs.return_value = 42

        result = RequestLog.cleanup_old_logs(days=90)

        assert result == 42
        mock_logger.cleanup_old_logs.assert_called_once_with(90)
