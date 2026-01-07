# Container Orchestration

This guide covers deploying DNSSEC Validator with various container orchestration platforms.

## Docker Compose

Docker Compose is the simplest way to deploy DNSSEC Validator with all dependencies.

### Development Setup

```yaml
services:
  influxdb:
    image: influxdb:2.7-alpine
    container_name: dnssec-influxdb
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=adminpassword
      - DOCKER_INFLUXDB_INIT_ORG=dnssec-validator
      - DOCKER_INFLUXDB_INIT_BUCKET=requests
      - DOCKER_INFLUXDB_INIT_RETENTION=10d
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=my-super-secret-auth-token
    volumes:
      - influx_data:/var/lib/influxdb2
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  dnssec-validator:
    build: .
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=development
      - REQUEST_LOGGING_ENABLED=true
      - INFLUX_URL=http://influxdb:8086
      - INFLUX_TOKEN=my-super-secret-auth-token
      - INFLUX_ORG=dnssec-validator
      - INFLUX_BUCKET=requests
      - RATE_LIMIT_GLOBAL_DAY=5000
      - HEALTH_CHECK_ENABLED=true
    volumes:
      - ./app:/app
    depends_on:
      - influxdb
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/simple"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  influx_data:
```

### Production Setup

```yaml
services:
  influxdb:
    image: influxdb:2.7-alpine
    container_name: dnssec-influxdb-prod
    ports:
      - "8088:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_RETENTION=30d
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=production-token
    volumes:
      - influx_data:/var/lib/influxdb2
    networks:
      - dnssec-network

  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    container_name: dnssec-validator-prod
    ports:
      - "8091:8080"
    environment:
      - FLASK_ENV=production
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - CORS_ORIGINS=https://dnssec-validator.bondit.dk
      - HEALTH_CHECK_MEMORY_THRESHOLD=80
    networks:
      - dnssec-network
    restart: unless-stopped

networks:
  dnssec-network:
    driver: bridge

volumes:
  influx_data:
```

## Docker Swarm

Docker Swarm provides clustering and high availability.

### Stack Configuration

```yaml
services:
  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      rollback_config:
        parallelism: 1
        delay: 5s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      - HEALTH_CHECK_ENABLED=true
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - dnssec-network

networks:
  dnssec-network:
    driver: overlay
```

### Deployment Commands

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-stack.yml dnssec

# Check services
docker stack services dnssec

# View logs
docker service logs dnssec_dnssec-validator

# Scale service
docker service scale dnssec_dnssec-validator=5

# Remove stack
docker stack rm dnssec
```

## Kubernetes

### Basic Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dnssec-validator
  labels:
    app: dnssec-validator
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
          name: http
        env:
        - name: FLASK_ENV
          value: "production"
        - name: HEALTH_CHECK_ENABLED
          value: "true"
        livenessProbe:
          httpGet:
            path: /health/simple
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/simple
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: dnssec-validator
spec:
  selector:
    app: dnssec-validator
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### ConfigMap for Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dnssec-validator-config
data:
  FLASK_ENV: "production"
  HEALTH_CHECK_ENABLED: "true"
  HEALTH_CHECK_MEMORY_THRESHOLD: "85"
  RATE_LIMIT_GLOBAL_DAY: "5000"
  RATE_LIMIT_GLOBAL_HOUR: "1000"
  LOG_LEVEL: "INFO"
---
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
        envFrom:
        - configMapRef:
            name: dnssec-validator-config
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dnssec-validator-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - dnssec-validator.example.com
    secretName: dnssec-validator-tls
  rules:
  - host: dnssec-validator.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dnssec-validator
            port:
              number: 80
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dnssec-validator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dnssec-validator
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Portainer

Portainer provides a web UI for managing Docker containers.

### Deploy via Portainer UI

1. Navigate to **Stacks** → **Add stack**
2. Choose "Web editor"
3. Paste your docker-compose.yml
4. Click "Deploy the stack"

### Portainer Stack Template

```yaml
services:
  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    container_name: dnssec-validator
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      - HEALTH_CHECK_ENABLED=true
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

### Watchtower Integration

Auto-update containers with Watchtower:

```yaml
services:
  dnssec-validator:
    image: maboni82/dnssec-validator:latest
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    restart: unless-stopped

  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 3600 --label-enable
```

## Nomad

HashiCorp Nomad for container orchestration:

```hcl
job "dnssec-validator" {
  datacenters = ["dc1"]
  type = "service"

  group "validator" {
    count = 3

    network {
      port "http" {
        to = 8080
      }
    }

    service {
      name = "dnssec-validator"
      port = "http"
      
      check {
        type = "http"
        path = "/health/simple"
        interval = "30s"
        timeout = "10s"
      }
    }

    task "app" {
      driver = "docker"

      config {
        image = "maboni82/dnssec-validator:latest"
        ports = ["http"]
      }

      env {
        FLASK_ENV = "production"
        HEALTH_CHECK_ENABLED = "true"
      }

      resources {
        cpu = 500
        memory = 512
      }
    }
  }
}
```

## Best Practices

### Resource Limits

Always set resource limits to prevent resource exhaustion:

```yaml
resources:
  limits:
    cpus: '0.5'
    memory: 512M
  reservations:
    cpus: '0.25'
    memory: 256M
```

### Health Checks

Enable health checks for automatic recovery:

```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/simple')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Rolling Updates

Configure rolling updates for zero-downtime deployments:

```yaml
update_config:
  parallelism: 1
  delay: 10s
  order: start-first
  failure_action: rollback
```

### Logging

Use structured logging for production:

```yaml
environment:
  - LOG_FORMAT=json
  - LOG_LEVEL=INFO
```

### Secrets Management

Use secrets for sensitive data:

**Docker Swarm:**
```bash
echo "my-secret-token" | docker secret create influx_token -
```

**Kubernetes:**
```bash
kubectl create secret generic influx-token --from-literal=token=my-secret-token
```

---

**📚 [Back to Documentation Index](README.md)**
