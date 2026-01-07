# Database & Analytics

DNSSEC Validator includes comprehensive request logging and analytics using **InfluxDB**, a time-series database optimized for monitoring and analytics.

## InfluxDB Integration

All DNSSEC validation requests are automatically logged to InfluxDB with detailed metadata:

- **Domain validation requests** with timestamps
- **IP address tracking** for usage analytics  
- **DNSSEC validation status** (valid/invalid/error)
- **Request source tracking** (API vs web interface)
- **HTTP status codes** and user agent information
- **90-day data retention** with automatic cleanup

## Configuration

Database logging is configured via environment variables:

```bash
# Enable/disable request logging
REQUEST_LOGGING_ENABLED=true

# InfluxDB connection settings
INFLUX_URL=http://influxdb:8086
INFLUX_TOKEN=my-super-secret-auth-token
INFLUX_ORG=dnssec-validator
INFLUX_BUCKET=requests
```

## Analytics Capabilities

The logging system provides built-in analytics methods for monitoring:

- **Request count tracking** by time period (hours/days)
- **Top domains analysis** with request frequencies
- **Validation success/failure ratios** for quality monitoring
- **API vs web interface usage breakdown**
- **Hourly request patterns** for trend analysis
- **IP-based usage analytics** for rate limiting insights

## Data Structure

The InfluxDB measurement structure:

- **Organization**: `dnssec-validator`
- **Bucket**: `requests` (90-day retention)
- **Measurement**: `request`
- **Tags**: `domain`, `ip_address`, `dnssec_status`, `source`
- **Fields**: `count`, `http_status`, `user_agent`
- **Timestamp**: Automatic with nanosecond precision

For complete configuration examples, see [Container Orchestration](container-orchestration.md).

---

**📚 [Back to Documentation Index](README.md)**
