# 🧱 VSCode Configuration for DNSSEC Validator

This folder contains shared VSCode configuration for the DNSSEC Validator project, following BondIT-ApS standards.

## 🚀 Quick Setup

### 1. Copy Templates

Copy templates to create your local settings:

```bash
cd .vscode
cp settings.json.template settings.json
cp launch.json.template launch.json
```

### 2. Install Recommended Extensions

VSCode will prompt you to install recommended extensions when you open the workspace. Click "Install All" to get the complete toolkit.

Or manually install via Command Palette:
```
Ctrl/Cmd + Shift + P → Extensions: Show Recommended Extensions
```

## 📁 Files Overview

### Shared (Version Controlled)
- **`tasks.json`** - Development tasks (testing, linting, Docker, etc.)
- **`extensions.json`** - Recommended VSCode extensions
- **`settings.json.template`** - Template workspace settings
- **`launch.json.template`** - Template debug configurations
- **`README.md`** - This file

### Local (Ignored by Git)
- **`settings.json`** - Your personal workspace settings
- **`launch.json`** - Your personal debug configurations

## 🧪 Available Tasks

Access tasks via `Ctrl/Cmd + Shift + P` → `Tasks: Run Task`

### Backend Tasks 🐍
- **🧱 Setup Virtual Environment** - Create and configure Python venv
- **🚀 Run Flask Development Server** - Start DNSSEC Validator locally
- **🧪 Run Tests with Coverage** - Execute pytest suite
- **🎨 Format with Black** - Auto-format Python code
- **🐍 Lint with Pylint** - Check code quality (must score 9.5+)
- **🛡️ Security: Bandit Scan** - Static security analysis
- **🔒 Security: Safety CLI Scan** - Dependency vulnerability check

### Docker Tasks 🐳
- **🐳 Docker: Build and Run** - Start containers with docker-compose
- **🐳 Docker: Stop Services** - Stop all containers
- **🐳 Docker: View Logs** - Follow container logs
- **🐳 Docker: Restart Services** - Restart containers
- **🩺 Docker: Health Check** - Test /health endpoint

### Development Tasks 🔧
- **📦 Update Dependencies** - Update pip packages
- **🧹 Clean Cache** - Remove __pycache__, .pyc files
- **🔧 Lint GitHub Actions Workflows** - Validate CI/CD with actionlint

### Quality Gates 🧱
- **🧱 Backend Quality Check** - Format, lint, and security scans
- **🧱 Full Quality Check** - Backend checks + workflow validation
- **🚀 Pre-Push Quality Gate** - Complete validation before pushing (recommended)

## 🐛 Debug Configurations

After copying `launch.json.template` to `launch.json`, these debug configurations are available:

1. **🧪 Python: Debug Tests** - Debug current test file
2. **🧪 Python: Debug All Tests** - Debug entire test suite
3. **🚀 Flask: Debug App** - Debug Flask application
4. **🐳 Docker: Attach to Container** - Debug inside Docker container
5. **🔧 CLI: Debug Validator** - Debug CLI validation tool

## 🛠️ Development Workflow

### Initial Setup
```bash
# 1. Create virtual environment
Task: 🧱 Setup Virtual Environment

# 2. Copy configuration templates
cp .vscode/settings.json.template .vscode/settings.json
cp .vscode/launch.json.template .vscode/launch.json

# 3. Install recommended extensions
(VSCode will prompt automatically)
```

### Daily Development
```bash
# Start Flask server
Task: 🚀 Run Flask Development Server

# Or use Docker
Task: 🐳 Docker: Build and Run
```

### Before Committing
```bash
# Run comprehensive quality checks
Task: 🚀 Pre-Push Quality Gate
```

## 🧱 Key Configuration Features

### Python Environment
- Auto-detects `.venv` virtual environment
- Black formatter (88 char line length)
- Pylint with custom `.pylintrc` configuration
- pytest integration with coverage

### Code Quality
- Format on save enabled for all file types
- Rulers at 88 and 120 characters
- Spell checking with DNSSEC-specific dictionary
- Auto-organize imports disabled (manual control)

### File Management
- Excludes: `__pycache__`, `.venv`, coverage reports, test caches
- Search excludes: venv, data folders, compiled Python files

### Testing
- pytest auto-discovery on save
- Verbose output with short tracebacks
- Coverage reports in HTML and terminal

## 🔧 Customization

### Personal Settings
Edit your local `settings.json` to customize:
- Python interpreter path
- Terminal settings
- Additional file exclusions
- Custom keybindings

### Debug Configurations
Edit your local `launch.json` to add:
- Custom test arguments
- Different Flask environment variables
- Additional CLI debug configurations

## 📚 Recommended Extensions

### Essential
- **Python** (ms-python.python) - Core Python support
- **Black Formatter** (ms-python.black-formatter) - Code formatting
- **Pylint** (ms-python.pylint) - Code linting
- **Docker** (ms-azuretools.vscode-docker) - Container management

### Code Quality
- **GitLens** (eamodio.gitlens) - Enhanced Git integration
- **REST Client** (humao.rest-client) - API testing
- **Code Spell Checker** (streetsidesoftware.code-spell-checker) - Spell checking

### Productivity
- **Path Intellisense** (christian-kohler.path-intellisense) - File path autocomplete
- **TODO Highlight** (wayou.vscode-todo-highlight) - Highlight TODO comments
- **Git Graph** (mhutchie.git-graph) - Visualize Git history

## 🆘 Troubleshooting

### Tests Not Discovered
1. Reload VSCode window: `Ctrl/Cmd + Shift + P` → `Developer: Reload Window`
2. Verify Python interpreter: Check bottom-left status bar
3. Clear pytest cache: `Task: 🧹 Clean Cache`

### Python Import Errors
1. Ensure virtual environment is activated
2. Check `PYTHONPATH` in terminal environment
3. Verify `settings.json` has correct `python.analysis.extraPaths`

### Flask Debug Issues
1. Check `.venv/bin/python` exists
2. Verify port 8080 is available: `lsof -ti:8080`
3. Review Flask environment variables in `launch.json`

### Docker Container Issues
1. Check containers are running: `docker-compose ps`
2. View logs: `Task: 🐳 Docker: View Logs`
3. Verify health endpoint: `Task: 🩺 Docker: Health Check`

## 🔗 Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development guide for Claude Code
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [README.md](../README.md) - Project overview

---

**Remember:** Like building with LEGO bricks, every DNS security piece should fit together perfectly! 🧱🔒

*Made with ❤️, ☕, and 🧱 by BondIT ApS*
