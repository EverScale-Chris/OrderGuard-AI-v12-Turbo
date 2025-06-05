# Phase 7: Production Deployment and Launch

## Overview
Prepare and deploy the application to production, ensuring security, performance, and reliability for B2B SaaS operations.

## Prerequisites
- All previous phases completed
- Production Supabase project created
- Production Stripe account verified
- Domain name registered
- SSL certificate ready

## Step-by-Step Implementation

### Step 1: Security Audit

1. **Environment variables audit**
   ```python
   # scripts/security_audit.py
   import os
   from dotenv import load_dotenv
   
   def audit_env_vars():
       """Ensure all sensitive data is in env vars"""
       required_vars = [
           'SUPABASE_URL',
           'SUPABASE_ANON_KEY',
           'SUPABASE_SERVICE_KEY',
           'STRIPE_SECRET_KEY',
           'STRIPE_PUBLISHABLE_KEY',
           'STRIPE_WEBHOOK_SECRET',
           'SESSION_SECRET',
           'SENDGRID_API_KEY',
           'REDIS_URL',
           'APP_URL'
       ]
       
       missing = []
       for var in required_vars:
           if not os.environ.get(var):
               missing.append(var)
       
       if missing:
           print(f"❌ Missing environment variables: {missing}")
           return False
       
       print("✅ All required environment variables present")
       return True
   
   def check_secret_strength():
       """Verify secret keys are strong"""
       session_secret = os.environ.get('SESSION_SECRET', '')
       
       if len(session_secret) < 32:
           print("❌ SESSION_SECRET should be at least 32 characters")
           return False
       
       print("✅ Secret keys appear strong")
       return True
   ```

2. **SQL injection prevention**
   ```python
   # utils/security.py
   import re
   from functools import wraps
   from flask import request, jsonify
   
   def sanitize_input(input_string):
       """Sanitize user input"""
       if not input_string:
           return input_string
       
       # Remove SQL keywords
       sql_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'UNION', 'SELECT']
       for keyword in sql_keywords:
           input_string = re.sub(f'\\b{keyword}\\b', '', input_string, flags=re.IGNORECASE)
       
       # Escape special characters
       input_string = input_string.replace("'", "''")
       
       return input_string
   
   def rate_limit(max_requests=60, window=60):
       """Rate limiting decorator"""
       def decorator(f):
           @wraps(f)
           def wrapped(*args, **kwargs):
               # Implementation would use Redis
               # Check request count for IP
               # Return 429 if exceeded
               return f(*args, **kwargs)
           return wrapped
       return decorator
   ```

3. **CORS and security headers**
   ```python
   # Add to app.py
   from flask_cors import CORS
   from flask_talisman import Talisman
   
   # Configure CORS
   CORS(app, origins=[os.environ.get('APP_URL')])
   
   # Force HTTPS and security headers
   Talisman(app, force_https=True)
   
   @app.after_request
   def set_security_headers(response):
       response.headers['X-Content-Type-Options'] = 'nosniff'
       response.headers['X-Frame-Options'] = 'DENY'
       response.headers['X-XSS-Protection'] = '1; mode=block'
       response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
       return response
   ```

### Step 2: Performance Optimization

1. **Database connection pooling**
   ```python
   # utils/db_config.py
   from sqlalchemy import create_engine
   from sqlalchemy.pool import QueuePool
   
   def create_production_engine():
       """Create optimized database engine"""
       return create_engine(
           os.environ.get('DATABASE_URL'),
           poolclass=QueuePool,
           pool_size=20,
           max_overflow=40,
           pool_pre_ping=True,
           pool_recycle=300
       )
   ```

2. **Response compression**
   ```python
   # Add to app.py
   from flask_compress import Compress
   
   # Enable compression
   Compress(app)
   
   # Configure compression
   app.config['COMPRESS_MIMETYPES'] = [
       'text/html', 'text/css', 'text/xml',
       'application/json', 'application/javascript'
   ]
   app.config['COMPRESS_LEVEL'] = 6
   app.config['COMPRESS_MIN_SIZE'] = 500
   ```

3. **Static file optimization**
   ```bash
   # scripts/optimize_static.sh
   #!/bin/bash
   
   # Minify CSS
   for file in static/css/*.css; do
       if [[ ! "$file" =~ \.min\.css$ ]]; then
           cssnano "$file" "${file%.css}.min.css"
       fi
   done
   
   # Minify JavaScript
   for file in static/js/*.js; do
       if [[ ! "$file" =~ \.min\.js$ ]]; then
           terser "$file" -o "${file%.js}.min.js" -c -m
       fi
   done
   
   # Optimize images
   for file in static/images/*; do
       optipng -o7 "$file"
   done
   ```

### Step 3: Monitoring Setup

1. **Application monitoring**
   ```python
   # utils/monitoring.py
   import sentry_sdk
   from sentry_sdk.integrations.flask import FlaskIntegration
   from prometheus_flask_exporter import PrometheusMetrics
   
   def init_monitoring(app):
       """Initialize monitoring tools"""
       
       # Sentry for error tracking
       sentry_sdk.init(
           dsn=os.environ.get('SENTRY_DSN'),
           integrations=[FlaskIntegration()],
           traces_sample_rate=0.1,
           environment=os.environ.get('ENVIRONMENT', 'production')
       )
       
       # Prometheus metrics
       metrics = PrometheusMetrics(app)
       
       # Custom metrics
       metrics.info('app_info', 'Application info',
                   version=os.environ.get('APP_VERSION', '1.0.0'))
       
       return metrics
   ```

2. **Health check endpoints**
   ```python
   # Add to app.py
   @app.route('/health')
   def health_check():
       """Basic health check"""
       return jsonify({
           'status': 'healthy',
           'timestamp': datetime.utcnow().isoformat()
       })
   
   @app.route('/health/detailed')
   @rate_limit(max_requests=10)
   def detailed_health():
       """Detailed health check"""
       checks = {
           'database': check_database_health(),
           'supabase': check_supabase_health(),
           'stripe': check_stripe_health(),
           'redis': check_redis_health()
       }
       
       all_healthy = all(check['healthy'] for check in checks.values())
       
       return jsonify({
           'status': 'healthy' if all_healthy else 'unhealthy',
           'checks': checks,
           'timestamp': datetime.utcnow().isoformat()
       }), 200 if all_healthy else 503
   ```

### Step 4: Deployment Configuration

1. **Production Dockerfile**
   ```dockerfile
   # Dockerfile
   FROM python:3.11-slim
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       postgresql-client \
       && rm -rf /var/lib/apt/lists/*
   
   # Set working directory
   WORKDIR /app
   
   # Copy requirements
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application
   COPY . .
   
   # Create non-root user
   RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
   USER appuser
   
   # Expose port
   EXPOSE 8000
   
   # Run with gunicorn
   CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "app:app"]
   ```

2. **Docker Compose for production**
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   
   services:
     web:
       build: .
       environment:
         - ENVIRONMENT=production
       env_file:
         - .env.production
       ports:
         - "8000:8000"
       depends_on:
         - redis
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
     
     redis:
       image: redis:7-alpine
       restart: unless-stopped
       volumes:
         - redis_data:/data
     
     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/nginx/ssl
       depends_on:
         - web
       restart: unless-stopped
   
   volumes:
     redis_data:
   ```

3. **Nginx configuration**
   ```nginx
   # nginx.conf
   events {
       worker_connections 1024;
   }
   
   http {
       upstream app {
           server web:8000;
       }
       
       server {
           listen 80;
           server_name orderguard.com;
           return 301 https://$server_name$request_uri;
       }
       
       server {
           listen 443 ssl http2;
           server_name orderguard.com;
           
           ssl_certificate /etc/nginx/ssl/cert.pem;
           ssl_certificate_key /etc/nginx/ssl/key.pem;
           
           # Security headers
           add_header X-Frame-Options "DENY" always;
           add_header X-Content-Type-Options "nosniff" always;
           add_header X-XSS-Protection "1; mode=block" always;
           
           # Proxy settings
           location / {
               proxy_pass http://app;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
           
           # Static files
           location /static {
               alias /app/static;
               expires 1y;
               add_header Cache-Control "public, immutable";
           }
       }
   }
   ```

### Step 5: Database Migration Strategy

1. **Production migration script**
   ```python
   # scripts/migrate_to_production.py
   import os
   from utils.supabase_client import get_supabase_client, get_supabase_admin_client
   
   def migrate_production():
       """Migrate data to production Supabase"""
       
       print("🚀 Starting production migration...")
       
       # 1. Create schema
       print("Creating schema...")
       run_schema_migrations()
       
       # 2. Set up RLS policies
       print("Setting up RLS policies...")
       setup_rls_policies()
       
       # 3. Create initial admin user
       print("Creating admin user...")
       create_admin_user()
       
       # 4. Set up Stripe webhooks
       print("Configuring Stripe webhooks...")
       configure_stripe_webhooks()
       
       # 5. Verify everything
       print("Running verification...")
       verify_production_setup()
       
       print("✅ Production migration complete!")
   ```

2. **Backup strategy**
   ```bash
   # scripts/backup.sh
   #!/bin/bash
   
   # Daily backup script
   BACKUP_DIR="/backups"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   # Backup Supabase data
   pg_dump $DATABASE_URL > "$BACKUP_DIR/db_backup_$DATE.sql"
   
   # Compress
   gzip "$BACKUP_DIR/db_backup_$DATE.sql"
   
   # Upload to S3
   aws s3 cp "$BACKUP_DIR/db_backup_$DATE.sql.gz" s3://orderguard-backups/
   
   # Clean old backups (keep 30 days)
   find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
   ```

### Step 6: Launch Checklist

1. **Pre-launch verification**
   ```python
   # scripts/pre_launch_check.py
   
   def pre_launch_checklist():
       """Run all pre-launch checks"""
       
       checks = {
           "Environment variables set": check_env_vars(),
           "Database accessible": check_database(),
           "Supabase RLS enabled": check_rls(),
           "Stripe webhooks configured": check_stripe_webhooks(),
           "SSL certificate valid": check_ssl(),
           "Monitoring active": check_monitoring(),
           "Backups configured": check_backups(),
           "Rate limiting enabled": check_rate_limiting(),
           "Error pages configured": check_error_pages(),
           "Terms of Service present": check_legal_pages()
       }
       
       print("\n🚀 PRE-LAUNCH CHECKLIST")
       print("=" * 50)
       
       all_passed = True
       for check, passed in checks.items():
           status = "✅" if passed else "❌"
           print(f"{status} {check}")
           if not passed:
               all_passed = False
       
       print("=" * 50)
       
       if all_passed:
           print("\n✅ All checks passed! Ready for launch!")
       else:
           print("\n❌ Some checks failed. Please fix before launching.")
       
       return all_passed
   ```

2. **Launch day procedures**
   ```markdown
   ## Launch Day Checklist
   
   ### Morning (T-4 hours)
   - [ ] Run final pre-launch checks
   - [ ] Verify all team members ready
   - [ ] Check monitoring dashboards
   - [ ] Confirm support channels ready
   
   ### Launch Time (T-0)
   - [ ] Deploy to production
   - [ ] Update DNS records
   - [ ] Enable Stripe live mode
   - [ ] Send launch announcement
   
   ### Post-Launch (T+1 hour)
   - [ ] Monitor error rates
   - [ ] Check performance metrics
   - [ ] Verify payment processing
   - [ ] Test user registration flow
   
   ### End of Day
   - [ ] Review metrics
   - [ ] Address any issues
   - [ ] Plan next day support
   ```

### Step 7: Post-Launch Operations

1. **Monitoring dashboard**
   ```python
   # Create Grafana dashboard config
   dashboard_config = {
       "dashboard": {
           "title": "OrderGuard Production Metrics",
           "panels": [
               {
                   "title": "Request Rate",
                   "targets": [{"expr": "rate(flask_http_request_total[5m])"}]
               },
               {
                   "title": "Error Rate",
                   "targets": [{"expr": "rate(flask_http_request_exceptions_total[5m])"}]
               },
               {
                   "title": "Response Time",
                   "targets": [{"expr": "histogram_quantile(0.95, flask_http_request_duration_seconds_bucket)"}]
               },
               {
                   "title": "Active Users",
                   "targets": [{"expr": "orderguard_active_users"}]
               }
           ]
       }
   }
   ```

2. **Incident response plan**
   ```markdown
   ## Incident Response Procedures
   
   ### Severity Levels
   - **P0**: Complete outage
   - **P1**: Major feature broken
   - **P2**: Minor feature issue
   - **P3**: Cosmetic issue
   
   ### Response Times
   - P0: Immediate (on-call)
   - P1: Within 1 hour
   - P2: Within 4 hours
   - P3: Next business day
   
   ### Escalation Path
   1. On-call engineer
   2. Team lead
   3. CTO
   4. CEO (P0 only)
   ```

## Deployment Commands

```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale workers
docker-compose -f docker-compose.prod.yml scale web=3

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python scripts/migrate_to_production.py
```

## Verification Checklist

- [ ] Security audit passed
- [ ] Performance benchmarks met
- [ ] Monitoring configured
- [ ] Backups automated
- [ ] SSL certificate installed
- [ ] Rate limiting active
- [ ] Error tracking enabled
- [ ] Health checks passing
- [ ] Documentation complete
- [ ] Team trained

## Performance Targets

- Page load time: < 2 seconds
- API response time: < 200ms (p95)
- Uptime: 99.9%
- Error rate: < 0.1%

## Congratulations! 🎉

Your OrderGuard B2B SaaS application is now ready for production. Remember to:

1. Monitor metrics closely for the first week
2. Be ready to scale based on demand
3. Gather user feedback actively
4. Plan your first feature updates
5. Celebrate your launch!

## Support Resources

- Documentation: docs.orderguard.com
- Status Page: status.orderguard.com
- Support Email: support@orderguard.com
- Emergency: on-call@orderguard.com 