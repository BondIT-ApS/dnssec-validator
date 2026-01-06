# Contributing to DNSSEC Validator

🙏 Thank you for considering contributing to DNSSEC Validator! Like building with LEGO bricks, every contribution matters for DNS security.

## Table of Contents
- [Quick Start](#-quick-start)
- [Development Setup](#%EF%B8%8F-development-setup)
- [Quality Standards](#-quality-standards)
- [Testing](#-testing)
- [Pull Request Process](#-pull-request-process)
- [Code Style](#-code-style)
- [CI/CD Pipeline](#-cicd-pipeline)

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/dnssec-validator.git
   cd dnssec-validator
   ```
3. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Set up development environment** (see below)
5. **Make your changes** following our quality standards
6. **Run quality checks** locally before pushing
7. **Push to your fork** and create a Pull Request

## 🛠️ Development Setup

### Prerequisites
- Python 3.11+ (3.13+ recommended)
- Docker & Docker Compose
- Git
- VS Code (recommended)

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock pytest-flask freezegun requests-mock

# Run tests
python -m pytest tests/ --cov=app --cov-report=html

# Start development server
python app/app.py
# or with Docker
docker-compose up --build
```

### VS Code Setup

The project includes pre-configured tasks (`.vscode/tasks.json`):

**Access via**: `Cmd+Shift+P` → `Tasks: Run Task`

- **Format with Black** - Auto-format code
- **Lint with Pylint** - Check code quality
- **Run Tests with Coverage** - Execute test suite  
- **Lint GitHub Actions Workflows** - Validate CI/CD
- **Docker: Build and Run** - Start application
- **Full Quality Check** - Run all checks sequentially ⭐

## 🏗️ Quality Standards

### Minimum Requirements

All code must meet these standards before merging:

| Check | Tool | Threshold | Status |
|-------|------|-----------|--------|
| 🎨 Code Formatting | Black | 100% compliant | Required |
| 🐍 Code Quality | Pylint | 9.5/10 minimum | Required |
| 🧪 Test Coverage | Pytest | 50% minimum | Required |
| 🛡️ Security Scan | Bandit + Safety | No high/critical | Required |
| 🐳 Docker Build | Docker Compose | Successful build | Required |

### Pre-Commit Checklist

Before committing, run these checks locally:

```bash
# 1. Format code
black app/ tests/ --line-length=88 --exclude='.git,.github,data'

# 2. Run linter (must score 9.5+)
pipx run pylint app/*.py --rcfile=.pylintrc

# 3. Run tests with coverage
source .venv/bin/activate
python -m pytest tests/ --cov=app --cov-report=term-missing

# 4. Optional: Security scans
pipx run bandit -r app/
pipx run safety check
```

**Quick Command** (all-in-one):
```bash
black app/ tests/ --line-length=88 --exclude='.git,.github,data' && \
pipx run pylint app/*.py --rcfile=.pylintrc && \
source .venv/bin/activate && python -m pytest tests/ --cov=app
```

**VS Code**: Use the **"Full Quality Check"** task for automated sequential execution.

## 🧪 Testing

### Current Status
- **Total Tests**: 130 passing (102 unit + 28 integration)
- **Coverage**: 53% (minimum: 50%)
- **Framework**: pytest with mocking

### Test Structure

```
tests/
├── unit/          # Fast, isolated tests (102 tests)
├── integration/   # Multi-component tests (28 tests)
├── fixtures/      # Mock data and helpers
└── conftest.py    # Shared fixtures
```

### Writing Tests

```python
import pytest
from unittest.mock import patch

@pytest.mark.unit
class TestMyFeature:
    """Test my feature."""
    
    def test_something(self):
        """Test description."""
        # Arrange
        expected = "result"
        
        # Act
        result = my_function()
        
        # Assert
        assert result == expected
```

### Running Tests

```bash
# All tests with coverage
pytest tests/ --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html

# Specific test
pytest tests/unit/test_dnssec_validator.py -v
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

## 📋 Pull Request Process

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write tests first (TDD approach recommended)
- Implement feature
- Ensure all quality checks pass locally

### 3. Commit Changes

```bash
git add .
git commit -m "Add feature: description

- Detailed change 1
- Detailed change 2

Closes #123"
```

**Commit Message Guidelines**:
- Use present tense ("Add feature" not "Added feature")
- First line: brief summary (50 chars max)
- Blank line, then detailed description
- Reference issues: `Closes #123`

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Create a Pull Request on GitHub with:
- Clear title describing the change
- Description explaining what and why
- Reference to related issues
- Screenshots/examples if applicable

### 5. PR Quality Gate

All PRs trigger our automated **🧱 LEGO Quality Gate** workflow:

#### Phase 1: Parallel Checks
- 🐍 **Linting** - Black formatting + Pylint (9.5+ required)
- ✨ **Quality** - Bandit security scan + pytest with coverage
- 🛡️ **Safety** - Deep dependency vulnerability scanning
- 📊 **Codecov** - Coverage upload and threshold check (50% min)
- 🔧 **Workflow Linting** - actionlint validation (if workflows changed)

#### Phase 2: Docker Build
- 🐳 **Docker Build** - Validates container builds successfully

#### Phase 3: Summary
- 📊 **Summary** - Posts comprehensive results as PR comment

### 6. PR Requirements

Before your PR can be merged:

✅ All quality gate checks must pass  
✅ Code coverage ≥ 50%  
✅ Pylint score ≥ 9.5/10  
✅ No security vulnerabilities  
✅ Docker build successful  
✅ At least one approval from maintainer  
✅ All conversations resolved  

## 📝 Code Style

### Python

We follow PEP 8 with these specific guidelines:

```python
# Line length: 88 characters (Black default)
# Indentation: 4 spaces (no tabs)
# String quotes: Double quotes preferred
# Imports: Grouped (stdlib, third-party, local)

# Good ✅
def validate_domain(domain: str) -> dict:
    """Validate DNSSEC configuration for a domain.
    
    Args:
        domain: Domain name to validate
        
    Returns:
        Dictionary with validation results
    """
    result = {"domain": domain, "status": "valid"}
    return result

# Bad ❌
def validate_domain(domain):
    result={"domain":domain,"status":"valid"}
    return result
```

### Docstrings

Use Google-style docstrings:

```python
def function(arg1: str, arg2: int) -> bool:
    """Short description.
    
    Longer description if needed.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When validation fails
    """
    pass
```

### Type Hints

Use type hints for all function signatures:

```python
from typing import Optional, Dict, List

def process_records(
    records: List[str], 
    config: Optional[Dict[str, any]] = None
) -> Dict[str, any]:
    """Process DNS records."""
    pass
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflows

- **PR Quality Gate** - Runs on every PR to main
- **Docker Publish** - Triggers on tags (YY.M.PATCH format)
- **Security Monitoring** - Weekly CodeQL scans
- **Nightly Builds** - Development builds from master

### Codecov Integration

- Automatic coverage upload on every PR
- Coverage diff in PR comments
- Minimum threshold: 50% (hard fail if below)
- View reports: https://codecov.io/gh/BondIT-ApS/dnssec-validator

### Docker Hub

Images published to: `maboni82/dnssec-validator`

Tags:
- `latest` - Latest stable release
- `YY.M.PATCH` - Specific version (e.g., `26.1.5`)
- `YY.M` - Monthly release (e.g., `26.1`)
- `nightly` - Latest development build

## 🔒 Security

### Reporting Vulnerabilities

Please report security vulnerabilities privately to [security@bondit.dk](mailto:security@bondit.dk) instead of opening a public issue.

### Security Practices

- All dependencies scanned with Safety CLI
- Code scanned with Bandit on every PR
- Weekly CodeQL security analysis
- No secrets in code (use environment variables)
- Regular dependency updates via Dependabot

## 🐛 Bug Reports

When reporting bugs, please include:
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, Docker version)
- Relevant error messages or logs
- Screenshots if applicable

## 💡 Feature Requests

We love new ideas! When suggesting features:
- Explain the use case and benefits
- Consider backward compatibility
- Check if similar functionality already exists
- Provide examples if possible

## 🤝 Community

- Be respectful and inclusive
- Help others learn and grow
- Follow our Code of Conduct
- Share knowledge and best practices

## 📞 Getting Help

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discussions**: Start a GitHub Discussion for questions
- **Email**: Contact us at [opensource@bondit.dk](mailto:opensource@bondit.dk)
- **Documentation**: Check [WARP.md](WARP.md) for detailed development guide

## 📚 Additional Resources

- [tests/README.md](tests/README.md) - Detailed testing documentation
- [WARP.md](WARP.md) - Comprehensive development guide
- [README.md](README.md) - Project overview and usage

---

**Happy coding! 🧱✨**

*Building better DNS security, one LEGO brick at a time.*

**Made with ❤️, ☕, and 🧱 by BondIT ApS**
