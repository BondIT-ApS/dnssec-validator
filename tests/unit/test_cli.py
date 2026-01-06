"""
Unit tests for CLI commands.
Tests command-line interface with InfluxDB.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "app"))


@pytest.mark.unit
class TestCLICommands:
    """Test CLI command functionality."""

    def test_cli_group_exists(self):
        """Test that CLI group is callable."""
        from cli import cli

        assert callable(cli)

    @patch("cli.influx_logger")
    def test_init_db_success(self, mock_logger):
        """Test init_db command success."""
        from cli import init_db

        mock_logger.client = MagicMock()
        mock_logger.get_database_info.return_value = {
            "bucket_name": "test-bucket",
            "bucket_id": "123",
        }

        runner = CliRunner()
        result = runner.invoke(init_db)

        assert result.exit_code == 0
        assert "successful" in result.output.lower()

    @patch("cli.influx_logger")
    def test_init_db_no_client(self, mock_logger):
        """Test init_db when client connection fails."""
        from cli import init_db

        mock_logger.client = None

        runner = CliRunner()
        result = runner.invoke(init_db)

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    @patch("cli.RequestLog")
    def test_cleanup_logs_dry_run(self, mock_request_log):
        """Test cleanup_logs with dry-run flag."""
        from cli import cleanup_logs

        runner = CliRunner()
        result = runner.invoke(cleanup_logs, ["--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    @patch("cli.RequestLog")
    def test_cleanup_logs_actual_deletion(self, mock_request_log):
        """Test cleanup_logs performs actual deletion."""
        from cli import cleanup_logs

        mock_request_log.cleanup_old_logs.return_value = 50

        runner = CliRunner()
        result = runner.invoke(cleanup_logs, ["--days", "30"])

        assert result.exit_code == 0
        assert "Successfully deleted" in result.output
        assert "50" in result.output
        mock_request_log.cleanup_old_logs.assert_called_once_with(30)

    @patch("cli.RequestLog")
    def test_cleanup_logs_error(self, mock_request_log):
        """Test cleanup_logs handles errors."""
        from cli import cleanup_logs

        mock_request_log.cleanup_old_logs.side_effect = Exception("DB error")

        runner = CliRunner()
        result = runner.invoke(cleanup_logs)

        assert result.exit_code == 1
        assert "Error during cleanup" in result.output

    @patch("cli.RequestLog")
    def test_stats_command(self, mock_request_log):
        """Test stats command displays statistics."""
        from cli import stats

        mock_request_log.get_requests_count.side_effect = [100, 500, 800, 1000]
        mock_request_log.get_top_domains.return_value = [
            ("bondit.dk", 50),
            ("example.com", 30),
        ]
        mock_request_log.get_validation_ratio.return_value = {
            "total": 1000,
            "valid": {"count": 800, "percentage": 80.0},
            "invalid": {"count": 150, "percentage": 15.0},
            "error": {"count": 50, "percentage": 5.0},
        }

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 0
        assert "Statistics" in result.output
        assert "bondit.dk" in result.output

    @patch("cli.RequestLog")
    def test_stats_error(self, mock_request_log):
        """Test stats command handles errors."""
        from cli import stats

        mock_request_log.get_requests_count.side_effect = Exception("DB error")

        runner = CliRunner()
        result = runner.invoke(stats)

        assert result.exit_code == 1
        assert "Error retrieving statistics" in result.output

    @patch("cli.RequestLog")
    def test_recent_requests_command(self, mock_request_log):
        """Test recent_requests command."""
        from cli import recent_requests

        mock_request_log.get_requests_count.return_value = 100
        mock_request_log.get_hourly_requests.return_value = [
            ("2024-01-01 12:00", 50),
            ("2024-01-01 13:00", 50),
        ]

        runner = CliRunner()
        result = runner.invoke(recent_requests, ["--hours", "24"])

        assert result.exit_code == 0
        assert "Request Statistics" in result.output
        assert "100" in result.output

    @patch("cli.RequestLog")
    def test_recent_requests_no_data(self, mock_request_log):
        """Test recent_requests when no requests found."""
        from cli import recent_requests

        mock_request_log.get_requests_count.return_value = 0

        runner = CliRunner()
        result = runner.invoke(recent_requests)

        assert result.exit_code == 0
        assert "No requests found" in result.output

    @patch("cli.RequestLog")
    def test_recent_requests_error(self, mock_request_log):
        """Test recent_requests handles errors."""
        from cli import recent_requests

        mock_request_log.get_requests_count.side_effect = Exception("DB error")

        runner = CliRunner()
        result = runner.invoke(recent_requests)

        assert result.exit_code == 1
        assert "Error retrieving recent requests" in result.output
