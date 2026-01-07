# Installation Guide

This guide covers all the different ways to install and run DNSSEC Validator.

## Docker Installation (Recommended)

Docker is the recommended method for running DNSSEC Validator as it provides a consistent environment and easy deployment.

### Pull and Run Latest Version

```bash
# Pull the latest image
docker pull maboni82/dnssec-validator:latest

# Run the container
docker run -d \
  -p 8080:8080 \
  --name dnssec-validator \
  --restart unless-stopped \
  maboni82/dnssec-validator:latest

# View logs
docker logs -f dnssec-validator
```

### Run Specific Version

```bash
# Run a specific version
docker run -p 8080:8080 maboni82/dnssec-validator:26.1.3

# Run latest patch of a specific month
docker run -p 8080:8080 maboni82/dnssec-validator:26.1
```

### Versioning

DNSSEC Validator uses semantic versioning with `YY.M.PATCH` format:

- **YY.M** = Year and Month (e.g., `26.1` for January 2026)
- **PATCH** = Incremental patch number (starts at 0 each month)

**Docker tags available:**
- `latest` - Always points to the most recent release
- `YY.M.0` - First stable release for the month (e.g., `26.1.0`)
- `YY.M` - Latest patch for that month (e.g., `26.1`)
- `YY.M.PATCH` - Specific version (e.g., `26.1.3`)

**Release schedule:**
- **Monthly Releases**: Created on the 1st of each month (`YY.M.0`)
- **Patch Releases**: Automatically created when PRs merge to main

View all releases on the [Releases page](https://github.com/BondIT-ApS/dnssec-validator/releases).

## Docker Compose Installation

Docker Compose is ideal for managing multi-container setups with InfluxDB for analytics.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/BondIT-ApS/dnssec-validator.git
cd dnssec-validator

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The development `docker-compose.yml` includes:
- DNSSEC Validator application
- InfluxDB for request logging (10-day retention)
- Health checks for both services
- Automatic restart policies

### Production Setup

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

The production `docker-compose.prod.yml` provides:
- Published Docker image (no local build)
- InfluxDB with 30-day retention
- Production-optimized settings
- Isolated Docker network
- JSON logging format

## Manual Installation

For development or custom deployments without Docker:

### Prerequisites

- Python 3.13+ (recommended for latest security features)
- pip package manager
- Git (for cloning repository)

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/BondIT-ApS/dnssec-validator.git
cd dnssec-validator

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app/app.py
```

The application will start on `http://localhost:8080`.

### Development Mode

```bash
# Enable development mode
export FLASK_ENV=development

# Run with debug logging
export LOG_LEVEL=DEBUG

# Start application
python app/app.py
```

## Building from Source

### Build Docker Image Locally

```bash
# Clone repository
git clone https://github.com/BondIT-ApS/dnssec-validator.git
cd dnssec-validator

# Build image
docker build -t dnssec-validator:custom .

# Run your custom build
docker run -p 8080:8080 dnssec-validator:custom
```

### Custom Dockerfile

```dockerfile
FROM python:3.13-alpine

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ .

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"

# Run application
CMD ["python", "app.py"]
```

## Verification

After installation, verify the application is running:

```bash
# Check health endpoint
curl http://localhost:8080/health/simple

# Expected response: "healthy"

# Test validation
curl http://localhost:8080/api/validate/bondit.dk

# Open web interface
open http://localhost:8080
```

## Next Steps

- **[Configuration](configuration.md)** - Configure environment variables
- **[Container Orchestration](container-orchestration.md)** - Deploy to Kubernetes, Swarm, etc.
- **[Health Monitoring](health-monitoring.md)** - Set up monitoring and health checks
- **[Database & Analytics](database-analytics.md)** - Configure InfluxDB integration

## Troubleshooting

### Port Already in Use

If port 8080 is already in use:

```bash
# Use different port
docker run -p 9090:8080 maboni82/dnssec-validator:latest
```

### Permission Denied

If you get permission errors with Docker:

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER

# Then log out and back in
```

### Python Version Issues

Ensure you're using Python 3.13+:

```bash
# Check version
python3 --version

# Install Python 3.13 (Ubuntu/Debian)
sudo apt update
sudo apt install python3.13 python3.13-venv
```

---

**📚 [Back to Documentation Index](README.md)**
