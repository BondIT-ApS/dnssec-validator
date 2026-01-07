# Getting Started with DNSSEC Validator

This guide will help you get up and running with DNSSEC Validator quickly.

## Quick Start with Docker

The fastest way to run DNSSEC Validator is using Docker:

```bash
# Run the latest version
docker run -p 8080:8080 maboni82/dnssec-validator:latest

# Open your browser
open http://localhost:8080
```

That's it! The application is now running and ready to validate domains.

## Basic Usage

### Web Interface

1. Navigate to `http://localhost:8080` in your web browser
2. Enter a domain name (e.g., `bondit.dk`)
3. Click "Validate DNSSEC"
4. View the detailed validation report

The web interface provides:
- Visual chain of trust from root to your domain
- Color-coded validation status
- Detailed DNSSEC records (DNSKEY, DS, RRSIG)
- TLSA/DANE validation results (when applicable)

### API Usage

The application provides a RESTful API for programmatic access:

```bash
# Validate a domain
curl "http://localhost:8080/api/validate/bondit.dk"

# Validate with URL input (automatically extracts domain)
curl "http://localhost:8080/api/validate/https://bondit.dk/some/path"

# Get detailed validation results
curl "http://localhost:8080/api/validate/detailed/bondit.dk"
```

**Response format:**
```json
{
  "domain": "bondit.dk",
  "status": "valid",
  "validation_time": "2025-08-08T16:30:00Z",
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
  ]
}
```

## Live Demo

Try the live production deployment at:
**[https://dnssec-validator.bondit.dk](https://dnssec-validator.bondit.dk)**

The production deployment includes:
- ✅ HTTPS with SSL/TLS encryption
- ✅ Professional domain and hosting
- ✅ High availability and monitoring
- ✅ Full API documentation at `/api/docs/`

## Input Flexibility

DNSSEC Validator accepts both domain names and URLs:

**Domain names:**
- `bondit.dk`
- `www.example.com`
- `sub.domain.example.org`

**URLs (domain automatically extracted):**
- `https://bondit.dk`
- `http://www.example.com/page`
- `https://example.com/path/to/resource?query=param`

**Smart processing:**
- Automatic space removal: `"bond it.dk"` → `"bondit.dk"`
- Protocol stripping: `"https://example.com"` → `"example.com"`
- Path removal: `"/path/page"` is ignored

## Next Steps

- **[Installation Guide](installation.md)** - Learn about different installation methods
- **[API Reference](api-reference.md)** - Complete API documentation
- **[Configuration](configuration.md)** - Customize your deployment
- **[Architecture](architecture.md)** - Understand how DNSSEC validation works

## Common Questions

### What domains can I validate?

Any domain with DNSSEC enabled. If DNSSEC is not configured for a domain, the validator will report this status.

### How accurate is the validation?

DNSSEC Validator performs cryptographic verification of the complete chain of trust from IANA root trust anchors down to your domain, the same process used by DNSSEC-validating DNS resolvers.

### Is there a rate limit?

Yes, to ensure fair usage. See the [Rate Limiting documentation](rate-limiting.md) for details.

### Can I use this in production?

Absolutely! The application is designed for production use with Docker support, health checks, monitoring integration, and comprehensive security features.

---

**📚 [Back to Documentation Index](README.md)**
