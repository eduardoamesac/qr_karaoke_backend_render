#!/usr/bin/env python3
"""
🔍 QR KARAOKE DATABASE VERIFICATION TOOL
========================================================
Quick status check for database deployment
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{text:^70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.ENDC}\n")

def print_check(label, status, message=""):
    icon = f"{Colors.GREEN}✅{Colors.ENDC}" if status else f"{Colors.RED}❌{Colors.ENDC}"
    print(f"{icon} {label:<50} {message}")

def run_command(cmd, shell=False):
    """Run command and return output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=shell,
            timeout=5
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

def verify_environment():
    """Verify system environment"""
    print_header("SYSTEM VERIFICATION")
    
    # Check Python
    py_ok, py_ver, _ = run_command([sys.executable, "--version"])
    print_check("Python", py_ok, py_ver.strip())
    
    # Check MySQL client
    mysql_ok, _, _ = run_command(["mysql", "--version"], shell=True)
    print_check("MySQL Client", mysql_ok)
    
    # Check mysqldump
    dump_ok, _, _ = run_command(["mysqldump", "--version"], shell=True)
    print_check("MySQL Dump", dump_ok)
    
    # Check virtual environment
    venv_ok = Path(".venv").exists() or Path("venv").exists()
    venv_path = ".venv" if Path(".venv").exists() else "venv"
    print_check("Virtual Environment", venv_ok, venv_path)

def verify_python_packages():
    """Verify required Python packages"""
    print_header("PYTHON PACKAGES")
    
    packages = ["sqlalchemy", "alembic", "pymysql"]
    for package in packages:
        ok, _, _ = run_command(
            [sys.executable, "-c", f"import {package.replace('-', '_')}"],
            shell=False
        )
        print_check(package, ok)

def verify_mysql_connection(host="localhost", user="root", password=""):
    """Verify MySQL connection"""
    print_header("DATABASE CONNECTION")
    
    cmd = ["mysql", "-h", host, "-u", user]
    if password:
        cmd.append(f"-p{password}")
    cmd.extend(["-e", "SELECT 1"])
    
    ok, _, err = run_command(cmd)
    
    if ok:
        print_check("MySQL Connection", True, f"{user}@{host}")
    else:
        print_check("MySQL Connection", False, "Check credentials")
        if "Access denied" in err:
            print(f"  {Colors.YELLOW}→ Verify username/password{Colors.ENDC}")
    
    return ok

def verify_database_structure(host="localhost", user="root", password="", db_name="mi_base_datos"):
    """Verify database structure"""
    print_header("DATABASE STRUCTURE")
    
    # Get list of tables
    cmd = ["mysql", "-h", host, "-u", user]
    if password:
        cmd.append(f"-p{password}")
    cmd.extend(["-D", db_name, "-e", "SHOW TABLES;"])
    
    ok, output, _ = run_command(cmd)
    
    if not ok:
        print_check("Database Access", False)
        return False
    
    tables = [line.strip() for line in output.split('\n') 
              if line.strip() and 'Tables' not in line]
    
    expected_tables = {
        'usuarios': True,
        'canciones': True,
        'mesas': True,
        'consumos': True,
        'cuentas': True,
        'productos': True,
        'pagos': True,
        'song_credits': True,
        'admin_api_keys': True,
    }
    
    removed_tables = {
        'admin_logs': False,
        'banned_nicks': False,
        'configuracion_global': False,
    }
    
    print(f"Tables in {db_name}: {len(tables)}")
    
    # Check expected tables
    for table in expected_tables:
        status = table in tables
        print_check(f"  • {table}", status, 
                   f"({len([t for t in output.split(chr(10)) if table in t])} rows)")
    
    # Check removed tables
    for table in removed_tables:
        status = table not in tables
        status_str = "REMOVED ✓" if status else "STILL EXISTS ✗"
        print_check(f"  • {table}", status, status_str)
    
    return True

def verify_indices(host="localhost", user="root", password="", db_name="mi_base_datos"):
    """Verify optimization indices"""
    print_header("OPTIMIZATION INDICES")
    
    indices_to_check = {
        'usuarios': ['idx_usuarios_banned', 'idx_usuarios_active'],
        'canciones': ['idx_canciones_estado', 'idx_canciones_fecha'],
        'consumos': ['idx_consumos_fecha', 'idx_consumos_dispatched'],
        'mesas': ['idx_mesas_active'],
        'cuentas': ['idx_cuentas_fecha', 'idx_cuentas_active'],
        'pagos': ['idx_pagos_fecha'],
    }
    
    for table, indices in indices_to_check.items():
        cmd = ["mysql", "-h", host, "-u", user]
        if password:
            cmd.append(f"-p{password}")
        cmd.extend(["-D", db_name, "-e", f"SHOW INDEX FROM {table};"])
        
        ok, output, _ = run_command(cmd)
        
        if ok:
            for idx in indices:
                status = idx in output
                print_check(f"  • {table}.{idx}", status)
        else:
            print_check(f"  • {table}", False, "Cannot access table")

def verify_migration_status(host="localhost", user="root", password="", db_name="mi_base_datos"):
    """Check Alembic migration status"""
    print_header("MIGRATION STATUS")
    
    ok, output, _ = run_command(["alembic", "current"])
    
    if ok:
        current = output.strip()
        is_optimized = "optimize_database_remove_unused_tables" in current
        
        print_check("Current Migration", True, current)
        print_check("Optimization Applied", is_optimized, 
                   "✓" if is_optimized else "NOT YET APPLIED")
    else:
        print_check("Alembic Status", False, "Cannot read migration status")

def verify_backups():
    """Check if backups exist"""
    print_header("BACKUPS")
    
    backup_dir = Path("./backups")
    
    if backup_dir.exists():
        backups = list(backup_dir.glob("*.sql.gz"))
        print_check("Backup Directory", True, f"{len(backups)} backup(s) found")
        
        if backups:
            latest = max(backups, key=lambda p: p.stat().st_mtime)
            size_mb = latest.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(latest.stat().st_mtime)
            print(f"  Latest: {latest.name} ({size_mb:.1f} MB)")
            print(f"  Date: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print_check("Backup Directory", False, "Not found - create with: mkdir backups")

def get_database_size(host="localhost", user="root", password="", db_name="mi_base_datos"):
    """Get database size info"""
    print_header("DATABASE SIZE")
    
    cmd = ["mysql", "-h", host, "-u", user]
    if password:
        cmd.append(f"-p{password}")
    cmd.extend(["-D", db_name, "-e", f"""
    SELECT 
        TABLE_NAME,
        ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS 'MB'
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = '{db_name}'
    ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
    """])
    
    ok, output, _ = run_command(cmd)
    
    if ok:
        print(output)
        # Calculate total
        total = 0
        for line in output.split('\n'):
            if 'MB' in line and '|' in line:
                try:
                    parts = line.split('|')
                    size = float(parts[-2].strip())
                    total += size
                except:
                    pass
        
        print(f"\n{Colors.BOLD}Total Size: {total:.2f} MB{Colors.ENDC}")

def main():
    """Main verification routine"""
    
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║        🔍 QR KARAOKE DATABASE - VERIFICATION TOOL               ║
║           Status Check & Deployment Verification               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.ENDC}
    """)
    
    # System checks
    verify_environment()
    verify_python_packages()
    
    # Get credentials
    print(f"\n{Colors.YELLOW}Enter database credentials:{Colors.ENDC}\n")
    host = input("MySQL Host [localhost]: ").strip() or "localhost"
    user = input("MySQL User [root]: ").strip() or "root"
    password = input("MySQL Password [none]: ").strip() or ""
    db_name = input("Database [mi_base_datos]: ").strip() or "mi_base_datos"
    
    # Database checks
    if verify_mysql_connection(host, user, password):
        verify_database_structure(host, user, password, db_name)
        verify_indices(host, user, password, db_name)
        get_database_size(host, user, password, db_name)
    
    # Other checks
    verify_migration_status()
    verify_backups()
    
    # Summary
    print_header("✨ VERIFICATION COMPLETE ✨")
    
    print(f"""
{Colors.GREEN}Check the results above for:
✅ All system binaries found
✅ Python packages installed
✅ Database connection works
✅ All expected tables exist
✅ Removed tables are gone
✅ Optimization indices present
✅ Backups exist
✅ Migration applied{Colors.ENDC}

{Colors.YELLOW}If any checks failed:
1. Check credentials
2. Verify MySQL is running
3. Ensure you're in the correct directory
4. Review the DEPLOYMENT_GUIDE.md{Colors.ENDC}
    """)

if __name__ == "__main__":
    main()
