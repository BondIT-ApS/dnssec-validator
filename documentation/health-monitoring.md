# Health Monitoring

DNSSEC Validator includes comprehensive health monitoring capabilities designed for container orchestration platforms and monitoring systems.

## Health Check Endpoints

| Endpoint | Purpose | Response Format | Rate Limited |
|----------|---------|-----------------|--------------|
| `/health` | Detailed health status | JSON | No |
| `/health/simple` | Basic health check | Plain text | No |

### Detailed Health Check (`/health`)

Returns comprehensive health information in JSON format:

```bash
curl http://localhost:8080/health
```

**Response format:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-06T07:23:12Z",
  "version": "1.0.0",
  "checks": {
    "application": "ok",
    "dns_resolver": "ok",
    "memory_usage": "ok"
  },
  "uptime": "2h 15m 32s"
}
```

**Health status values:**
- `healthy` - All systems operational (HTTP 200)
- `degraded` - Some non-critical issues detected (HTTP 200)
- `unhealthy` - Critical issues affecting functionality (HTTP 503)

### Simple Health Check (`/health/simple`)

Returns plain text response for simple monitoring:

```bash
curl http://localhost:8080/health/simple
```

**Response:**
```
healthy
```

Returns HTTP 200 with "healthy" text when the application is running properly, or HTTP 503 when unhealthy.

## Configuration

Health monitoring behavior can be customized using environment variables:

```bash
# Enable/disable detailed health checks
HEALTH_CHECK_ENABLED=true

# Enable/disable DNS resolution test
HEALTH_CHECK_DNS_TEST=true

# Memory usage warning threshold (percentage)
HEALTH_CHECK_MEMORY_THRESHOLD=90

# Test domain for DNS resolution check
HEALTH_CHECK_DNS_DOMAIN=example.com
```

### Configuration Examples

**Strict health monitoring:**
```yaml
environment:
  - HEALTH_CHECK_ENABLED=true
  - HEALTH_CHECK_DNS_TEST=true
  - HEALTH_CHECK_MEMORY_THRESHOLD=80  # Warn at 80% memory
```

**Minimal health checks (faster response):**
```yaml
environment:
  - HEALTH_CHECK_ENABLED=true
  - HEALTH_CHECK_DNS_TEST=false  # Skip DNS test
  - HEALTH_CHECK_MEMORY_THRESHOLD=95
```

## Health Check Components

The detailed health endpoint monitors:

### 1. Application Status
Tests basic Flask application responsiveness. Returns `ok` if the application can process requests.

### 2. DNS Resolver
Tests ability to resolve DNS queries against a known-good domain (default: `example.com`). This ensures the core DNSSEC validation functionality will work.

**Configurable via:**
```bash
HEALTH_CHECK_DNS_TEST=true   # Enable/disable DNS resolution test (default: true)
```

**Note:** The test domain is hardcoded to `example.com` in the application code.

### 3. Memory Usage
Monitors system memory consumption and warns if usage exceeds the configured threshold.

**Configurable via:**
```bash
HEALTH_CHECK_MEMORY_THRESHOLD=90  # Percentage
```

### 4. Uptime
Tracks application runtime since startup. Useful for monitoring restart frequency.

## Docker Integration

### Docker Health Check

Add health checks to your Docker containers:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"
```

**Parameters:**
- `interval` - Time between health checks (default: 30s)
- `timeout` - Max time for health check to complete (default: 10s)
- `retries` - Number of consecutive failures before unhealthy (default: 3)
- `start-period` - Grace period before health checks start (default: 60s)

### Docker Compose Integration

**Development (`docker-compose.yml`):**
```yaml
services:
  dnssec-validator:
    build: .
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

**Production (`docker-compose.prod.yml`):**
```yaml
services:
  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    ports:
      - "8080:8080"
    environment:
      - HEALTH_CHECK_ENABLED=true
      - HEALTH_CHECK_MEMORY_THRESHOLD=80
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### Check Container Health Status

```bash
# View health status
docker ps

# View detailed health information
docker inspect dnssec-validator | grep -A 10 Health

# View health check logs
docker inspect dnssec-validator --format='{{json .State.Health}}' | jq
```

## Container Orchestration

### Portainer

Portainer provides visual health status indicators:
- Green checkmark - Container healthy
- Yellow warning - Container degraded
- Red X - Container unhealthy

Health checks are automatically displayed in the container overview.

### Docker Swarm

Docker Swarm uses health checks for automatic container replacement:

```yaml
version: '3.8'
services:
  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes

**Liveness Probe** (restart unhealthy containers):
```yaml
livenessProbe:
  httpGet:
    path: /health/simple
    port: 8080
  initialDelaySeconds: 60
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
```

**Readiness Probe** (control traffic routing):
```yaml
readinessProbe:
  httpGet:
    path: /health/simple
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

**Complete Kubernetes deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dnssec-validator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dnssec-validator
  template:
    metadata:
      labels:
        app: dnssec-validator
    spec:
      containers:
      - name: dnssec-validator
        image: maboni82/dnssec-validator:latest
        ports:
        - containerPort: 8080
        env:
        - name: HEALTH_CHECK_ENABLED
          value: "true"
        - name: HEALTH_CHECK_MEMORY_THRESHOLD
          value: "85"
        livenessProbe:
          httpGet:
            path: /health/simple
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/simple
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Monitoring Integration

### Prometheus

Configure Prometheus to scrape health endpoint:

```yaml
scrape_configs:
  - job_name: 'dnssec-validator'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/health'
    scrape_interval: 30s
    scrape_timeout: 10s
```

### Grafana

Create alerts based on health status:

```yaml
alert: DNSSECValidatorUnhealthy
expr: dnssec_validator_health_status != 1
for: 5m
labels:
  severity: critical
annotations:
  summary: "DNSSEC Validator is unhealthy"
  description: "DNSSEC Validator has been unhealthy for more than 5 minutes"
```

### Uptime Monitoring Services

Configure external uptime monitoring (e.g., Uptime Robot, Pingdom):

- **Endpoint**: `https://your-domain.com/health/simple`
- **Expected response**: `healthy`
- **Check interval**: 1-5 minutes
- **Timeout**: 10 seconds

## Load Balancer Integration

### nginx

```nginx
upstream dnssec_validator {
    server dnssec-validator-1:8080 max_fails=3 fail_timeout=30s;
    server dnssec-validator-2:8080 max_fails=3 fail_timeout=30s;
    server dnssec-validator-3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name dnssec-validator.example.com;

    location /health {
        access_log off;
        proxy_pass http://dnssec_validator;
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://dnssec_validator;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### HAProxy

```haproxy
backend dnssec_validator
    balance roundrobin
    option httpchk GET /health/simple
    http-check expect string healthy
    server dnssec1 dnssec-validator-1:8080 check inter 30s
    server dnssec2 dnssec-validator-2:8080 check inter 30s
    server dnssec3 dnssec-validator-3:8080 check inter 30s
```

## Troubleshooting

### Health Check Failing

1. **Check application logs**:
   ```bash
   docker logs dnssec-validator
   ```

2. **Test health endpoint manually**:
   ```bash
   curl -v http://localhost:8080/health/simple
   ```

3. **Verify DNS resolution** (if DNS test enabled):
   ```bash
   docker exec dnssec-validator nslookup example.com
   ```

4. **Check memory usage**:
   ```bash
   docker stats dnssec-validator
   ```

### Container Restarting Frequently

1. Increase `start_period` to give application more startup time
2. Increase `retries` to allow more failures before restart
3. Check application logs for startup errors
4. Verify resource limits (memory, CPU) are adequate

### Health Endpoint Timing Out

1. Increase health check `timeout` value
2. Disable DNS test if network latency is high:
   ```yaml
   environment:
     - HEALTH_CHECK_DNS_TEST=false
   ```
3. Check if application is overloaded (increase resources)

---

**📚 [Back to Documentation Index](README.md)**
