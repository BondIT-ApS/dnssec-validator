# Contributing to DNSSEC Validator

🙏 Thank you for considering contributing to DNSSEC Validator! We're excited to collaborate with you.

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
4. **Make your changes** and commit them
5. **Push to your fork** and create a Pull Request

## 🛠️ Development Setup

### Prerequisites
- Python 3.8+
- Docker (optional but recommended)

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
export FLASK_ENV=development
python app/app.py
```

### Docker Development
```bash
# Build and run
docker-compose up --build
```

## 🧪 Testing

Before submitting a PR, ensure your changes work:

```bash
# Test the API
curl "http://localhost:8080/api/validate/bondit.dk"

# Test with different domains
curl "http://localhost:8080/api/validate/example.com"
```

## 📝 Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and concise

## 🐛 Bug Reports

When reporting bugs, please include:
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)
- Relevant error messages or logs

## 💡 Feature Requests

We love new ideas! When suggesting features:
- Explain the use case and benefits
- Consider backward compatibility
- Check if similar functionality already exists

## 🔒 Security Issues

If you find a security vulnerability, please email us directly at [security@bondit.dk](mailto:security@bondit.dk) instead of opening a public issue.

## 📋 Pull Request Guidelines

- **Title**: Use a clear, descriptive title
- **Description**: Explain what your PR does and why
- **Testing**: Describe how you tested your changes
- **Documentation**: Update README.md if needed
- **Commits**: Use meaningful commit messages

### PR Checklist
- [ ] Code follows our style guidelines
- [ ] Self-review of the code completed
- [ ] Changes have been tested locally
- [ ] Documentation updated if needed
- [ ] No new security vulnerabilities introduced

## 🤝 Community

- Be respectful and inclusive
- Help others learn and grow
- Follow our [Code of Conduct](CODE_OF_CONDUCT.md)

## 📞 Getting Help

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Questions**: Start a GitHub Discussion
- **Email**: Contact us at [opensource@bondit.dk](mailto:opensource@bondit.dk)

---

**Happy coding! 🧱✨**
*Building better DNS security, one brick at a time.*
