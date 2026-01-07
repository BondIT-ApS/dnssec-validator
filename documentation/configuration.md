# Configuration Reference

Complete reference for all environment variables used to configure DNSSEC Validator.

## Quick Reference

| Category | Variables | Documentation |
|----------|-----------|---------------|
| **Application** | `FLASK_ENV`, `LOG_LEVEL`, `LOG_FORMAT`, `LOG_FILE` | [Details](#application-settings) |
| **Rate Limiting** | `RATE_LIMIT_GLOBAL_DAY`, `RATE_LIMIT_GLOBAL_HOUR`, `RATE_LIMIT_API_MINUTE`, `RATE_LIMIT_API_HOUR`, `RATE_LIMIT_WEB_MINUTE`, `RATE_LIMIT_WEB_HOUR` | [Details](#rate-limiting) |
| **Health Checks** | `HEALTH_CHECK_ENABLED`, `HEALTH_CHECK_DNS_TEST`, `HEALTH_CHECK_MEMORY_THRESHOLD` | [Details](#health-monitoring) |
| **Database** | `REQUEST_LOGGING_ENABLED`, `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`, `INFLUX_DB_RECREATE`, `INFLUX_DB_TRUNCATE`, `INFLUX_DB_VERSION`, `INFLUX_DB_INIT_WAIT` | [Details](#database--analytics) |
| **Security** | `CORS_ORIGINS`, `SHOW_VALIDATION_TLSA_DANE`, `SHOW_BONDIT_ATTRIBUTION` | [Details](#security--cors) |
| **InfluxDB Docker** | `DOCKER_INFLUXDB_INIT_*` | [Details](#influxdb-docker-initialization) |

## Application Settings

```bash
# Flask environment
FLASK_ENV=production              # production | development

# Logging
LOG_LEVEL=INFO                    # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=json                   # json | standard
# LOG_FILE=/app/logs/app.log      # Optional: Enable file logging (uncomment to use)
```

## Rate Limiting

```bash
# Global rate limits
RATE_LIMIT_GLOBAL_DAY=5000        # Requests per IP per day
RATE_LIMIT_GLOBAL_HOUR=1000       # Requests per IP per hour

# API rate limits
RATE_LIMIT_API_MINUTE=200         # API requests per IP per minute
RATE_LIMIT_API_HOUR=2000          # API requests per IP per hour

# Web interface rate limits
RATE_LIMIT_WEB_MINUTE=50          # Web requests per IP per minute
RATE_LIMIT_WEB_HOUR=500           # Web requests per IP per hour
```

See [Rate Limiting](rate-limiting.md) for details.

## Health Monitoring

```bash
# Health check configuration
HEALTH_CHECK_ENABLED=true         # Enable health checks
HEALTH_CHECK_DNS_TEST=true        # Enable DNS resolution test (default: true)
HEALTH_CHECK_MEMORY_THRESHOLD=90  # Memory warning threshold (%)
```

See [Health Monitoring](health-monitoring.md) for details.

## Database & Analytics

```bash
# InfluxDB settings
REQUEST_LOGGING_ENABLED=true      # Enable request logging
INFLUX_URL=http://influxdb:8086   # InfluxDB URL
INFLUX_TOKEN=your-auth-token      # InfluxDB authentication token
INFLUX_ORG=dnssec-validator       # InfluxDB organization
INFLUX_BUCKET=requests            # InfluxDB bucket name

# Database management (advanced)
INFLUX_DB_RECREATE=false          # Recreate database/bucket on startup (DANGEROUS!)
INFLUX_DB_TRUNCATE=false          # Truncate all data on startup (DANGEROUS!)
INFLUX_DB_VERSION=v2.1            # Optional schema version for tracking
INFLUX_DB_INIT_WAIT=10            # Seconds to wait for InfluxDB readiness (default: 5)
```

See [Database & Analytics](database-analytics.md) for details.

## InfluxDB Docker Initialization

These variables are only used when running InfluxDB via Docker Compose:

```bash
# InfluxDB Docker setup (for docker-compose only)
DOCKER_INFLUXDB_INIT_MODE=setup              # Setup mode for first run
DOCKER_INFLUXDB_INIT_USERNAME=admin          # Admin username
DOCKER_INFLUXDB_INIT_PASSWORD=password       # Admin password
DOCKER_INFLUXDB_INIT_ORG=dnssec-validator    # Organization name
DOCKER_INFLUXDB_INIT_BUCKET=requests         # Bucket name
DOCKER_INFLUXDB_INIT_RETENTION=30d           # Data retention period
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=auth-token  # Admin API token
```

**Note:** These are InfluxDB-specific environment variables for the InfluxDB container, not the DNSSEC Validator application.

## Security & CORS

```bash
# CORS configuration
CORS_ORIGINS=https://example.com  # Allowed origins (comma-separated)

# Feature flags
SHOW_VALIDATION_TLSA_DANE=false   # Show TLSA validation in UI
SHOW_BONDIT_ATTRIBUTION=true      # Show BondIT footer
```

## Example Configurations

### Development

```bash
FLASK_ENV=development
LOG_LEVEL=DEBUG
RATE_LIMIT_GLOBAL_DAY=10000
HEALTH_CHECK_ENABLED=true
REQUEST_LOGGING_ENABLED=true
```

### Production

```bash
FLASK_ENV=production
LOG_LEVEL=INFO
LOG_FORMAT=json
RATE_LIMIT_GLOBAL_DAY=1000
RATE_LIMIT_GLOBAL_HOUR=100
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_MEMORY_THRESHOLD=80
REQUEST_LOGGING_ENABLED=true
CORS_ORIGINS=https://dnssec-validator.bondit.dk
```

---

**📚 [Back to Documentation Index](README.md)**
