# Enterprise Web Scraper - Deployment & Operations Guide

This guide covers deployment, configuration, monitoring, and operational procedures for the Enterprise Web Scraper.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Operations](#operations)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Scaling](#scaling)

## Quick Start

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/enterprise-web-scraper.git
cd enterprise-web-scraper

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Run basic tests
python -m pytest tests/

# Run a simple scrape
web-scraper scrape --site truckpro --search "brake pads" --debug
```

### Docker Quick Start

```bash
# Build and run with docker-compose
docker-compose up -d

# Run a scraping operation
docker-compose exec scraper web-scraper scrape --site truckpro --search "brake pads"

# View logs
docker-compose logs -f scraper

# Access monitoring
open http://localhost:3000  # Grafana (admin/admin)
open http://localhost:9090  # Prometheus
```

## Installation Methods

### Method 1: Pip Installation

```bash
# From PyPI (when published)
pip install enterprise-web-scraper

# From source
pip install git+https://github.com/yourorg/enterprise-web-scraper.git

# With all optional dependencies
pip install enterprise-web-scraper[all]
```

### Method 2: Development Installation

```bash
git clone https://github.com/yourorg/enterprise-web-scraper.git
cd enterprise-web-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install in development mode
pip install -e .[dev]

# Setup pre-commit hooks
pre-commit install
```

### Method 3: Docker Installation

```bash
# Pull from registry (when published)
docker pull yourorg/enterprise-web-scraper:latest

# Or build locally
docker build -t enterprise-web-scraper .
```

## Configuration

### Configuration Files

Create your configuration files based on the examples:

```bash
# Copy example configuration
cp config_examples.json config.json

# Edit for your environment
vim config.json
```

### Environment Variables

```bash
# Core settings
export LOG_LEVEL=INFO
export ENVIRONMENT=production
export CONFIG_PATH=/app/config/config.json

# Database (optional)
export DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (optional)
export REDIS_URL=redis://host:6379/0

# Monitoring
export METRICS_ENABLED=true
export PROMETHEUS_PORT=9090

# Rate Limiting
export GLOBAL_RATE_LIMIT=1.0
export ENABLE_RATE_LIMITING=true
```

### Site-Specific Configuration

Example TruckPro configuration:

```json
{
  "sites": {
    "truckpro": {
      "site_name": "TruckPro",
      "target_url": "https://www.truckpro.com/",
      "scraping": {
        "search_input_selectors": ["#searchInput"],
        "search_button_selectors": ["//button[contains(@class, 'search-button')]"],
        "product_card_selectors": ["div.productlist"],
        "max_results_per_query": 10,
        "wait_timeout": 10,
        "page_load_timeout": 30
      },
      "rate_limiting": {
        "requests_per_second": 1.0,
        "burst_allowance": 3
      }
    }
  }
}
```

## Docker Deployment

### Single Container Deployment

```bash
# Basic run
docker run -d \
  --name enterprise-scraper \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  enterprise-web-scraper

# With environment variables
docker run -d \
  --name enterprise-scraper \
  -e LOG_LEVEL=INFO \
  -e ENVIRONMENT=production \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  enterprise-web-scraper \
  web-scraper scrape --site truckpro --search "brake pads"
```

### Docker Compose Deployment

```bash
# Full stack deployment
docker-compose up -d

# Development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# With logging stack
docker-compose --profile logging up -d

# Scale workers
docker-compose up -d --scale worker=3
```

### Service Management

```bash
# View running services
docker-compose ps

# View logs
docker-compose logs -f scraper
docker-compose logs -f api

# Restart services
docker-compose restart scraper

# Update services
docker-compose pull
docker-compose up -d

# Backup data
docker run --rm -v enterprise-scraper_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup_$(date +%Y%m%d_%H%M%S).tar.gz /data
```

## Production Deployment

### Prerequisites

- Docker and Docker Compose
- SSL certificates (for HTTPS)
- Domain name and DNS configuration
- Monitoring setup (Prometheus, Grafana)
- Log aggregation (ELK stack - optional)

### Production Setup

1. **Prepare the environment:**

```bash
# Create production directory
mkdir -p /opt/enterprise-scraper
cd /opt/enterprise-scraper

# Clone the repository
git clone https://github.com/yourorg/enterprise-web-scraper.git .

# Create production configuration
cp config_examples.json config/production.json
```

2. **Configure SSL:**

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Copy your SSL certificates
cp yourdomain.crt nginx/ssl/
cp yourdomain.key nginx/ssl/
```

3. **Configure Nginx:**

```nginx
# nginx/nginx.conf
upstream api_backend {
    server api:8000;
}

upstream grafana_backend {
    server grafana:3000;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/yourdomain.crt;
    ssl_certificate_key /etc/nginx/ssl/yourdomain.key;

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /monitoring/ {
        proxy_pass http://grafana_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **Deploy:**

```bash
# Deploy the stack
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose ps
curl -k https://yourdomain.com/api/health
```

### Production Environment Variables

```bash
# .env file for production
ENVIRONMENT=production
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://scraper:your_secure_password@postgres:5432/scraper_db
REDIS_URL=redis://redis:6379/0
METRICS_ENABLED=true
SSL_CERT_PATH=/etc/nginx/ssl/yourdomain.crt
SSL_KEY_PATH=/etc/nginx/ssl/yourdomain.key
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

## Monitoring & Observability

### Metrics Collection

The scraper automatically collects metrics on:

- **Performance**: Request duration, success rates, error rates
- **Resource Usage**: Memory, CPU, network
- **Business Metrics**: Products scraped, search success rates
- **Operational**: Rate limiting, queue sizes, worker health

### Prometheus Metrics

Key metrics exposed:

```
# Performance metrics
scraper_request_duration_seconds
scraper_request_total
scraper_errors_total

# Business metrics
scraper_products_scraped_total
scraper_searches_performed_total
scraper_sites_scraped_total

# Resource metrics
scraper_memory_usage_bytes
scraper_cpu_usage_percent
```

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (admin/admin) and import dashboards:

1. **Scraper Overview**: High-level performance metrics
2. **Site Performance**: Per-site success rates and timing
3. **Error Analysis**: Error rates and types
4. **Resource Monitoring**: CPU, memory, and network usage
5. **Business Intelligence**: Scraping volume and trends

### Alerting

Configure alerts in Grafana for:

- High error rates (>10%)
- Slow response times (>30s average)
- Low success rates (<85%)
- Resource exhaustion (>80% memory/CPU)
- Queue backlog (>100 pending tasks)

### Log Management

**Structured Logging:**
```python
# Logs are structured JSON for easy parsing
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "component": "scraper",
  "site": "truckpro",
  "operation": "search",
  "search_term": "brake pads",
  "duration": 2.5,
  "results_count": 8,
  "success": true
}
```

**ELK Stack (Optional):**
```bash
# Enable logging stack
docker-compose --profile logging up -d

# Access Kibana
open http://localhost:5601
```

## Operations

### Daily Operations

```bash
# Check system health
docker-compose exec scraper web-scraper config validate config.json

# Run performance benchmarks
docker-compose exec scraper python performance_benchmarks.py

# Generate daily report
docker-compose exec scraper web-scraper report --metrics /app/data/metrics.json

# Check for configuration drift
docker-compose exec scraper web-scraper test --component all
```

### Scheduled Tasks

```bash
# Add to crontab
0 2 * * * /opt/enterprise-scraper/scripts/daily_backup.sh
0 6 * * * /opt/enterprise-scraper/scripts/performance_report.sh
*/15 * * * * /opt/enterprise-scraper/scripts/health_check.sh
```

### Backup and Recovery

**Automated Backup:**
```bash
#!/bin/bash
# scripts/daily_backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/enterprise-scraper"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U scraper scraper_db > $BACKUP_DIR/db_backup_$DATE.sql

# Backup configuration
tar czf $BACKUP_DIR/config_backup_$DATE.tar.gz config/

# Backup data
tar czf $BACKUP_DIR/data_backup_$DATE.tar.gz data/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

**Recovery:**
```bash
# Restore database
docker-compose exec -T postgres psql -U scraper scraper_db < backup_file.sql

# Restore configuration
tar xzf config_backup.tar.gz

# Restart services
docker-compose restart
```

### Scaling Operations

**Horizontal Scaling:**
```bash
# Scale worker processes
docker-compose up -d --scale worker=5

# Scale across multiple machines
docker swarm init
docker stack deploy -c docker-compose.yml scraper-stack
```

**Vertical Scaling:**
```yaml
# Increase resource limits
services:
  scraper:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
```

## Troubleshooting

### Common Issues

**1. Chrome/WebDriver Issues:**
```bash
# Check Chrome installation
docker-compose exec scraper google-chrome --version
docker-compose exec scraper chromedriver --version

# Fix permission issues
docker-compose exec scraper chown -R scraper:scraper /app/data
```

**2. Memory Issues:**
```bash
# Monitor memory usage
docker stats

# Increase shared memory for Chrome
# Add to docker-compose.yml:
shm_size: 2gb
```

**3. Rate Limiting:**
```bash
# Check rate limiting status
docker-compose exec scraper python -c "
from rate_limiter import DomainBasedRateLimiter, RateLimitConfig
config = RateLimitConfig()
limiter = DomainBasedRateLimiter(config)
print(limiter.get_domain_stats())
"
```

**4. Configuration Issues:**
```bash
# Validate configuration
docker-compose exec scraper web-scraper config validate config.json

# Test site accessibility
docker-compose exec scraper curl -I https://www.truckpro.com/
```

### Debug Mode

```bash
# Enable debug logging
docker-compose exec scraper web-scraper scrape \
  --site truckpro \
  --search "test" \
  --debug \
  --screenshots \
  --log-level DEBUG
```

### Performance Issues

```bash
# Run performance analysis
docker-compose exec scraper python performance_benchmarks.py

# Profile memory usage
docker-compose exec scraper python -m memory_profiler example_usage.py

# Check database performance
docker-compose exec postgres psql -U scraper -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;
"
```

## Security

### Security Best Practices

1. **Container Security:**
   - Run as non-root user
   - Use minimal base images
   - Regular security updates
   - Network isolation

2. **Secrets Management:**
   - Use Docker secrets for sensitive data
   - Environment variables for configuration
   - Encrypted storage for credentials

3. **Network Security:**
   - TLS/SSL for all external communications
   - Internal network isolation
   - Firewall rules for exposed ports

4. **Access Control:**
   - API authentication and authorization
   - Role-based access control
   - Audit logging

### Security Configuration

```yaml
# docker-compose.yml security additions
services:
  scraper:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    cap_drop:
      - ALL
    cap_add:
      - SYS_PTRACE  # Only if debugging needed
```

## Scaling

### Horizontal Scaling Strategies

1. **Multi-Site Deployment:**
   - Separate scraper instances per site
   - Load balancing across instances
   - Site-specific rate limiting

2. **Worker Scaling:**
   - Scale worker processes based on queue depth
   - Auto-scaling with Docker Swarm or Kubernetes
   - Circuit breakers for failed sites

3. **Database Scaling:**
   - Read replicas for reporting
   - Partitioning by site or date
   - Connection pooling

### Kubernetes Deployment

```yaml
# k8s/scraper-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: enterprise-scraper
spec:
  replicas: 3
  selector:
    matchLabels:
      app: enterprise-scraper
  template:
    metadata:
      labels:
        app: enterprise-scraper
    spec:
      containers:
      - name: scraper
        image: enterprise-web-scraper:latest
        resources:
          limits:
            memory: "2Gi"
            cpu: "1000m"
          requests:
            memory: "1Gi"
            cpu: "500m"
        env:
        - name: CONFIG_PATH
          value: "/app/config/config.json"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: data
          mountPath: /app/data
      volumes:
      - name: config
        configMap:
          name: scraper-config
      - name: data
        persistentVolumeClaim:
          claimName: scraper-data
```

### Performance Optimization

1. **Chrome Optimization:**
   - Disable unnecessary features
   - Use shared memory for better performance
   - Pool browser instances

2. **Database Optimization:**
   - Index frequently queried columns
   - Implement caching strategies
   - Use connection pooling

3. **Network Optimization:**
   - HTTP/2 connections
   - Connection reuse
   - Compression

4. **Caching:**
   - Redis for temporary data
   - CDN for static assets
   - Application-level caching

## Support and Maintenance

### Regular Maintenance Tasks

- **Weekly**: Update dependencies, review performance metrics
- **Monthly**: Security patches, configuration review
- **Quarterly**: Capacity planning, disaster recovery testing
- **Annually**: Architecture review, technology updates

### Monitoring Checklist

- [ ] All services running and healthy
- [ ] Error rates within acceptable limits
- [ ] Response times meeting SLA requirements
- [ ] Resource utilization within normal ranges
- [ ] Backup processes completing successfully
- [ ] Security patches up to date
- [ ] Configuration drift monitoring
- [ ] Capacity planning metrics

This deployment guide provides a comprehensive foundation for running the Enterprise Web Scraper in production environments. Adjust configurations based on your specific requirements and infrastructure.