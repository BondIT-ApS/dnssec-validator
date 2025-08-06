# InfluxDB Dashboard for DNSSEC Validator

This document explains how to set up and use the comprehensive InfluxDB dashboard for monitoring DNSSEC Validator analytics.

## Overview

The `influxdb-dashboard.json` file contains a pre-configured dashboard that provides comprehensive analytics for the DNSSEC Validator, including both external validation requests and internal system requests. This dashboard complements the web-based `/stats` page by showing the complete picture of system activity.

## Features

The dashboard includes the following visualizations:

### 1. **Hourly Request Volume** (Line Chart)
- Shows total request volume over time (including internal requests)
- Aggregated by hour for trend analysis

### 2. **Summary Statistics** (Single Stats - 24h window)
- **Total Requests**: All requests in last 24 hours
- **External Requests**: Only validation requests (excludes internal/system calls)  
- **Internal Requests**: System requests (analytics API, health checks, etc.)
- **Success Rate**: DNSSEC validation success rate (external requests only)

### 3. **External vs Internal Requests** (Multi-line Chart)
- Time series comparison showing external validation requests vs internal system requests
- Color-coded: Green for external, Orange for internal

### 4. **DNSSEC Validation Results** (Pie Chart)
- Distribution of validation results (valid, invalid, error)
- Shows only external requests to focus on actual validations

### 5. **Top Domains** (Table)
- Most frequently requested domains
- Shows both internal and external classifications
- Limited to top 20 domains

### 6. **Request Sources** (Table)
- Breakdown by source (API, webapp, etc.)
- Shows internal/external classification

## Setup Instructions

### Method 1: Automatic Creation (Recommended)

1. Set the environment variable in your docker-compose.yml:
   ```yaml
   environment:
     - INFLUX_DB_CREATE_DASHBOARD=true
   ```

2. Restart your containers:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. Check the application logs to confirm dashboard creation:
   ```bash
   docker-compose logs dnssec-validator
   ```

### Method 2: Manual Import

1. Access the InfluxDB UI at `http://localhost:8086`
2. Log in with your credentials (default: admin/adminpassword)
3. Navigate to **Dashboards** in the left sidebar
4. Click **Create Dashboard** → **Import Dashboard**
5. Upload the `influxdb-dashboard.json` file
6. The dashboard will be created as "DNSSEC Validator Analytics (Complete)"

## Environment Variables

The following environment variables control dashboard creation:

| Variable | Description | Default |
|----------|-------------|---------|
| `INFLUX_DB_CREATE_DASHBOARD` | Set to `true` to automatically create dashboard on startup | `false` |
| `INFLUX_DB_INIT_WAIT` | Seconds to wait for InfluxDB to be ready before creating dashboard | `5` |

## Usage

1. **Access the Dashboard**: 
   - Navigate to `http://localhost:8086` 
   - Go to **Dashboards** → **DNSSEC Validator Analytics (Complete)**

2. **Time Range Selection**:
   - Use the time picker in the top-right to adjust the viewing window
   - Default queries show last 24 hours for stats, configurable range for charts

3. **Understanding the Data**:
   - **External requests**: Actual DNSSEC validation requests from users
   - **Internal requests**: System calls like `/analytics/*`, `/stats`, `/health/*`, `/docs`
   - **Total requests**: Sum of external + internal for complete system load picture

## Key Differences from `/stats` Page

| Feature | Web `/stats` Page | InfluxDB Dashboard |
|---------|------------------|-------------------|
| **Scope** | External requests only | All requests (external + internal) |
| **Time Range** | Fixed periods | Flexible time selection |
| **Data Retention** | Real-time queries | Historical data with retention |
| **Interactivity** | Basic charts | Full InfluxDB query capabilities |
| **System Load** | Hidden internal calls | Shows complete system activity |

## Monitoring Use Cases

### For Developers
- **System Health**: Monitor internal vs external request ratios
- **Performance**: Identify peak usage periods
- **Debugging**: See complete request patterns including internal calls

### for Operations
- **Capacity Planning**: Understand total system load (not just user requests)
- **Alerting**: Set up alerts based on request volume or success rates
- **Trends**: Long-term analysis of system usage patterns

### For Users
- **Service Quality**: DNSSEC validation success rates over time
- **Popular Domains**: Most frequently validated domains
- **API Usage**: Understanding of API vs web interface usage

## Customization

You can modify the `influxdb-dashboard.json` file to:
- Adjust time ranges in queries
- Change visualization types
- Add new panels with custom Flux queries
- Modify colors and styling

After making changes, re-import the dashboard or recreate it using the environment variable method.

## Troubleshooting

### Dashboard Creation Fails
- Check InfluxDB connectivity: `docker-compose logs influxdb`
- Verify environment variables are set correctly
- Ensure `influxdb-dashboard.json` file exists in project root

### Missing Data in Charts
- Verify requests are being logged: check application logs
- Ensure correct bucket name in environment variables
- Check time range selection in dashboard

### Performance Issues
- Consider adjusting query time ranges for large datasets
- InfluxDB automatically handles retention (default: 90 days)
- Use downsampling for long-term historical data

## Data Schema

The dashboard queries data with the following structure:
- **Measurement**: `request`
- **Tags**: `domain`, `source`, `dnssec_status`, `ip_address`, `internal`
- **Fields**: `http_status`, `count`, `user_agent`
- **Timestamp**: Automatic InfluxDB timestamp

This matches the logging format used by the DNSSEC Validator application.
