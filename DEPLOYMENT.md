# DNSSEC Validator - Production Deployment Guide

This guide covers deploying the DNSSEC Validator to production using Portainer and Nginx Proxy Manager.

## 🎯 Production Environment

- **Live URL**: [https://dnssec-validator.bondit.dk](https://dnssec-validator.bondit.dk)
- **Portainer**: [https://portainer.bonde.ninja](https://portainer.bonde.ninja)
- **Container Management**: Portainer
- **Reverse Proxy**: Nginx Proxy Manager
- **SSL/TLS**: Let's Encrypt certificates

## 🚀 Deployment Methods

### Method 1: Portainer Web UI (Recommended)

1. **Access Portainer**
   - Navigate to [https://portainer.bonde.ninja](https://portainer.bonde.ninja)
   - Log in with your credentials

2. **Create New Stack**
   - Go to "Stacks" → "Add stack"
   - Name: `dnssec-validator`
   - Use the `docker-compose.prod.yml` file content

3. **Configure Environment**
   - Set the following environment variables:
     ```
     FLASK_ENV=production
     CORS_ORIGINS=https://dnssec-validator.bondit.dk
     ```

4. **Deploy Stack**
   - Click "Deploy the stack"
   - Monitor deployment in the logs

### Method 2: Portainer API

Use the Portainer REST API for automated deployment:

```bash
# Get authentication token
curl -X POST "https://portainer.bonde.ninja/api/auth" \
  -H "Content-Type: application/json" \
  -d '{"Username":"your-username","Password":"your-password"}'

# Create stack via API
curl -X POST "https://portainer.bonde.ninja/api/stacks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "Name": "dnssec-validator",
    "SwarmID": "",
    "ComposeFile": "$(cat docker-compose.prod.yml | base64 -w 0)",
    "Env": [
      {"name": "FLASK_ENV", "value": "production"},
      {"name": "CORS_ORIGINS", "value": "https://dnssec-validator.bondit.dk"}
    ]
  }'
```

## 🌐 Nginx Proxy Manager Configuration

### 1. Add Proxy Host

In Nginx Proxy Manager:

1. **Proxy Hosts** → **Add Proxy Host**
2. **Details Tab**:
   - Domain Names: `dnssec-validator.bondit.dk`
   - Scheme: `http`
   - Forward Hostname/IP: `dnssec-validator-prod` (container name)
   - Forward Port: `8080`
   - Cache Assets: ✅ Enabled
   - Block Common Exploits: ✅ Enabled
   - Websockets Support: ✅ Enabled

3. **SSL Tab**:
   - SSL Certificate: Request a new SSL certificate
   - Force SSL: ✅ Enabled
   - HTTP/2 Support: ✅ Enabled
   - HSTS Enabled: ✅ Enabled
   - HSTS Subdomains: ✅ Enabled

### 2. Advanced Configuration

Add custom Nginx configuration for better performance:

```nginx
# Security headers (additional to Flask-Talisman)
add_header X-Robots-Tag "noindex, nofollow, nosnippet, noarchive" always;
add_header X-Permitted-Cross-Domain-Policies "none" always;

# Performance optimizations
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# API rate limiting
location /api/ {
    limit_req zone=api burst=20 nodelay;
    limit_req_status 429;
}

# Health check endpoint
location /health {
    access_log off;
    return 200 "healthy\\n";
    add_header Content-Type text/plain;
}
```

## 🔧 Production Configuration

### Environment Variables

| Variable | Value | Description |
|----------|--------|-------------|
| `FLASK_ENV` | `production` | Enables production mode |
| `CORS_ORIGINS` | `https://dnssec-validator.bondit.dk` | Restricts CORS to production domain |

### Security Considerations

1. **HTTPS Enforcement**: All traffic redirected to HTTPS
2. **CORS Restriction**: Only production domain allowed
3. **Rate Limiting**: API and web requests are rate limited
4. **Security Headers**: Comprehensive security headers applied
5. **Health Checks**: Container health monitoring enabled

## 📊 Monitoring and Maintenance

### Health Checks

The container includes health checks that:
- Test the application every 30 seconds
- Timeout after 10 seconds
- Retry 3 times before marking unhealthy
- Wait 60 seconds before first check

### Log Monitoring

Access logs via Portainer:
1. Go to **Containers** → **dnssec-validator-prod**
2. Click **Logs** tab
3. Monitor for errors and performance issues

### Updates

To update the application:

1. **Via Portainer Web UI**:
   - Go to Stack → **dnssec-validator**
   - Click **Editor** tab
   - Update image tag if needed
   - Click **Update the stack**

2. **Via Portainer API**:
   ```bash
   curl -X PUT "https://portainer.bonde.ninja/api/stacks/{id}" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -d @updated-stack.json
   ```

## 🔄 Backup and Recovery

### Container Data

The application is stateless, but consider backing up:
- Container logs
- Portainer stack configuration
- Nginx Proxy Manager configuration

### Disaster Recovery

To restore service:
1. Deploy new container using `docker-compose.prod.yml`
2. Recreate Nginx Proxy Manager proxy host
3. Verify SSL certificate renewal

## 📈 Performance Optimization

### Nginx Proxy Manager Optimizations

- Enable HTTP/2
- Enable gzip compression
- Configure appropriate cache headers
- Use CDN for static assets (if needed)

### Container Optimizations

- Resource limits can be added if needed:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
  ```

## 🚨 Troubleshooting

### Common Issues

1. **Container Won't Start**
   - Check logs in Portainer
   - Verify environment variables
   - Ensure port 8080 is available

2. **SSL Certificate Issues**
   - Verify DNS points to correct server
   - Check Nginx Proxy Manager logs
   - Ensure port 80/443 are open

3. **API Not Responding**
   - Check container health status
   - Verify CORS configuration
   - Review application logs

### Support Contacts

- **Technical Issues**: Create issue on [GitHub](https://github.com/BondIT-ApS/dnssec-validator/issues)
- **Infrastructure**: Contact BondIT ApS support

## 🎉 Post-Deployment Verification

After deployment, verify:

1. **Web Interface**: [https://dnssec-validator.bondit.dk](https://dnssec-validator.bondit.dk)
2. **API Endpoint**: [https://dnssec-validator.bondit.dk/api/validate/bondit.dk](https://dnssec-validator.bondit.dk/api/validate/bondit.dk)
3. **API Documentation**: [https://dnssec-validator.bondit.dk/api/docs/](https://dnssec-validator.bondit.dk/api/docs/)
4. **SSL Certificate**: Verify SSL rating with SSL Labs
5. **Health Check**: Monitor container health in Portainer

---

**Deployment completed by BondIT ApS** ❤️
