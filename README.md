# DNSSEC Validator

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/BondIT-ApS/dnssec-validator/docker-publish.yml?branch=main&style=for-the-badge&logo=github)](https://github.com/BondIT-ApS/dnssec-validator/actions)
[![License](https://img.shields.io/github/license/BondIT-ApS/dnssec-validator?style=for-the-badge)](https://github.com/BondIT-ApS/dnssec-validator/blob/main/LICENSE)
[![GitHub repo size](https://img.shields.io/github/repo-size/BondIT-ApS/dnssec-validator?style=for-the-badge)](https://github.com/BondIT-ApS/dnssec-validator)
[![Made in Denmark](https://img.shields.io/badge/Made%20in-Denmark-red?style=for-the-badge)](https://bondit.dk)
[![codecov](https://img.shields.io/codecov/c/github/BondIT-ApS/dnssec-validator?style=for-the-badge&logo=codecov)](https://codecov.io/gh/BondIT-ApS/dnssec-validator)

[![Docker Pulls](https://img.shields.io/docker/pulls/maboni82/dnssec-validator?style=for-the-badge&logo=docker)](https://hub.docker.com/r/maboni82/dnssec-validator)
[![GitHub Release](https://img.shields.io/github/v/release/BondIT-ApS/dnssec-validator?style=for-the-badge&logo=github&label=release)](https://github.com/BondIT-ApS/dnssec-validator/releases/latest)

> 🧱 **Building DNS Security Solutions, One Brick at a Time** 🔒

A **professional-grade** web-based DNSSEC validation tool that validates the complete chain of trust from root servers down to your domain. Similar to Verisign's DNSSEC Debugger but with modern architecture, Docker support, and comprehensive monitoring.

## 🧱 Foundation Pieces (Features)

- ✅ **Complete Chain of Trust** - Validates from root (.) → TLD → domain
- ✅ **Visual Web Interface** - Clean UI with color-coded validation status
- ✅ **RESTful API** - Programmatic access for automation
- ✅ **Docker Ready** - Easy deployment with official Docker images
- ✅ **Smart Input** - Accepts domains or URLs with automatic parsing
- ✅ **Health Monitoring** - Built-in health checks for orchestration
- ✅ **Rate Limiting** - Configurable limits for production use
- ✅ **Analytics** - Optional InfluxDB integration for request logging
- ✅ **Google Analytics** - Optional GA4 tracking with GDPR-compliant cookie consent

## 🌐 Live Demo

**Try it now: [https://dnssec-validator.bondit.dk](https://dnssec-validator.bondit.dk)**

## 🚀 Quick Assembly (Quick Start)

```bash
# Run with Docker
docker run -p 8080:8080 maboni82/dnssec-validator:latest

# Open browser
open http://localhost:8080
```

That's it! The validator is now running.

## 📖 Basic Usage

### Web Interface

1. Navigate to `http://localhost:8080`
2. Enter a domain (e.g., `bondit.dk`)
3. Click "Validate DNSSEC"
4. View detailed validation results

### API

```bash
# Validate a domain
curl http://localhost:8080/api/validate/bondit.dk

# Response includes chain of trust and DNSSEC records
```

## 📦 Assembly Instructions (Installation)

### Docker (Recommended)

```bash
# Pull and run latest version
docker pull maboni82/dnssec-validator:latest
docker run -d -p 8080:8080 --name dnssec-validator maboni82/dnssec-validator:latest
```

### Docker Compose

```bash
# Clone repository
git clone https://github.com/BondIT-ApS/dnssec-validator.git
cd dnssec-validator

# Start with compose
docker-compose up -d
```

### Manual Installation

```bash
# Requires Python 3.13+
git clone https://github.com/BondIT-ApS/dnssec-validator.git
cd dnssec-validator
pip install -r requirements.txt
python app/app.py
```

📚 **See [Installation Guide](documentation/installation.md) for detailed options**

## 🔧 Configuration

Configure via environment variables:

```bash
# Rate limiting
RATE_LIMIT_GLOBAL_DAY=5000
RATE_LIMIT_API_MINUTE=200

# Health checks
HEALTH_CHECK_ENABLED=true

# InfluxDB analytics (optional)
REQUEST_LOGGING_ENABLED=true
INFLUX_URL=http://influxdb:8086

# Google Analytics (optional, disabled by default)
GA_ENABLED=false
GA_TRACKING_ID=G-XXXXXXXXXX
```

### Google Analytics Configuration

Optional Google Analytics 4 tracking with GDPR-compliant cookie consent:

```bash
# Enable Google Analytics
GA_ENABLED=true
GA_TRACKING_ID=G-XXXXXXXXXX  # Your GA4 tracking ID
```

**Features:**
- ✅ GDPR-compliant cookie consent banner
- ✅ Only loads GA after user accepts tracking
- ✅ User can decline tracking
- ✅ Consent preference saved in local storage
- ✅ Privacy-first approach with IP anonymization
- ✅ Disabled by default
- ✅ Automatically logs error if enabled without tracking ID

**Note:** GA is disabled by default. The application will log an error if `GA_ENABLED=true` but `GA_TRACKING_ID` is missing.

📚 **See [Configuration Reference](documentation/configuration.md) for all options**

## 📚 Documentation

Comprehensive documentation is available in the [`documentation/`](documentation/) folder:

### Getting Started
- **[Getting Started Guide](documentation/getting-started.md)** - Quick start and basic usage
- **[Installation Guide](documentation/installation.md)** - All installation methods
- **[Configuration Reference](documentation/configuration.md)** - Environment variables

### Deployment & Operations
- **[Container Orchestration](documentation/container-orchestration.md)** - Docker, Kubernetes, Swarm
- **[Health Monitoring](documentation/health-monitoring.md)** - Health checks and monitoring
- **[Rate Limiting](documentation/rate-limiting.md)** - Configuration and best practices

### Development & Technical
- **[API Reference](documentation/api-reference.md)** - Complete API documentation
- **[Architecture](documentation/architecture.md)** - System design and validation process
- **[Development Guide](documentation/development.md)** - Contributing and development setup
- **[Database & Analytics](documentation/database-analytics.md)** - InfluxDB integration

## 🏗️ Building Design (Architecture)

DNSSEC Validator validates the complete chain of trust:

```
Root (.) → TLD (.dk) → Domain (bondit.dk)
   ↓         ↓              ↓
DNSKEY → DS Record → DNSKEY + RRSIG
```

Each step is cryptographically verified using DNSSEC signatures.

📚 **See [Architecture Guide](documentation/architecture.md) for details**

## 🐳 Production Deployment

### Docker Compose

```bash
# Production deployment with compose
docker-compose -f docker-compose.prod.yml up -d
```

### Container Orchestration

For advanced deployments with Docker Swarm, Kubernetes, or Portainer, see the [Container Orchestration Guide](documentation/container-orchestration.md) which includes:

- Docker Swarm stack configurations
- Kubernetes deployment manifests
- Portainer templates
- Health check integration
- Load balancer configurations

### Health Checks

All deployments include health check endpoints:
- `/health` - Detailed JSON status
- `/health/simple` - Simple text response

📚 **See [Container Orchestration Guide](documentation/container-orchestration.md) for complete examples**

## 🤝 Join the Building Team (Contributing)

We welcome contributions! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run quality checks: `black`, `pylint`, `pytest`
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) and [Development Guide](documentation/development.md) for details.

## 🏷️ Versioning

DNSSEC Validator uses semantic versioning with `YY.M.PATCH` format:

- `26.1.0` - January 2026, first release
- `26.1.3` - January 2026, patch 3
- `26.2.0` - February 2026, first release

**Docker tags:**
- `latest` - Most recent release
- `26.1.0` - First stable release for January 2026
- `26.1` - Latest patch for January 2026
- `26.1.3` - Specific version

View all releases on the [Releases page](https://github.com/BondIT-ApS/dnssec-validator/releases).

## 📋 Building Blueprints (Roadmap)

- [ ] [CAA record validation](https://github.com/BondIT-ApS/dnssec-validator/issues/35)
- [x] [TLSA/DANE validation](https://github.com/BondIT-ApS/dnssec-validator/issues/34) ✅
- [ ] [Batch validation API](https://github.com/BondIT-ApS/dnssec-validator/issues/32)
- [x] [InfluxDB analytics](https://github.com/BondIT-ApS/dnssec-validator/issues/33) ✅
- [ ] [Response caching](https://github.com/BondIT-ApS/dnssec-validator/issues/36)
- [ ] [IDN support](https://github.com/BondIT-ApS/dnssec-validator/issues/37)

## ⚠️ Security

- Domain requests are logged for analytics (configurable retention)
- Only IP addresses and domains are stored
- Rate limiting prevents abuse
- Regular security scans with Bandit and Safety CLI
- Weekly CodeQL analysis

Report security issues via [GitHub Security Advisories](https://github.com/BondIT-ApS/dnssec-validator/security/advisories).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- **Issues**: [GitHub Issues](https://github.com/BondIT-ApS/dnssec-validator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/BondIT-ApS/dnssec-validator/discussions)
- **Documentation**: [Full documentation](documentation/)
- **API Docs**: Available at `/api/docs/` when running

## 🏢 About BondIT ApS

This project is maintained by [BondIT ApS](https://bondit.dk), a Danish IT consultancy. Like our fellow Danish company LEGO, we believe in building things methodically - except our bricks are lines of code, and you won't step on them barefoot at 3 AM! 🧱💻

---

**Made with ❤️, ☕, and 🧱 by BondIT ApS**
