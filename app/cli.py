#!/usr/bin/env python3
"""
CLI commands for DNSSEC Validator influx db management
"""

import os
import sys
import click
from models import RequestLog, influx_logger


@click.group()
def cli():
    """DNSSEC Validator CLI commands"""
    pass


@cli.command()
@click.option("--days", default=90, help="Delete logs older than N days (default: 90)")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting",
)
def cleanup_logs(days, dry_run):
    """Clean up old request logs from InfluxDB"""
    try:
        if dry_run:
            click.echo(f"DRY RUN: Would delete log entries older than {days} days")
            click.echo("Note: InfluxDB uses retention policies for automatic cleanup")
            return

        # Perform actual cleanup
        deleted = RequestLog.cleanup_old_logs(days)
        click.echo(f"Successfully deleted {deleted} log entries older than {days} days")

    except Exception as e:
        click.echo(f"Error during cleanup: {e}", err=True)
        sys.exit(1)


@cli.command()
def init_db():
    """Initialize the InfluxDB bucket"""
    try:
        if influx_logger.client:
            click.echo("InfluxDB connection successful")
            bucket_info = influx_logger.get_database_info()
            if "error" in bucket_info:
                click.echo(f"Bucket not found, may need to create it manually")
            else:
                click.echo(f"Bucket '{bucket_info['bucket_name']}' exists")
                click.echo("Database initialized successfully")
        else:
            click.echo("Error: Could not connect to InfluxDB", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)
        sys.exit(1)


@cli.command()
def stats():
    """Show database statistics from InfluxDB"""
    try:
        last_hour = RequestLog.get_requests_count(hours=1)
        last_day = RequestLog.get_requests_count(days=1)
        last_week = RequestLog.get_requests_count(days=7)
        last_month = RequestLog.get_requests_count(days=30)

        click.echo("\n=== DNSSEC Validator Statistics ===")
        click.echo(f"Last hour:      {last_hour}")
        click.echo(f"Last 24 hours:  {last_day}")
        click.echo(f"Last 7 days:    {last_week}")
        click.echo(f"Last 30 days:   {last_month}")

        # Top domains
        top_domains = RequestLog.get_top_domains(limit=10, days=30)
        if top_domains:
            click.echo("\n=== Top 10 Domains (Last 30 days) ===")
            for domain, count in top_domains:
                click.echo(f"{domain}: {count} requests")

        # Validation ratio
        ratio = RequestLog.get_validation_ratio(days=30)
        if ratio.get("total", 0) > 0:
            click.echo(f"\n=== Validation Results (Last 30 days) ===")
            for status in ["valid", "invalid", "error"]:
                if status in ratio:
                    click.echo(
                        f"{status.capitalize()}: {ratio[status]['count']} ({ratio[status]['percentage']}%)"
                    )

    except Exception as e:
        click.echo(f"Error retrieving statistics: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--hours", default=24, help="Show requests from last N hours (default: 24)"
)
def recent_requests(hours):
    """Show recent request statistics from InfluxDB"""
    try:
        count = RequestLog.get_requests_count(hours=hours)

        if count == 0:
            click.echo(f"No requests found in the last {hours} hours.")
            return

        click.echo(f"\n=== Request Statistics (Last {hours} hours) ===")
        click.echo(f"Total requests: {count}")

        # Get hourly breakdown
        hourly = RequestLog.get_hourly_requests(hours=hours)
        if hourly:
            click.echo("\nHourly breakdown:")
            for timestamp, request_count in hourly[:10]:  # Show last 10 hours
                click.echo(f"{timestamp}: {request_count} requests")

    except Exception as e:
        click.echo(f"Error retrieving recent requests: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
