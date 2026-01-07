# Rate Limiting

DNSSEC Validator includes comprehensive rate limiting to ensure fair usage and prevent abuse. Rate limits are applied per IP address and are fully configurable via environment variables.

## Default Rate Limits

| Endpoint Type | Limit | Description |
|---------------|-------|-------------|
| **Global** | 5000/day, 1000/hour | Overall requests per IP across all endpoints |
| **API** | 200/minute, 2000/hour | REST API endpoints (`/api/validate/*`) |
| **Web Interface** | 50/minute, 500/hour | Web UI and direct domain URLs |

## Configuration

Rate limits can be customized using environment variables:

```bash
# Global rate limits (applied to all requests)
RATE_LIMIT_GLOBAL_DAY=5000    # Requests per IP per day
RATE_LIMIT_GLOBAL_HOUR=1000   # Requests per IP per hour

# API-specific rate limits
RATE_LIMIT_API_MINUTE=200     # API requests per IP per minute
RATE_LIMIT_API_HOUR=2000      # API requests per IP per hour

# Web interface rate limits
RATE_LIMIT_WEB_MINUTE=50      # Web requests per IP per minute
RATE_LIMIT_WEB_HOUR=500       # Web requests per IP per hour
```

## Docker Configuration Examples

### Development/Testing

For development or testing environments with lighter restrictions:

```yaml
services:
  dnssec-validator:
    build: .
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=development
      - RATE_LIMIT_GLOBAL_DAY=10000
      - RATE_LIMIT_GLOBAL_HOUR=2000
      - RATE_LIMIT_API_MINUTE=500
      - RATE_LIMIT_API_HOUR=5000
      - RATE_LIMIT_WEB_MINUTE=100
      - RATE_LIMIT_WEB_HOUR=1000
```

### Conservative Production

For public services with conservative limits:

```yaml
services:
  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      - RATE_LIMIT_GLOBAL_DAY=1000
      - RATE_LIMIT_GLOBAL_HOUR=100
      - RATE_LIMIT_API_MINUTE=5
      - RATE_LIMIT_API_HOUR=50
      - RATE_LIMIT_WEB_MINUTE=10
      - RATE_LIMIT_WEB_HOUR=100
```

### Enterprise/Internal Use

For internal or enterprise deployments with generous limits:

```yaml
services:
  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      - RATE_LIMIT_GLOBAL_DAY=5000
      - RATE_LIMIT_GLOBAL_HOUR=500
      - RATE_LIMIT_API_MINUTE=30
      - RATE_LIMIT_API_HOUR=1000
      - RATE_LIMIT_WEB_MINUTE=50
      - RATE_LIMIT_WEB_HOUR=1000
```

## Rate Limit Responses

### API Endpoints

When rate limits are exceeded, API endpoints return structured JSON with HTTP 429:

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

**Response headers include:**
- `X-RateLimit-Limit` - The rate limit ceiling for that endpoint
- `X-RateLimit-Remaining` - Number of requests remaining
- `X-RateLimit-Reset` - Unix timestamp when the limit resets
- `Retry-After` - Seconds until the rate limit resets

### Web Interface

When rate limits are exceeded, the web interface shows a user-friendly error page with:
- Current rate limit information
- Time until limit resets
- Suggestions for API usage for automated tools
- Link to API documentation

## Rate Limiting Strategy

### How It Works

1. **IP-Based Tracking**: Rate limits are tracked per IP address
2. **Multiple Windows**: Limits are enforced across different time windows (minute, hour, day)
3. **Hierarchical Limits**: Global limits apply first, then endpoint-specific limits
4. **Automatic Reset**: Limits automatically reset at the end of each time window

### Exempt Endpoints

The following endpoints are **not** rate limited:
- `/health` - Detailed health check
- `/health/simple` - Simple health check
- `/static/*` - Static assets (CSS, JS, images)

These endpoints are excluded to ensure monitoring and health checks work reliably.

## Production Recommendations

### Public Web Service

Recommended limits for a public-facing web service:

```bash
RATE_LIMIT_GLOBAL_DAY=1000
RATE_LIMIT_GLOBAL_HOUR=100
RATE_LIMIT_API_MINUTE=10
RATE_LIMIT_API_HOUR=100
RATE_LIMIT_WEB_MINUTE=15
RATE_LIMIT_WEB_HOUR=150
```

### Internal Tool

Recommended limits for internal/corporate use:

```bash
RATE_LIMIT_GLOBAL_DAY=5000
RATE_LIMIT_GLOBAL_HOUR=500
RATE_LIMIT_API_MINUTE=50
RATE_LIMIT_API_HOUR=1000
RATE_LIMIT_WEB_MINUTE=100
RATE_LIMIT_WEB_HOUR=1000
```

### API-First Service

If primarily exposing the API with minimal web UI usage:

```bash
RATE_LIMIT_GLOBAL_DAY=10000
RATE_LIMIT_GLOBAL_HOUR=1000
RATE_LIMIT_API_MINUTE=100
RATE_LIMIT_API_HOUR=5000
RATE_LIMIT_WEB_MINUTE=20
RATE_LIMIT_WEB_HOUR=200
```

## Monitoring Rate Limits

### Check Current Limits

You can inspect current rate limits via response headers on any request:

```bash
curl -I http://localhost:8080/api/validate/bondit.dk
```

Look for these headers:
```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 195
X-RateLimit-Reset: 1705329600
```

### Analytics Integration

If you have InfluxDB analytics enabled, rate limit events are logged:
- Number of rate-limited requests
- Which endpoints are most frequently limited
- IP addresses hitting limits
- Time patterns of limit violations

See [Database & Analytics](database-analytics.md) for more details.

## Handling Rate Limits in Code

### Python Example

```python
import requests
import time

def validate_domain(domain, max_retries=3):
    url = f"http://localhost:8080/api/validate/{domain}"
    
    for attempt in range(max_retries):
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # Rate limited - check retry-after header
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
        else:
            raise Exception(f"API error: {response.status_code}")
    
    raise Exception("Max retries exceeded")
```

### JavaScript Example

```javascript
async function validateDomain(domain, maxRetries = 3) {
  const url = `http://localhost:8080/api/validate/${domain}`;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const response = await fetch(url);
    
    if (response.ok) {
      return await response.json();
    } else if (response.status === 429) {
      // Rate limited - check retry-after header
      const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
      console.log(`Rate limited. Waiting ${retryAfter} seconds...`);
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
    } else {
      throw new Error(`API error: ${response.status}`);
    }
  }
  
  throw new Error('Max retries exceeded');
}
```

## Troubleshooting

### I'm Getting Rate Limited Too Quickly

1. **Check your IP**: Ensure you're not behind a NAT that shares an IP with other users
2. **Review limits**: Check configured limits with `docker logs dnssec-validator | grep "RATE_LIMIT"`
3. **Adjust limits**: Increase limits via environment variables
4. **Use exponential backoff**: Implement retry logic with increasing delays

### Rate Limits Not Working

1. **Verify configuration**: Check environment variables are being passed to container
2. **Check logs**: Look for rate limit initialization messages in application logs
3. **Test endpoints**: Use curl with `-I` flag to inspect rate limit headers

### Need Higher Limits

For legitimate high-volume use cases:
1. Deploy your own instance with custom limits
2. Contact [BondIT ApS](https://bondit.dk) for enterprise support
3. Implement caching in your application to reduce requests

## Security Considerations

Rate limiting is a critical security feature that:
- **Prevents abuse**: Stops malicious users from overwhelming the service
- **Ensures availability**: Guarantees fair access for all users
- **Reduces costs**: Limits resource consumption and infrastructure costs
- **Protects DNS infrastructure**: Prevents excessive queries to upstream DNS servers

**Never disable rate limiting in production environments.**

---

**📚 [Back to Documentation Index](README.md)**
