# Development Guide

This guide covers setting up a development environment and contributing to DNSSEC Validator.

## Development Setup

### Local Python Environment

```bash
# Clone repository
git clone https://github.com/BondIT-ApS/dnssec-validator.git
cd dnssec-validator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
export FLASK_ENV=development
python app/app.py
```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# View logs
docker-compose logs -f dnssec-validator
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/test_domain_utils.py
```

## Code Quality

### Pre-Commit Checks

Before committing, run:

```bash
# Format code
black app/ tests/ --line-length=88

# Lint code
pylint app/*.py --rcfile=.pylintrc

# Run tests
pytest tests/
```

### Quality Standards

- **Pylint Score**: 9.5/10 minimum (currently: 10.00/10)
- **Code Coverage**: High coverage encouraged
- **Security**: Bandit + Safety CLI scans

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests for new functionality
5. Run quality checks
6. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.

## Project Structure

See [Architecture](architecture.md) for details on the codebase structure.

---

**📚 [Back to Documentation Index](README.md)**
