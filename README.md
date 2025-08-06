# DNSSEC Validator

[![Docker Image Version](https://img.shields.io/docker/v/maboni82/dnssec-validator?style=for-the-badge&logo=docker)](https://hub.docker.com/r/maboni82/dnssec-validator)
[![Docker Pulls](https://img.shields.io/docker/pulls/maboni82/dnssec-validator?style=for-the-badge&logo=docker)](https://hub.docker.com/r/maboni82/dnssec-validator)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/BondIT-ApS/dnssec-validator/docker-publish.yml?branch=master&style=for-the-badge&logo=github)](https://github.com/BondIT-ApS/dnssec-validator/actions)
[![GitHub Issues](https://img.shields.io/github/issues/BondIT-ApS/dnssec-validator?style=for-the-badge)](https://github.com/BondIT-ApS/dnssec-validator/issues)
[![GitHub Stars](https://img.shields.io/github/stars/BondIT-ApS/dnssec-validator?style=for-the-badge)](https://github.com/BondIT-ApS/dnssec-validator/stargazers)
[![License](https://img.shields.io/github/license/BondIT-ApS/dnssec-validator?style=for-the-badge)](https://github.com/BondIT-ApS/dnssec-validator/blob/master/LICENSE)
[![Security Rating](https://img.shields.io/badge/security-A%2B-green?style=for-the-badge&logo=shield)](https://github.com/BondIT-ApS/dnssec-validator/security)

A **professional-grade** web-based DNSSEC validation tool that provides comprehensive analysis of DNS Security Extensions (DNSSEC) for any domain. This tool validates the complete chain of trust from root servers down to your domain, similar to Verisign's DNSSEC Debugger but with modern architecture and enhanced features.

## 🚀 Features

- **Complete Chain of Trust Validation**: Traces DNSSEC validation from root (.) → TLD → domain
- **Real-time Analysis**: Live DNS queries with detailed step-by-step validation
- **Visual Interface**: Clean web UI showing validation results with color-coded status
- **API Endpoint**: RESTful API for programmatic access
- **Docker Support**: Easy deployment with Docker containers
- **Multi-Algorithm Support**: Supports all DNSSEC algorithms (RSA, ECDSA, EdDSA)
- **Detailed Reporting**: Shows DNSKEY, DS, RRSIG records with validation status

## 🌐 Live Demo

🎉 **Try the live version at: [https://dnssec-validator.bondit.dk](https://dnssec-validator.bondit.dk)**

The production deployment includes:
- ✅ HTTPS with SSL/TLS encryption
- ✅ Professional domain and hosting
- ✅ High availability and monitoring
- ✅ Full API documentation at `/api/docs/`

## 🐳 Quick Start with Docker

```bash
# Run the container
docker run -p 8080:8080 maboni82/dnssec-validator:latest

# Open your browser to http://localhost:8080
```

## 🔧 Manual Installation

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/BondIT-ApS/dnssec-validator.git
cd dnssec-validator
pip install -r requirements.txt
python app.py
```

Open your browser to `http://localhost:8080`

## 📖 Usage

### Web Interface

1. Navigate to the web interface
2. Enter a domain name (e.g., `bondit.dk`)
3. Click "Validate DNSSEC"
4. View the detailed validation report

### API Usage

#### DNSSEC Validation

```bash
# Validate a domain via API
curl "http://localhost:8080/api/validate/bondit.dk"

# Response format
{
  "domain": "bondit.dk",
  "status": "valid",
  "chain_of_trust": [
    {
      "zone": ".",
      "status": "valid",
      "algorithm": 8,
      "key_tag": 20326
    },
    {
      "zone": "dk.",
      "status": "valid", 
      "algorithm": 13,
      "key_tag": 20109
    },
    {
      "zone": "bondit.dk.",
      "status": "valid",
      "algorithm": 13,
      "key_tag": 48993
    }
  ],
  "records": {
    "dnskey": [...],
    "ds": [...],
    "rrsig": [...]
  }
}
```

#### Health Check Endpoints

The application provides dedicated health check endpoints for monitoring and container orchestration:

```bash
# Detailed health check (JSON response)
curl "http://localhost:8080/health"

# Response format
{
  "status": "healthy",
  "timestamp": "2025-08-06T07:23:12Z",
  "version": "1.0.0",
  "checks": {
    "application": "ok",
    "dns_resolver": "ok",
    "memory_usage": "ok"
  },
  "uptime": "2h 15m 32s"
}

# Simple health check (plain text response)
curl "http://localhost:8080/health/simple"
# Response: "healthy"
```

**Health Status Levels:**
- `healthy`: All systems operational (HTTP 200)
- `degraded`: Some non-critical issues detected (HTTP 200) 
- `unhealthy`: Critical issues affecting functionality (HTTP 503)

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "User Interface"
        WEB["🌐 Web Frontend<br/>(HTML/CSS/JS)"]
        API["🔌 REST API<br/>(/api/validate)"]
    end
    
    subgraph "Application Layer"
        FLASK["🐍 Flask App<br/>(Python)"]
        ENGINE["🔒 DNSSEC Engine<br/>(dnspython)"]
    end
    
    subgraph "External Services"
        DNS["🌍 DNS Servers<br/>(Root, TLD, Authoritative)"]
        VALIDATION["✅ DNSSEC Validation<br/>(Chain of Trust)"]
    end
    
    WEB --> FLASK
    API --> FLASK
    FLASK --> ENGINE
    ENGINE --> DNS
    ENGINE --> VALIDATION
    
    style WEB fill:#e1f5fe
    style API fill:#e8f5e8
    style FLASK fill:#fff3e0
    style ENGINE fill:#fce4ec
    style DNS fill:#f3e5f5
    style VALIDATION fill:#e0f2f1
```

## 🔍 What It Validates

- **Root Trust Anchor**: Validates against IANA root trust anchors
- **DS Records**: Checks Delegation Signer records in parent zones
- **DNSKEY Records**: Validates public keys and algorithms
- **RRSIG Records**: Verifies cryptographic signatures
- **Chain Continuity**: Ensures unbroken chain from root to domain
- **Algorithm Support**: Validates RSA/SHA-1, RSA/SHA-256, ECDSA P-256, ECDSA P-384, Ed25519

## 📂 Project Structure

```
dnssec-validator/
├── app.py                 # Flask web application
├── dnssec_validator.py    # Core DNSSEC validation logic
├── static/
│   ├── css/
│   │   └── style.css     # Web interface styling
│   └── js/
│       └── app.js        # Frontend JavaScript
├── templates/
│   └── index.html        # Main web interface
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker container definition
├── docker-compose.yml    # Docker Compose setup
└── README.md            # This file
```

## 🧪 Development

### Running Tests

```bash
python -m pytest tests/
```

### Development Mode

```bash
export FLASK_ENV=development
python app.py
```

## 🚀 Deployment

### Docker

```bash
# Build the image
docker build -t dnssec-validator .

# Run the container
docker run -p 8080:8080 dnssec-validator
```

### Docker Compose

```bash
docker-compose up -d
```

### Cloud Deployment

The application can be deployed to:
- **Heroku**: `heroku create your-app-name`
- **Google Cloud Run**: `gcloud run deploy`
- **AWS ECS**: Using the provided Dockerfile
- **Kubernetes**: Using the provided manifests

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Run tests: `python -m pytest`
6. Submit a pull request

## 📋 Todo / Roadmap

- [ ] [Add support for CAA record validation](https://github.com/BondIT-ApS/dnssec-validator/issues/35)
- [ ] [Implement TLSA record checking](https://github.com/BondIT-ApS/dnssec-validator/issues/34)
- [ ] [Create batch validation API](https://github.com/BondIT-ApS/dnssec-validator/issues/32)
- [ ] [Add database for request logging and monitoring](https://github.com/BondIT-ApS/dnssec-validator/issues/33)
- [ ] [Implement caching for faster responses](https://github.com/BondIT-ApS/dnssec-validator/issues/36)
- [ ] [Add support for internationalized domain names (IDN)](https://github.com/BondIT-ApS/dnssec-validator/issues/37)

## 🛡️ Rate Limiting

The DNSSEC Validator includes comprehensive rate limiting to ensure fair usage and prevent abuse. Rate limits are applied per IP address and are configurable via environment variables.

### Default Rate Limits

| Endpoint Type | Limit | Description |
|---------------|-------|-------------|
| **Global** | 5000/day, 500/hour | Overall requests per IP across all endpoints |
| **API** | 100/minute, 1000/hour | REST API endpoints (`/api/validate/*`) |
| **Web Interface** | 50/minute, 500/hour | Web UI and direct domain URLs |

### Configuration

Rate limits can be customized using environment variables:

```bash
# Global rate limits (applied to all requests)
RATE_LIMIT_GLOBAL_DAY=5000    # Requests per IP per day
RATE_LIMIT_GLOBAL_HOUR=500    # Requests per IP per hour

# API-specific rate limits
RATE_LIMIT_API_MINUTE=100     # API requests per IP per minute
RATE_LIMIT_API_HOUR=1000      # API requests per IP per hour

# Web interface rate limits
RATE_LIMIT_WEB_MINUTE=50      # Web requests per IP per minute
RATE_LIMIT_WEB_HOUR=500       # Web requests per IP per hour
```

### Docker Compose Example

```yaml
services:
  dnssec-validator:
    build: .
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      # Custom rate limits for high-traffic deployment
      - RATE_LIMIT_GLOBAL_DAY=500
      - RATE_LIMIT_GLOBAL_HOUR=100
      - RATE_LIMIT_API_MINUTE=15
      - RATE_LIMIT_API_HOUR=150
      - RATE_LIMIT_WEB_MINUTE=30
      - RATE_LIMIT_WEB_HOUR=300
```

### Rate Limit Responses

When rate limits are exceeded:

**API Endpoints** return structured JSON:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded",
    "details": {
      "limit": "10 per 1 minute",
      "retry_after": 45,
      "reset_time": "2024-01-15T14:30:00Z"
    }
  }
}
```

**Web Interface** shows a user-friendly error page with:
- Current rate limit information
- Time until limit resets
- Suggestions for API usage for automated tools

### Production Recommendations

For production deployments:

```bash
# Conservative limits for public services
RATE_LIMIT_GLOBAL_DAY=1000
RATE_LIMIT_GLOBAL_HOUR=100
RATE_LIMIT_API_MINUTE=5
RATE_LIMIT_API_HOUR=50
RATE_LIMIT_WEB_MINUTE=10
RATE_LIMIT_WEB_HOUR=100

# More generous limits for internal/enterprise use
RATE_LIMIT_GLOBAL_DAY=5000
RATE_LIMIT_GLOBAL_HOUR=500
RATE_LIMIT_API_MINUTE=30
RATE_LIMIT_API_HOUR=1000
RATE_LIMIT_WEB_MINUTE=50
RATE_LIMIT_WEB_HOUR=1000
```

## 🏥 Health Monitoring

The DNSSEC Validator includes comprehensive health monitoring capabilities designed for container orchestration and monitoring systems.

### Health Check Endpoints

| Endpoint | Purpose | Response Format | Rate Limited |
|----------|---------|-----------------|-------------|
| `/health` | Detailed health status | JSON | No |
| `/health/simple` | Basic health check | Plain text | No |

### Health Check Configuration

Health monitoring behavior can be customized using environment variables:

```bash
# Health check configuration
HEALTH_CHECK_ENABLED=true          # Enable/disable detailed health checks
HEALTH_CHECK_DNS_TEST=true         # Test DNS resolution capability
HEALTH_CHECK_MEMORY_THRESHOLD=90   # Memory usage warning threshold (%)
```

### Docker Health Check Integration

Both Docker Compose configurations include health checks:

**Development (docker-compose.yml):**
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

**Production (docker-compose.prod.yml):**
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Health Check Components

The detailed health endpoint (`/health`) monitors:

1. **Application Status**: Basic Flask app responsiveness
2. **DNS Resolver**: Tests ability to resolve DNS queries (`example.com`)
3. **Memory Usage**: Monitors system memory consumption
4. **Uptime**: Tracks application runtime since startup

### Container Orchestration Benefits

- **Portainer**: Visual health status indicators in container overview
- **Docker Swarm**: Automatic container replacement on health failures
- **Kubernetes**: Readiness and liveness probe compatibility
- **Load Balancers**: Health-based traffic routing decisions
- **Monitoring Tools**: Integration with Prometheus, Grafana, etc.

### Monitoring Integration Examples

**Prometheus scraping configuration:**
```yaml
scrape_configs:
  - job_name: 'dnssec-validator'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/health'
    scrape_interval: 30s
```

**Kubernetes liveness probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health/simple
    port: 8080
  initialDelaySeconds: 60
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
```

## ⚠️ Security Considerations

- This tool performs live DNS queries to validate DNSSEC
- No domain data is stored or logged
- All validation is performed server-side
- Comprehensive rate limiting prevents abuse and ensures fair usage
- Security headers (CSP, HSTS) protect against common web vulnerabilities
- CORS configuration restricts cross-origin requests in production

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/BondIT-ApS/dnssec-validator/issues)
- **Documentation**: Full API documentation available at `/docs` when running
- **Community**: Join our discussions in [GitHub Discussions](https://github.com/BondIT-ApS/dnssec-validator/discussions)

## 🏢 About BondIT ApS

This project is maintained and developed by [BondIT ApS](https://bondit.dk), a Scandinavian IT consultancy specializing in secure web applications and infrastructure solutions. Just like our fellow Danish company LEGO, we believe in building things one brick at a time – except our bricks are lines of code, and instead of stepping on them barefoot at 3 AM, you'll actually enjoy using what we build! 🧱💻

---

**Made with ❤️ by BondIT ApS**
