# API Reference

DNSSEC Validator provides a RESTful API for programmatic access to DNS Security Extensions validation.

## Base URL

```
http://localhost:8080/api
```

## Endpoints

### Validate Domain

**GET** `/api/validate/{domain_or_url}`

Validates DNSSEC for a domain or extracts domain from URL.

**Parameters:**
- `domain_or_url` (path) - Domain name or full URL

**Examples:**
```bash
# Domain name
curl "http://localhost:8080/api/validate/bondit.dk"

# URL (automatically extracts domain)
curl "http://localhost:8080/api/validate/https://bondit.dk/page"
```

**Response:**
```json
{
  "domain": "bondit.dk",
  "status": "valid",
  "validation_time": "2025-08-08T16:30:00Z",
  "chain_of_trust": [...],
  "records": {...},
  "tlsa_summary": {...}
}
```

### Detailed Validation

**GET** `/api/validate/detailed/{domain_or_url}`

Returns comprehensive DNSSEC validation details.

### Health Check

**GET** `/health` - Detailed health status (JSON)  
**GET** `/health/simple` - Simple health check (text)

See [Health Monitoring](health-monitoring.md) for details.

## Interactive Documentation

Visit `/api/docs/` for interactive Swagger UI documentation.

---

**📚 [Back to Documentation Index](README.md)**
