# 📋 QR KARAOKE DATABASE DEPLOYMENT - STEP-BY-STEP CHECKLIST

## ✅ Pre-Deployment Checklist

### Environment Verification
- [ ] MySQL is installed and running
  ```powershell
  mysql --version
  ```
- [ ] Python 3.8+ is installed
  ```powershell
  python --version
  ```
- [ ] Virtual environment exists and can be activated
  ```powershell
  .\venv\Scripts\Activate.ps1  # Windows
  source venv/bin/activate     # Linux
  ```
- [ ] Required packages are installed
  ```bash
  pip list | grep -E "sqlalchemy|alembic|pymysql"
  ```

### Network & Connectivity
- [ ] Can connect to MySQL locally
  ```bash
  mysql -u root -p -e "SELECT 1"
  ```
- [ ] Can connect to VPS (if deploying remotely)
  ```bash
  ssh user@vps-ip "mysql -u root -p -e 'SELECT 1'"
  ```

### Backup Preparation
- [ ] Backups directory exists
  ```bash
  mkdir -p backups
  ls -la backups/
  ```
- [ ] Have access to backup storage (at least 1GB free)
  ```bash
  df -h backups/
  ```

---

## 📌 Phase 1: LOCAL TESTING (Windows)

### Step 1: Activate Python Environment
```powershell
# Navigate to project directory
cd C:\Users\MARCO_MESA\Documents\qr_karaoke_backend_render

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Verify activation (should show (venv) at prompt)
```
**Status:** ☐ Completed

### Step 2: Run Database Optimizer (Recommended)
```powershell
# Run the Python optimizer
python database_optimizer.py

# When prompted, enter:
# Host: localhost
# User: root
# Password: [your-mysql-password]
# Database: mi_base_datos
```
**Expected Output:**
- ✅ Conexión a MySQL verificada
- ✅ Backup creado: backups/backup_*.sql.gz
- ✅ Integridad de tablas verificada
- ✅ Optimización completada

**Status:** ☐ Completed

### Step 3: Verify Local Changes
```bash
# Check that migration ran
alembic current
# Should show: optimize_database_remove_unused_tables

# Verify new indices exist
mysql -u root -p mi_base_datos -e "SHOW INDEX FROM usuarios WHERE Key_name LIKE 'idx_%';"
```
**Expected Output:**
- 8+ new indices visible
- No errors about missing indices

**Status:** ☐ Completed

### Step 4: Test Application Locally
```bash
# Restart your application
# If using FastAPI directly
python main.py &

# Wait 5 seconds for startup
Start-Sleep -Seconds 5

# Test that API is responsive
curl http://localhost:8000/docs
# Or visit: http://localhost:8000/docs in browser
```
**Expected Output:**
- HTTP 200 response
- Swagger docs load successfully

**Status:** ☐ Completed

### Step 5: Monitor Local Logs
```bash
# Check for any errors
Get-Content logs/*.log -Tail 50 2>/dev/null | Select-String -Pattern "ERROR|CRITICAL"

# Or check application output for errors during startup
```
**Expected Output:**
- No ERROR or CRITICAL messages
- Application starts normally

**Status:** ☐ Completed

### Step 6: Quick Functional Test
Test these basic endpoints:

```powershell
# Test 1: Check users table (should not error)
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/usuarios" -UseBasicParsing
"✅ Users endpoint: $($response.StatusCode)"

# Test 2: Check songs table
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/canciones" -UseBasicParsing
"✅ Songs endpoint: $($response.StatusCode)"

# Test 3: Check queue
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/queue" -UseBasicParsing
"✅ Queue endpoint: $($response.StatusCode)"
```
**Expected Output:**
- All responses: HTTP 200

**Status:** ☐ Completed

---

## 🚀 Phase 2: VPS DEPLOYMENT (Linux)

### Step 1: Connect to VPS
```bash
# SSH into VPS
ssh ubuntu@your-vps-ip
# or
ssh user@your-vps-ip

# Navigate to project directory
cd /home/user/qr_karaoke_backend_render

# Verify you're in correct directory
pwd  # Should show: /home/user/qr_karaoke_backend_render
ls -la | head
```
**Status:** ☐ Completed

### Step 2: Activate Python Environment on VPS
```bash
# Activate virtual environment
source venv/bin/activate

# Verify activation (should show (venv) at prompt)
which python

# Verify version
python --version  # Should be 3.8+
```
**Status:** ☐ Completed

### Step 3: Stop Application (IMPORTANT!)
```bash
# If using systemd
sudo systemctl stop qr_karaoke

# Or if running directly:
pkill -f "python main.py"

# Wait for graceful shutdown
sleep 3

# Verify it's stopped
pgrep -f "python main.py" || echo "✅ Application stopped"
```
**Status:** ☐ Completed

### Step 4: Create Pre-Deployment Backup
```bash
# Create backup directory if needed
mkdir -p ./backups

# Create full database backup
echo "Creating backup... (this may take a few minutes)"
mysqldump -u root -p mi_base_datos | gzip > ./backups/pre_deployment_$(date +%Y%m%d_%H%M%S).sql.gz

# Verify backup was created
ls -lh ./backups/pre_deployment*.gz
# Should show file size of 10MB-100MB or more
```
**Expected Output:**
```
-rw-r--r-- 1 user user 45M Jan 15 10:23 ./backups/pre_deployment_20240115_102345.sql.gz
```

**Status:** ☐ Completed

### Step 5: Apply Database Migration
```bash
# Show current migration status
alembic current

# List available migrations
alembic heads

# Apply migration
echo "Applying migration..."
alembic upgrade head

# Verify migration was applied
alembic current
# Should show: optimize_database_remove_unused_tables
```
**Status:** ☐ Completed

### Step 6: Verify Table Changes
```bash
# Check that old tables are gone
echo "Checking for removed tables..."
mysql -u root -p -e "SHOW TABLES;" mi_base_datos | grep -E "admin_logs|banned_nicks|configuracion_global"
# Should return NO OUTPUT (tables successfully removed)

echo "✅ Old tables successfully removed"

# Check that new indices were added
echo "Checking indices..."
mysql -u root -p -e "SHOW INDEXES FROM usuarios" mi_base_datos | grep "idx_usuarios_banned"
# Should show the new index
```
**Expected Output:**
```
✅ Old tables successfully removed
Table   Non_unique  Key_name                 ...
usuarios    1         idx_usuarios_banned     ...
```

**Status:** ☐ Completed

### Step 7: Verify Data Integrity
```bash
# Check table integrity
echo "Verifying table integrity..."
mysql -u root -p -e "CHECK TABLE usuarios, canciones, consumos, mesas, cuentas, pagos, productos;" mi_base_datos

# Check for any errors or warnings
mysql -u root -p -e "SHOW ENGINES;" mi_base_datos | grep InnoDB
```
**Expected Output:**
```
Table                          Op      Msg_type   Msg_text
mi_base_datos.usuarios       check   status     OK
mi_base_datos.canciones      check   status     OK
...
```

**Status:** ☐ Completed

### Step 8: Verify Database Size
```bash
# Check new database size
mysql -u root -p -e "
SELECT 
    TABLE_NAME,
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS 'Size_MB'
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'mi_base_datos'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;" mi_base_datos
```
**Expected Output:**
```
TABLE_NAME          Size_MB
canciones           15.50
usuarios            8.25
consumos            12.10
...
(Should be 10-20% smaller than before)
```

**Status:** ☐ Completed

### Step 9: Restart Application
```bash
# If using systemd service
sudo systemctl start qr_karaoke

# Or if running directly (use tmux/screen for background)
python main.py &

# Wait for startup
sleep 5

# Verify it started
systemctl status qr_karaoke  # or pgrep -f "python main.py"
```
**Expected Output:**
```
● qr_karaoke.service - QR Karaoke Backend
   Active: active (running) since...
```

**Status:** ☐ Completed

### Step 10: Test VPS Application
```bash
# Test if API is responding
curl -s http://localhost:8000/docs | grep -q "Swagger" && echo "✅ API is responding"

# Test specific endpoints
curl -s http://localhost:8000/api/usuarios | head -20  # Check users
curl -s http://localhost:8000/api/queue | head -20     # Check queue

# Check for errors in latest logs
tail -50 logs/error.log 2>/dev/null | grep -i error || echo "✅ No errors in logs"
```
**Expected Output:**
```
✅ API is responding
✅ No errors in logs
[JSON response with users/queue data]
```

**Status:** ☐ Completed

---

## 🔍 Phase 3: VERIFICATION & MONITORING

### Step 1: 24-Hour Monitoring
- [ ] Monitor application for 24 hours after deployment
- [ ] Watch logs for any errors
  ```bash
  tail -f logs/error.log
  tail -f logs/performance.log  # if exists
  ```

### Step 2: Performance Verification
```bash
# Check query performance improvement
# Run a complex query and time it
mysql -u root -p mi_base_datos -e "
SELECT COUNT(*) FROM canciones 
WHERE estado = 'approved' AND created_at > DATE_SUB(NOW(), INTERVAL 7 DAY);" --verbose

# Compare with notes taken before deployment
```
**Expected:** Queries should be 2-5x faster

- [ ] Queries are responding faster
- [ ] No timeouts or slow query warnings

### Step 3: User Reports
- [ ] No user-reported issues after 24 hours
- [ ] Application responsiveness is normal or better
- [ ] Queue functionality works correctly
- [ ] Payments/consumption tracking works

### Step 4: Database Health Check
```bash
# Weekly health check
mysql -u root -p -e "
SELECT 
    DATE_NOW() as check_time,
    (SELECT COUNT(*) FROM usuarios) as user_count,
    (SELECT COUNT(*) FROM canciones) as song_count,
    (SELECT COUNT(*) FROM consumos) as consumption_count;" mi_base_datos

# Check for fragmentation (if >30%, run OPTIMIZE)
mysql -u root -p -e "
SELECT 
    TABLE_NAME, 
    ROUND((DATA_FREE / (DATA_LENGTH + INDEX_LENGTH))*100, 2) as frag_percent
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'mi_base_datos';" mi_base_datos
```

- [ ] All counts are expected values
- [ ] Fragmentation is < 30%
- [ ] No unexpected errors

---

## 🆘 ROLLBACK PROCEDURES

### If You Need to Rollback:

#### Option 1: Restore from Backup (Recommended)
```bash
# 1. Stop application
sudo systemctl stop qr_karaoke

# 2. List available backups
ls -lh ./backups/

# 3. Restore from backup
echo "Restoring database..."
gunzip < ./backups/pre_deployment_20240115_102345.sql.gz | mysql -u root -p mi_base_datos

# 4. Verify restoration
mysql -u root -p -e "SHOW TABLES;" mi_base_datos | wc -l
# Should show 12-14 tables (including old ones)

# 5. Restart application
sudo systemctl start qr_karaoke
```
**Time to rollback:** 5-15 minutes

**Status:** ☐ Completed (if needed)

#### Option 2: Downgrade Migration
```bash
# 1. Stop application
sudo systemctl stop qr_karaoke

# 2. Check migration history
alembic history

# 3. Downgrade to version before optimization
alembic downgrade -1  # Go back 1 version

# 4. Or downgrade to specific version (if needed)
alembic downgrade <version_id_before_optimization>

# 5. Restart application
sudo systemctl start qr_karaoke
```
**Time to rollback:** 2-5 minutes

**Status:** ☐ Completed (if needed)

---

## 📊 SUCCESS CRITERIA

### ✅ Deployment is Successful If:
- [x] No errors during migration
- [x] Old tables (admin_logs, banned_nicks, configuracion_global) are gone
- [x] Application starts without errors
- [x] All endpoints respond normally
- [x] Database size is similar or smaller
- [x] Queries are completing faster
- [x] No user-facing issues reported

### ❌ Rollback If:
- [ ] Application won't start after deployment
- [ ] Users report lost data
- [ ] Endpoints return 500 errors
- [ ] Database is significantly slower
- [ ] Foreign key constraint errors appear

---

## 📝 SIGN-OFF

**Deployment Date:** _______________

**Performed By:** _______________

**VPS IP/Host:** _______________

**Database:** _______________

**Backup Location:** _______________

**Status:**
- [ ] ✅ SUCCESSFUL - Application working normally after 24 hours
- [ ] ⚠️ WARNINGS - Minor issues, monitoring
- [ ] ❌ ROLLED BACK - Database restored to pre-deployment state

**Notes:**
```
_____________________________________________________________

_____________________________________________________________

_____________________________________________________________
```

---

## 📞 SUPPORT CONTACTS

If you encounter issues:

1. **Check logs first:**
   ```bash
   tail -100 logs/error.log
   ```

2. **MySQL connection issues:**
   ```bash
   mysql -u root -p -e "SELECT 1"
   sudo systemctl status mysql
   ```

3. **Application won't start:**
   ```bash
   python main.py  # Run directly to see error messages
   ```

4. **Need to restore backup:**
   See "ROLLBACK PROCEDURES" section above

---

**Documentation Version:** 1.0  
**Last Updated:** January 2024  
**Next Review:** After first production deployment  
