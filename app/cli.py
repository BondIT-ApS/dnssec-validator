#!/usr/bin/env python3
"""
CLI commands for DNSSEC Validator database management
"""

import os
import sys
import click
from flask import Flask
from models import db, RequestLog

def create_app():
    """Create Flask app for CLI operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dnssec_validator.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

@click.group()
def cli():
    """DNSSEC Validator CLI commands"""
    pass

@cli.command()
@click.option('--days', default=90, help='Delete logs older than N days (default: 90)')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
def cleanup_logs(days, dry_run):
    """Clean up old request logs from the database"""
    app = create_app()
    
    with app.app_context():
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Count logs to be deleted
            count = RequestLog.query.filter(RequestLog.timestamp < cutoff_date).count()
            
            if count == 0:
                click.echo(f"No logs older than {days} days found.")
                return
            
            if dry_run:
                click.echo(f"DRY RUN: Would delete {count} log entries older than {days} days (before {cutoff_date})")
                return
            
            # Perform actual cleanup
            deleted = RequestLog.cleanup_old_logs(days)
            click.echo(f"Successfully deleted {deleted} log entries older than {days} days")
            
        except Exception as e:
            click.echo(f"Error during cleanup: {e}", err=True)
            sys.exit(1)

@cli.command()
def init_db():
    """Initialize the database tables"""
    app = create_app()
    
    with app.app_context():
        try:
            db.create_all()
            click.echo("Database tables created successfully")
        except Exception as e:
            click.echo(f"Error creating database tables: {e}", err=True)
            sys.exit(1)

@cli.command()
def stats():
    """Show database statistics"""
    app = create_app()
    
    with app.app_context():
        try:
            total_requests = RequestLog.query.count()
            last_hour = RequestLog.get_requests_count(hours=1)
            last_day = RequestLog.get_requests_count(days=1)
            last_week = RequestLog.get_requests_count(days=7)
            
            api_requests = RequestLog.get_requests_count(source='api')
            webapp_requests = RequestLog.get_requests_count(source='webapp')
            
            click.echo("\n=== DNSSEC Validator Statistics ===")
            click.echo(f"Total requests: {total_requests}")
            click.echo(f"Last hour:      {last_hour}")
            click.echo(f"Last 24 hours:  {last_day}")
            click.echo(f"Last 7 days:    {last_week}")
            click.echo(f"API requests:   {api_requests}")
            click.echo(f"Web requests:   {webapp_requests}")
            
            # Top domains
            top_domains = RequestLog.get_top_domains(limit=10, days=30)
            if top_domains:
                click.echo("\n=== Top 10 Domains (Last 30 days) ===")
                for domain, count in top_domains:
                    click.echo(f"{domain}: {count} requests")
            
            # Validation ratio
            ratio = RequestLog.get_validation_ratio(days=30)
            if ratio.get('total', 0) > 0:
                click.echo(f"\n=== Validation Results (Last 30 days) ===")
                for status in ['valid', 'invalid', 'error']:
                    if status in ratio:
                        click.echo(f"{status.capitalize()}: {ratio[status]['count']} ({ratio[status]['percentage']}%)")
            
        except Exception as e:
            click.echo(f"Error retrieving statistics: {e}", err=True)
            sys.exit(1)

@cli.command()
@click.option('--hours', default=24, help='Show requests from last N hours (default: 24)')
def recent_requests(hours):
    """Show recent requests"""
    app = create_app()
    
    with app.app_context():
        try:
            from datetime import datetime, timedelta
            since = datetime.utcnow() - timedelta(hours=hours)
            
            recent = RequestLog.query.filter(
                RequestLog.timestamp >= since
            ).order_by(RequestLog.timestamp.desc()).limit(20).all()
            
            if not recent:
                click.echo(f"No requests found in the last {hours} hours.")
                return
            
            click.echo(f"\n=== Recent Requests (Last {hours} hours) ===")
            click.echo("Timestamp                Domain                  IP              Status  Source")
            click.echo("-" * 80)
            
            for req in recent:
                timestamp = req.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                domain = req.domain[:20].ljust(20)
                ip = req.ip_address[:15].ljust(15)
                status = f"{req.http_status}/{req.dnssec_status}".ljust(8)
                source = req.source.ljust(6)
                click.echo(f"{timestamp} {domain} {ip} {status} {source}")
            
        except Exception as e:
            click.echo(f"Error retrieving recent requests: {e}", err=True)
            sys.exit(1)

if __name__ == '__main__':
    cli()
