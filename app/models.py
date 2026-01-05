import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import SYNCHRONOUS


@dataclass
class RequestLogEntry:
    """Data class for request log entries"""

    ip_address: str
    domain: str
    http_status: int
    dnssec_status: str  # valid, invalid, error
    source: str  # api, webapp
    user_agent: Optional[str] = None
    timestamp: Optional[datetime] = None


class InfluxDBLogger:
    """InfluxDB client for logging requests and analytics"""

    def __init__(self):
        self.url = os.getenv("INFLUX_URL", "http://localhost:8086")
        self.token = os.getenv("INFLUX_TOKEN", "dev-token")
        self.org = os.getenv("INFLUX_ORG", "dnssec-validator")
        self.bucket = os.getenv("INFLUX_BUCKET", "requests")

        # Initialize client (will be lazy-loaded)
        self._client = None
        self._write_api = None
        self._query_api = None

    @property
    def client(self) -> InfluxDBClient:
        """Lazy-load InfluxDB client"""
        if self._client is None:
            try:
                self._client = InfluxDBClient(
                    url=self.url, token=self.token, org=self.org
                )
                # Test connection
                health = self._client.health()
                if health.status != "pass":
                    print(f"InfluxDB health check failed: {health.message}")
            except Exception as e:
                print(f"Failed to connect to InfluxDB: {e}")
                self._client = None
        return self._client

    @property
    def write_api(self):
        """Get write API"""
        if self._write_api is None and self.client:
            self._write_api = self.client.write_api(write_options=SYNCHRONOUS)
        return self._write_api

    @property
    def query_api(self) -> Optional[QueryApi]:
        """Get query API"""
        if self._query_api is None and self.client:
            self._query_api = self.client.query_api()
        return self._query_api

    def log_request(
        self,
        ip_address: str,
        domain: str,
        http_status: int,
        dnssec_status: str,
        source: str,
        user_agent: str = None,
        internal: bool = False,
        client: str = None,
        request_type: str = None,
    ) -> bool:
        """Log a request to InfluxDB
        client: optional tag to distinguish 'webapp' vs 'external' for API calls
        request_type: optional tag to distinguish 'basic' vs 'detailed' analysis
        """
        try:
            if not self.write_api:
                print("InfluxDB write API not available")
                return False

            # Normalize client tag
            client_tag = (client or "external").lower()
            if client_tag not in ["webapp", "external"]:
                client_tag = "external"

            # Create point for time-series data
            point = (
                Point("request")
                .tag("domain", domain)
                .tag("source", source)
                .tag("client", client_tag)
                .tag("dnssec_status", dnssec_status)
                .tag("ip_address", ip_address)
                .tag("internal", str(internal).lower())  # Add internal tag
                .field("http_status", http_status)
                .field("count", 1)
            )

            # Add request_type tag if provided (basic vs detailed analysis)
            if request_type:
                point = point.tag("request_type", request_type)

            # Add user agent as field if provided (can be large)
            if user_agent:
                point = point.field("user_agent", user_agent[:500])  # Limit length

            # Write point to InfluxDB
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True

        except Exception as e:
            print(f"Error logging request to InfluxDB: {e}")
            return False

    def _execute_query(self, flux_query: str) -> List[Dict[str, Any]]:
        """Execute Flux query and return results"""
        try:
            if not self.query_api:
                return []

            tables = self.query_api.query(flux_query, org=self.org)
            results = []

            for table in tables:
                for record in table.records:
                    results.append(record.values)

            return results

        except Exception as e:
            print(f"Error executing query: {e}")
            return []

    def get_requests_count(
        self,
        hours: int = None,
        days: int = None,
        source: str = None,
        include_internal: bool = True,
    ) -> int:
        """Get request count for specified time period"""
        try:
            # Build time range
            if hours:
                time_range = f"-{hours}h"
            elif days:
                time_range = f"-{days}d"
            else:
                time_range = "-30d"  # Default to 30 days

            # Build query
            flux_query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: {time_range})
                |> filter(fn: (r) => r._measurement == "request")
                |> filter(fn: (r) => r._field == "count")
                |> filter(fn: (r) => r.domain != "unknown")
            """

            # Filter out internal requests for stats dashboard
            if not include_internal:
                flux_query += '|> filter(fn: (r) => r.internal == "false")'

            # Add source filter if specified
            if source:
                flux_query += f'|> filter(fn: (r) => r.source == "{source}")'

            # Collapse all series and sum
            flux_query += "|> group() |> sum()"

            results = self._execute_query(flux_query)
            total = 0
            for r in results:
                try:
                    total += int(r.get("_value", 0))
                except Exception:
                    pass
            return total

        except Exception as e:
            print(f"Error getting requests count: {e}")
            return 0

    def get_top_domains(
        self,
        limit: int = 20,
        days: int = None,
        hours: int = None,
        include_internal: bool = True,
        source: str = "api",
    ) -> List[tuple]:
        """Get most frequently validated domains"""
        try:
            time_range = f"-{hours}h" if hours else (f"-{days}d" if days else "-30d")

            flux_query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: {time_range})
                |> filter(fn: (r) => r._measurement == "request")
                |> filter(fn: (r) => r._field == "count")
                |> filter(fn: (r) => r.domain != "unknown")
            """

            # Filter out internal requests for stats dashboard
            if not include_internal:
                flux_query += '|> filter(fn: (r) => r.internal == "false")'

            # Only API validations for top domains by default
            if source:
                flux_query += f'|> filter(fn: (r) => r.source == "{source}")'

            flux_query += f"""
                |> group(columns: ["domain"])
                |> sum()
                |> group()
                |> sort(columns: ["_value"], desc: true)
                |> limit(n: {limit})
            """

            results = self._execute_query(flux_query)
            return [(r.get("domain"), int(r.get("_value", 0))) for r in results]

        except Exception as e:
            print(f"Error getting top domains: {e}")
            return []

    def get_validation_ratio(
        self,
        days: int = None,
        hours: int = None,
        include_internal: bool = True,
        source: str = "api",
    ) -> Dict[str, Any]:
        """Get ratio of valid vs invalid vs error validations.
        Percentages are computed excluding 'error' from the denominator (valid+invalid).
        """
        try:
            time_range = f"-{hours}h" if hours else (f"-{days}d" if days else "-30d")

            flux_query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: {time_range})
                |> filter(fn: (r) => r._measurement == "request")
                |> filter(fn: (r) => r._field == "count")
                |> filter(fn: (r) => r.domain != "unknown")
            """

            # Filter out internal requests for stats dashboard
            if not include_internal:
                flux_query += '|> filter(fn: (r) => r.internal == "false")'

            # Only API by default
            if source:
                flux_query += f'|> filter(fn: (r) => r.source == "{source}")'

            flux_query += '|> group(columns: ["dnssec_status"]) |> sum()'

            results = self._execute_query(flux_query)

            totals = (
                {r.get("dnssec_status"): int(r.get("_value", 0)) for r in results}
                if results
                else {}
            )
            v = totals.get("valid", 0)
            inv = totals.get("invalid", 0)
            err = totals.get("error", 0)
            total_count = v + inv + err
            denom = v + inv

            ratios = {
                "total": total_count,
                "valid": {
                    "count": v,
                    "percentage": round((v / denom) * 100, 1) if denom > 0 else 0,
                },
                "invalid": {
                    "count": inv,
                    "percentage": round((inv / denom) * 100, 1) if denom > 0 else 0,
                },
                "error": {"count": err, "percentage": 0},
            }
            return ratios

        except Exception as e:
            print(f"Error getting validation ratio: {e}")
            return {"total": 0}

    def get_hourly_requests(
        self,
        hours: int = 24,
        include_internal: bool = True,
        window_every: str = "1h",
        source: str = "api",
    ) -> List[tuple]:
        """Get request counts aggregated by a dynamic window. Returns list of (ISO timestamp, count)."""
        try:
            flux_query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: -{hours}h)
                |> filter(fn: (r) => r._measurement == "request")
                |> filter(fn: (r) => r._field == "count")
                |> filter(fn: (r) => r.domain != "unknown")
            """

            # Filter out internal requests for stats dashboard
            if not include_internal:
                flux_query += '|> filter(fn: (r) => r.internal == "false")'

            # Only API by default
            if source:
                flux_query += f'|> filter(fn: (r) => r.source == "{source}")'

            flux_query += f"""
                |> drop(columns: ["domain", "dnssec_status", "ip_address", "_measurement", "_field"])
                |> group()
                |> aggregateWindow(every: {window_every}, fn: sum, createEmpty: false)
                |> yield()
            """

            results = self._execute_query(flux_query)
            series = []
            for r in results:
                if r.get("_time"):
                    ts = r.get("_time").isoformat()
                    value = int(r.get("_value", 0))
                    series.append((ts, value))
            # Sort by timestamp
            return sorted(series, key=lambda x: x[0])

        except Exception as e:
            print(f"Error getting hourly requests: {e}")
            return []

    def get_source_breakdown(self, days: int = None, hours: int = None) -> List[tuple]:
        """Get breakdown of API usage 'external' vs 'webapp' via client tag for API-only requests"""
        try:
            time_range = f"-{hours}h" if hours else (f"-{days}d" if days else "-30d")

            flux_query = f"""
                from(bucket: "{self.bucket}")
                |> range(start: {time_range})
                |> filter(fn: (r) => r._measurement == "request")
                |> filter(fn: (r) => r._field == "count")
                |> filter(fn: (r) => r.source == "api")
                |> group(columns: ["client"])
                |> sum()
            """

            results = self._execute_query(flux_query)
            return [
                (r.get("client") or "external", int(r.get("_value", 0)))
                for r in results
            ]

        except Exception as e:
            print(f"Error getting source breakdown: {e}")
            return []

    def cleanup_old_logs(self, days: int = None) -> int:
        """InfluxDB handles retention automatically, but we can delete old data manually"""
        # InfluxDB 2.x uses retention policies automatically
        # This is mainly for compatibility with the CLI interface
        print(
            f"InfluxDB retention is handled automatically. Configured for {days or '90'} days."
        )
        return 0

    def truncate_database(self) -> bool:
        """Truncate all data from the bucket (dangerous operation)"""
        try:
            if not self.client:
                print("InfluxDB client not available")
                return False

            # Delete all data from bucket using delete API
            from datetime import datetime, timezone
            import urllib.parse

            # Get the delete API
            delete_api = self.client.delete_api()

            # Delete all data from the bucket (from beginning of time to now)
            start_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
            stop_time = datetime.now(timezone.utc)

            delete_api.delete(
                start=start_time, stop=stop_time, bucket=self.bucket, org=self.org
            )

            print(f"Successfully truncated all data from bucket '{self.bucket}'")
            return True

        except Exception as e:
            print(f"Error truncating database: {e}")
            return False

    def recreate_database(self, version: str = None) -> bool:
        """Recreate the database/bucket with optional version tagging"""
        try:
            if not self.client:
                print("InfluxDB client not available")
                return False

            # Get the buckets API
            buckets_api = self.client.buckets_api()

            try:
                # Try to get existing bucket
                existing_bucket = buckets_api.find_bucket_by_name(self.bucket)
                if existing_bucket:
                    print(f"Found existing bucket '{self.bucket}', deleting...")
                    buckets_api.delete_bucket(existing_bucket)
                    print(f"Deleted bucket '{self.bucket}'")
            except Exception as e:
                print(f"Bucket '{self.bucket}' not found or already deleted: {e}")

            # Create new bucket
            from influxdb_client import BucketRetentionRules

            # Set up retention rules (default 90 days)
            retention_rules = BucketRetentionRules(
                type="expire", every_seconds=90 * 24 * 60 * 60  # 90 days in seconds
            )

            # Create bucket description with version if provided
            description = f"DNSSEC Validator request logs"
            if version:
                description += f" (Schema version: {version})"

            new_bucket = buckets_api.create_bucket(
                bucket_name=self.bucket,
                retention_rules=retention_rules,
                org=self.org,
                description=description,
            )

            print(
                f"Successfully recreated bucket '{self.bucket}' with ID: {new_bucket.id}"
            )
            if version:
                print(f"Schema version: {version}")

            return True

        except Exception as e:
            print(f"Error recreating database: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the current database/bucket"""
        try:
            if not self.client:
                return {"error": "InfluxDB client not available"}

            buckets_api = self.client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(self.bucket)

            if not bucket:
                return {"error": f"Bucket {self.bucket} not found"}

            # Get bucket statistics
            info = {
                "bucket_name": bucket.name,
                "bucket_id": bucket.id,
                "description": bucket.description,
                "created_at": (
                    bucket.created_at.isoformat() if bucket.created_at else None
                ),
                "updated_at": (
                    bucket.updated_at.isoformat() if bucket.updated_at else None
                ),
                "retention_rules": [],
                "org": self.org,
            }

            # Add retention rules info
            if bucket.retention_rules:
                for rule in bucket.retention_rules:
                    info["retention_rules"].append(
                        {
                            "type": rule.type,
                            "every_seconds": rule.every_seconds,
                            "days": (
                                rule.every_seconds // (24 * 60 * 60)
                                if rule.every_seconds
                                else None
                            ),
                        }
                    )

            return info

        except Exception as e:
            return {"error": f"Error getting database info: {e}"}

    def close(self):
        """Close InfluxDB client connection"""
        if self._client:
            self._client.close()


# Global instance
influx_logger = InfluxDBLogger()


# Compatibility layer for existing code
class RequestLog:
    """Compatibility layer for SQLAlchemy-style interface"""

    @classmethod
    def log_request(
        cls,
        ip_address: str,
        domain: str,
        http_status: int,
        dnssec_status: str,
        source: str,
        user_agent: str = None,
    ) -> bool:
        return influx_logger.log_request(
            ip_address, domain, http_status, dnssec_status, source, user_agent
        )

    @classmethod
    def get_requests_count(
        cls, hours: int = None, days: int = None, source: str = None
    ) -> int:
        return influx_logger.get_requests_count(hours, days, source)

    @classmethod
    def get_top_domains(cls, limit: int = 20, days: int = None) -> List[tuple]:
        return influx_logger.get_top_domains(limit, days)

    @classmethod
    def get_validation_ratio(cls, days: int = None) -> Dict[str, Any]:
        return influx_logger.get_validation_ratio(days)

    @classmethod
    def get_hourly_requests(cls, hours: int = 24) -> List[tuple]:
        return influx_logger.get_hourly_requests(hours)

    @classmethod
    def get_source_breakdown(cls, days: int = None, hours: int = None) -> List[tuple]:
        return influx_logger.get_source_breakdown(days=days, hours=hours)

    @classmethod
    def cleanup_old_logs(cls, days: int = None) -> int:
        return influx_logger.cleanup_old_logs(days)

    # External-only methods for stats dashboard (filters out internal requests)
    @classmethod
    def get_external_requests_count(
        cls, hours: int = None, days: int = None, source: str = None
    ) -> int:
        return influx_logger.get_requests_count(
            hours, days, source, include_internal=False
        )

    @classmethod
    def get_external_top_domains(
        cls, limit: int = 20, days: int = None, hours: int = None
    ) -> List[tuple]:
        return influx_logger.get_top_domains(
            limit, days=days, hours=hours, include_internal=False, source="api"
        )

    @classmethod
    def get_external_validation_ratio(
        cls, days: int = None, hours: int = None
    ) -> Dict[str, Any]:
        return influx_logger.get_validation_ratio(
            days=days, hours=hours, include_internal=False, source="api"
        )

    @classmethod
    def get_external_hourly_requests(
        cls, hours: int = 24, window_every: str = "1h"
    ) -> List[tuple]:
        return influx_logger.get_hourly_requests(
            hours, include_internal=False, window_every=window_every, source="api"
        )
