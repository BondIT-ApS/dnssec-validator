# DNSSEC Validator - Testing Documentation

## Overview
This directory contains comprehensive unit and integration tests for the DNSSEC Validator application with **53% code coverage** and **130 passing tests**. The testing framework uses `pytest` with mocking to avoid real DNS queries and network calls.

## Quick Start

```bash
# Run all tests with coverage
source .venv/bin/activate && python -m pytest tests/ --cov=app --cov-report=html --cov-report=term

# View coverage report in browser
open htmlcov/index.html

# Run quality checks (Black + Pylint + Tests + Actionlint)
# Use VS Code Task: Cmd+Shift+P -> "Run Task" -> "Full Quality Check"
```

## Test Structure
```
tests/
├── conftest.py                          # Shared fixtures and test configuration
├── fixtures/                             # Mock data and test helpers
│   ├── dns_responses.py                 # Mock DNS response generators
│   ├── test_domains.py                  # Test domain data
│   └── tlsa_records.py                  # TLSA record fixtures
├── unit/                                 # Unit tests (102 tests)
│   ├── test_dnssec_validator.py         # DNSSEC validation tests (19 tests)
│   ├── test_tlsa_validator.py           # TLSA/DANE validation tests (23 tests)
│   ├── test_models.py                   # InfluxDB logging tests (21 tests)
│   ├── test_cli.py                      # CLI command tests (11 tests)
│   ├── test_db_init.py                  # Database initialization (9 tests)
│   ├── test_domain_utils.py             # Domain utilities (17 tests)
│   └── test_attribution.py              # Attribution tests (13 tests)
├── integration/                          # Integration tests (28 tests)
│   ├── test_app_endpoints.py            # Flask API endpoint tests (15 tests)
│   └── test_validation_workflow.py      # End-to-end workflow tests (13 tests)
└── README.md                             # This file
```

## Running Tests

### Run All Tests
```bash
# From project root
.venv/bin/python -m pytest tests/ -v

# With coverage report
.venv/bin/python -m pytest tests/ --cov=app --cov-report=html
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Specific test file
pytest tests/unit/test_dnssec_validator.py

# Specific test class or function
pytest tests/unit/test_dnssec_validator.py::TestDNSSECValidatorInitialization
pytest tests/unit/test_dnssec_validator.py::TestDNSSECValidatorInitialization::test_init_with_valid_domain
```

### Coverage Report
```bash
# Generate HTML coverage report
.venv/bin/python -m pytest tests/ --cov=app --cov-report=html

# View in browser
open htmlcov/index.html

# Terminal coverage with missing lines
.venv/bin/python -m pytest tests/ --cov=app --cov-report=term-missing
```

## Test Markers
Tests are marked with pytest markers for selective execution:
- `@pytest.mark.unit` - Fast, isolated unit tests with mocked dependencies
- `@pytest.mark.integration` - Slower integration tests involving multiple components
- `@pytest.mark.slow` - Very slow tests (can be skipped in quick runs)

## Test Fixtures

### Shared Fixtures (conftest.py)
- `flask_app` - Flask application instance for testing
- `client` - Flask test client for HTTP requests
- `runner` - Flask CLI test runner
- `mock_influxdb_client` - Mocked InfluxDB client
- `mock_influxdb_logger` - Mocked InfluxDB logger
- `test_config` - Test configuration dictionary

### DNS Response Fixtures (fixtures/dns_responses.py)
Mock DNS responses for different DNSSEC scenarios:
- `create_mock_dnskey_rrset()` - Generate DNSKEY records
- `create_mock_ds_rrset()` - Generate DS records
- `create_mock_rrsig_rrset()` - Generate RRSIG records
- `get_dns_response()` - Get complete DNS response for a domain

Example scenarios:
- **Valid DNSSEC**: Domains with proper DNSKEY + DS + RRSIG
- **Unsigned**: Domains without DNSSEC
- **Broken Chain**: Domains with DNSKEY but no DS record
- **Bogus**: Domains with mismatched key tags

### Domain Test Data (fixtures/test_domains.py)
Collections of test domains:
- `VALID_DOMAINS` - DNSSEC-signed domains (bondit.dk, cloudflare.com)
- `UNSIGNED_DOMAINS` - Domains without DNSSEC (example.org)
- `INVALID_DOMAINS` - Domains with broken DNSSEC
- `MALFORMED_DOMAINS` - Invalid domain strings
- `SUBDOMAIN_TEST_CASES` - Subdomain fallback test cases

### TLSA Record Fixtures (fixtures/tlsa_records.py)
Mock TLSA/DANE records:
- `create_mock_tlsa_record()` - Generate TLSA records
- `get_tlsa_fixture()` - Get TLSA fixtures by type (DANE-EE, DANE-TA, etc.)
- `get_mock_certificate()` - Mock TLS certificate data

## Writing New Tests

### Unit Test Template
```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
class TestMyFeature:
    \"\"\"Test my feature.\"\"\"
    
    def test_something(self):
        \"\"\"Test description.\"\"\"
        # Arrange
        # ...
        
        # Act
        # ...
        
        # Assert
        assert result == expected
    
    @patch("module.dependency")
    def test_with_mock(self, mock_dependency):
        \"\"\"Test with mocked dependency.\"\"\"
        mock_dependency.return_value = "mocked"
        # ...
```

### Integration Test Template
```python
import pytest

@pytest.mark.integration
class TestAPIEndpoint:
    \"\"\"Test API endpoint integration.\"\"\"
    
    def test_endpoint(self, client):
        \"\"\"Test endpoint returns expected response.\"\"\"
        response = client.get("/api/endpoint")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
```

## Mocking Strategy

### DNS Queries
All DNS queries are mocked to avoid real network calls:
```python
@patch("dns.resolver.Resolver")
def test_dns_query(mock_resolver_class):
    mock_resolver = MagicMock()
    mock_resolver_class.return_value = mock_resolver
    
    # Mock DNS response
    mock_answer = MagicMock()
    mock_answer.rrset = create_mock_dnskey_rrset("bondit.dk")
    mock_resolver.resolve.return_value = mock_answer
```

### InfluxDB
Database operations are mocked to avoid requiring a running InfluxDB instance:
```python
def test_with_influxdb(mock_influxdb_logger):
    # mock_influxdb_logger is already mocked
    result = mock_influxdb_logger.log_request(...)
    assert result is True
```

### Flask App
The Flask app fixture automatically mocks InfluxDB:
```python
def test_endpoint(client):
    # client is already configured with mocked dependencies
    response = client.get("/endpoint")
    assert response.status_code == 200
```

## VS Code Tasks

Pre-configured tasks available via `Cmd+Shift+P -> Run Task`:
- **Format with Black** - Auto-format code
- **Lint with Pylint** - Check code quality (9.5+ required)
- **Run Tests with Coverage** - Execute full test suite
- **Lint GitHub Actions Workflows** - Validate workflows
- **Docker: Build and Run** - Start application in Docker
- **Full Quality Check** - Run all checks in sequence

## Coverage Goals & Current Status

### ✅ Current Status (v1.0)
- **Total Tests**: 130 passing (102 unit + 28 integration)
- **Overall Coverage**: 53%
- **CI/CD**: Codecov integration with 50% minimum threshold

### Module Coverage
| Module | Coverage | Tests | Status |
|--------|----------|-------|--------|
| cli.py | 94% | 11 | ✅ Excellent |
| db_init.py | 83% | 9 | ✅ Good |
| domain_utils.py | 68% | 17 | ✅ Good |
| app.py | 58% | 28 | ✅ Good |
| models.py | 50% | 21 | ✅ Baseline |
| tlsa_validator.py | 40% | 23 | ⚠️ Needs improvement |
| dnssec_validator.py | 37% | 19 | ⚠️ Needs improvement |

### Future Goals (v2.0)
- **Overall**: 70%+ (stretch: 80%)
- **DNSSEC Validator**: 60%+ (complex logic)
- **TLSA Validator**: 60%+ (complex logic)
- **Models**: 70%+
- **App**: 70%+
- **All modules**: 50%+ ✅ (Already achieved!)
  - db_init.py: 7%

## CI/CD Integration
Tests run automatically on every PR via GitHub Actions (`.github/workflows/pr-quality-gate.yml`):
- Linting (Black + Pylint 9.5+)
- Unit tests
- Coverage reporting
- Security scans (Bandit + Safety)

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError`, ensure you're running tests from the project root with the virtual environment activated:
```bash
cd /path/to/dnssec-validator
source .venv/bin/activate
pytest tests/
```

### Coverage Not Collecting
The coverage tool needs the correct path configuration. Tests use `sys.path` manipulation to import app modules.

### Slow Tests
Skip slow tests in development:
```bash
pytest -m "not slow"
```

## Contributing
When adding new features:
1. Write tests first (TDD approach)
2. Ensure tests pass: `pytest tests/`
3. Check coverage: `pytest --cov=app`
4. Run linting: `pylint app/*.py`
5. Format code: `black app/ tests/`

## Resources
- [pytest documentation](https://docs.pytest.org/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Flask testing](https://flask.palletsprojects.com/en/latest/testing/)
