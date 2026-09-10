# Phase 9 Deployment Guide

Complete guide for deploying the database-driven test case generator with Jira sync.

---

## Prerequisites

- **Python 3.8+**
- **PostgreSQL 12+**
- **Git**
- **pip** (Python package manager)

---

## Step 1: Environment Setup

### 1.1 Clone Repository

```bash
git clone <repo-url>
cd automation-dashboard
```

### 1.2 Create Python Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 1.3 Install Dependencies

```bash
pip install -r requirements.txt
```

Verify critical packages:
```bash
pip list | grep -E "SQLAlchemy|psycopg2|anthropic|openai"
```

---

## Step 2: Database Setup

### 2.1 Install PostgreSQL

**Windows:**
```bash
# Download from https://www.postgresql.org/download/windows/
# Run installer, note the password for postgres user
choco install postgresql
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
```

**Mac:**
```bash
brew install postgresql
brew services start postgresql
```

### 2.2 Create Database and User

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql prompt:
CREATE USER automation_user WITH PASSWORD 'automation_password';
CREATE DATABASE automation_dashboard OWNER automation_user;
GRANT ALL PRIVILEGES ON DATABASE automation_dashboard TO automation_user;
\q
```

### 2.3 Verify Connection

```bash
psql -U automation_user -d automation_dashboard -h localhost
# Should connect without error
\q
```

### 2.4 Initialize Schema

```bash
# Set environment variable
export DATABASE_URL="postgresql://automation_user:automation_password@localhost:5432/automation_dashboard"

# Initialize database
python database/init_db.py

# Check status
python database/init_db.py --check
```

Expected output:
```
✓ Found 8 tables:
  - acceptance_criteria_coverage: 0 rows
  - jira_custom_fields: 0 rows
  - jira_issues: 0 rows
  - project_settings: 1 rows
  - sessions: 0 rows
  - sync_history: 0 rows
  - test_case_generations: 0 rows
  - test_scenarios: 0 rows
```

---

## Step 3: Environment Configuration

### 3.1 Create .env File

```bash
# Copy template
cp .env.example .env

# Edit .env with your settings
```

### 3.2 Configure Variables

```bash
# Database
DATABASE_URL=postgresql://automation_user:automation_password@localhost:5432/automation_dashboard

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Server
SERVER_PORT=6060
SERVER_HOST=localhost

# Optional: Jira defaults
JIRA_BASE_URL=https://retech.atlassian.net
JIRA_PROJECT_KEY=REB3
```

### 3.3 Verify Configuration

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('DATABASE_URL:', os.getenv('DATABASE_URL', 'NOT SET'))"
```

---

## Step 4: Run Development Server

### 4.1 Start Server

```bash
python server.py
```

Expected output:
```
======================================================================
Automation Dashboard - Local Development Server
======================================================================
✓ Server running on: http://localhost:6060
✓ Dashboard available at: http://localhost:6060/index.html
✓ Press CTRL+C to stop server
======================================================================
```

### 4.2 Access Dashboard

Open browser: `http://localhost:6060`

### 4.3 Test Database Connection

1. Click "Generate Test Cases" button
2. Enter credentials dialog
3. Verify connection with "Verify Credentials" button
4. Should show: ✓ Credentials verified

---

## Step 5: Testing

### 5.1 Run Unit Tests

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_repositories.py::TestSessionRepository::test_create_session PASSED
tests/test_repositories.py::TestSessionRepository::test_get_session_by_email PASSED
tests/test_repositories.py::TestSessionRepository::test_session_expiry PASSED
...
```

### 5.2 Run Specific Test

```bash
pytest tests/test_repositories.py::TestSessionRepository -v
```

### 5.3 Run with Coverage

```bash
pytest tests/ --cov=database --cov=sync --cov=api --cov-report=html
```

---

## Step 6: End-to-End Testing

### 6.1 Manual Workflow Test

```
1. Start server: python server.py
2. Open browser: http://localhost:6060
3. Click "Generate Test Cases"
4. Enter Jira credentials (real or test)
5. Click "Verify Credentials" - should succeed
6. Select issue (e.g., REB3-101)
7. Click "Generate" - should create scenarios
8. Scenarios appear in review panel
9. Click "Approve" on a scenario
10. Click "Sync to Jira" button
11. Should see progress and success
12. Verify child issue created in Jira
```

### 6.2 Test Endpoints with curl

**Create Session:**
```bash
curl -X POST http://localhost:6060/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "test@example.com",
    "jira_base_url": "https://retech.atlassian.net",
    "jira_email": "user@company.com",
    "jira_api_token": "token123",
    "ai_provider": "anthropic",
    "anthropic_api_key": "sk-ant-..."
  }'
```

**Get Pending Scenarios:**
```bash
curl http://localhost:6060/api/jira/pending-syncs
```

**Sync Pending:**
```bash
curl -X POST http://localhost:6060/api/jira/sync-pending \
  -H "Content-Type: application/json" \
  -d '{
    "jira_base_url": "https://retech.atlassian.net",
    "jira_email": "user@company.com",
    "jira_api_token": "token123"
  }'
```

---

## Step 7: Production Deployment

### 7.1 Pre-Deployment Checklist

- [ ] All tests passing (pytest tests/ -v)
- [ ] Database backup created
- [ ] Environment variables configured
- [ ] SSL/TLS certificates ready (for HTTPS)
- [ ] Load balancer configured (if applicable)
- [ ] Monitoring/logging setup
- [ ] Security review completed

### 7.2 Database Backup

```bash
# Backup production database
pg_dump -U automation_user automation_dashboard > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup size check
du -h backup_*.sql
```

### 7.3 Restore from Backup

```bash
# Create new database
psql -U postgres -c "CREATE DATABASE automation_dashboard_restore"

# Restore from backup
psql -U automation_user automation_dashboard_restore < backup_20260910_120000.sql

# Verify
psql -U automation_user automation_dashboard_restore -c "SELECT COUNT(*) FROM test_scenarios;"
```

### 7.4 Deploy Application

**Option A: Docker Container**

```bash
# Build image
docker build -t automation-dashboard:phase9 .

# Run container
docker run -d \
  -p 6060:6060 \
  -e DATABASE_URL="postgresql://user:pass@db-host:5432/automation_dashboard" \
  --name automation-dashboard \
  automation-dashboard:phase9
```

**Option B: Systemd Service**

Create `/etc/systemd/system/automation-dashboard.service`:
```ini
[Unit]
Description=Automation Dashboard
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/automation-dashboard
ExecStart=/opt/automation-dashboard/venv/bin/python server.py
Restart=always
RestartSec=10

Environment="DATABASE_URL=postgresql://automation_user:password@localhost:5432/automation_dashboard"
Environment="LOG_LEVEL=INFO"

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl start automation-dashboard
sudo systemctl enable automation-dashboard
sudo systemctl status automation-dashboard
```

### 7.5 Configure Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name dashboard.company.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:6060;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 7.6 Monitor Application

```bash
# Check logs
tail -f logs/app.log

# Monitor processes
watch -n 1 'ps aux | grep python'

# Check database connections
psql -U automation_user automation_dashboard -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Step 8: Troubleshooting

### Issue: Database Connection Failed

```
Error: could not connect to server: Connection refused
```

**Solution:**
```bash
# Verify PostgreSQL is running
sudo service postgresql status

# Check connection string
echo $DATABASE_URL

# Test connection
psql -U automation_user -d automation_dashboard -h localhost -c "SELECT 1"
```

### Issue: Import Errors

```
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify installation
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

### Issue: Port Already in Use

```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 6060
lsof -i :6060

# Kill process
kill -9 <PID>

# Or use different port
python server.py --port 6061
```

### Issue: Sync to Jira Fails

```
Error: 401 Unauthorized
```

**Solution:**
- Verify Jira API token is correct
- Check token hasn't expired
- Verify user email is correct
- Test with curl:
  ```bash
  curl -u email@company.com:token https://jira.atlassian.net/rest/api/3/myself
  ```

---

## Step 9: Monitoring & Maintenance

### 9.1 Log Monitoring

```bash
# View recent errors
grep -i error logs/app.log | tail -20

# Monitor in real-time
tail -f logs/app.log | grep -E "ERROR|CRITICAL"

# Log rotation setup (logrotate)
# Create /etc/logrotate.d/automation-dashboard
/opt/automation-dashboard/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
```

### 9.2 Database Maintenance

```bash
# Analyze and optimize tables (weekly)
psql -U automation_user automation_dashboard -c "ANALYZE;"

# Vacuum (removes dead rows, monthly)
psql -U automation_user automation_dashboard -c "VACUUM ANALYZE;"

# Check index usage
psql -U automation_user automation_dashboard -c "
  SELECT schemaname, tablename, indexname, idx_scan 
  FROM pg_stat_user_indexes 
  ORDER BY idx_scan DESC;"
```

### 9.3 Performance Monitoring

```bash
# Check active connections
psql -U automation_user automation_dashboard -c "
  SELECT pid, usename, query, state 
  FROM pg_stat_activity 
  WHERE state != 'idle';"

# Slow query log
psql -U postgres -d automation_dashboard -c "
  ALTER SYSTEM SET log_min_duration_statement = 1000;
  SELECT pg_reload_conf();"
```

### 9.4 Health Check Endpoint (Optional)

Add to server.py:
```python
@app.route('/health')
def health_check():
    # Check database
    try:
        session = db_manager.get_session()
        session.execute(text("SELECT 1"))
        session.close()
        return {"status": "healthy", "database": "connected"}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503
```

Monitor with:
```bash
curl http://localhost:6060/health
watch -n 5 'curl -s http://localhost:6060/health | jq'
```

---

## Step 10: Rollback Procedures

### 10.1 Application Rollback

```bash
# Stop current version
sudo systemctl stop automation-dashboard

# Checkout previous version
git checkout HEAD~1

# Reinstall dependencies (if needed)
pip install -r requirements.txt

# Start previous version
sudo systemctl start automation-dashboard
```

### 10.2 Database Rollback

```bash
# If schema migration failed:
psql -U automation_user automation_dashboard < backup_20260910_120000.sql

# If data corruption occurred:
# 1. Restore from backup
# 2. Replay transaction log (if available)
# 3. Notify users of data loss window
```

---

## Verification Checklist

After deployment, verify:

- [ ] Server is running: `curl http://localhost:6060/`
- [ ] Database connected: `python database/init_db.py --check`
- [ ] All 8 tables present
- [ ] Tests passing: `pytest tests/ -q`
- [ ] Jira credentials work: Test with verify endpoint
- [ ] Scenario generation works: End-to-end test
- [ ] Sync to Jira works: Create and verify child issue
- [ ] Logs are being written: `tail logs/app.log`
- [ ] Backups are scheduled: `crontab -l | grep pg_dump`
- [ ] Monitoring is active: Check logs/metrics

---

## Support & Contacts

- **Database Issues**: Check PostgreSQL logs: `/var/log/postgresql/`
- **Application Issues**: Check app logs: `logs/app.log`
- **Jira Integration**: Test with `/api/verify-credentials` endpoint
- **Performance Issues**: Monitor with PostgreSQL admin queries

---

## Emergency Contacts

- Database Admin: [contact]
- Jira Admin: [contact]
- DevOps: [contact]

---

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Jira Cloud API](https://developer.atlassian.com/cloud/jira/rest/)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
