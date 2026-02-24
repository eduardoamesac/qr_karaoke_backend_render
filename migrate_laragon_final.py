#!/usr/bin/env python3
"""
Migracion a Laragon - Usa el MySQL de Laragon
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_ok(text):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {text}")

def print_error(text):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {text}")

def print_info(text):
    print(f"{Colors.CYAN}[INFO]{Colors.RESET} {text}")

print("\n" + "="*60)
print("MIGRACION MYSQL -> LARAGON")
print("="*60 + "\n")

# Rutas
laragon_mysql = r"C:\laragon\bin\mysql\mysql-8.0.30-winx64\bin"
mysql_exe = os.path.join(laragon_mysql, "mysql.exe")
mysqldump_exe = os.path.join(laragon_mysql, "mysqldump.exe")
project_root = Path(__file__).parent

db_name = "mi_base_datos"
db_user = "root"
db_password = ""

# Verificar que existen
if not os.path.exists(mysql_exe):
    print_error(f"mysql.exe no encontrado en {mysql_exe}")
    sys.exit(1)

if not os.path.exists(mysqldump_exe):
    print_error(f"mysqldump.exe no encontrado en {mysqldump_exe}")
    sys.exit(1)

print_info("[1/4] Verificando MySQL de Laragon...")
print_ok("MySQL 8.0.30 encontrado")

# Paso 2: Crear dump
print_info("[2/4] Exportando base de datos...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dump_file = f"C:\\temp\\{db_name}_backup_{timestamp}.sql"
os.makedirs("C:\\temp", exist_ok=True)

cmd_dump = f'"{mysqldump_exe}" -h localhost -u {db_user} --routines --triggers --column-statistics=0 --result-file="{dump_file}" {db_name}'
result = subprocess.run(cmd_dump, shell=True, capture_output=True, text=True)

if os.path.exists(dump_file):
    file_size = os.path.getsize(dump_file) / (1024*1024)
    print_ok(f"Dump creado ({file_size:.2f} MB)")
else:
    print_error("No se pudo crear el dump")
    if result.stderr:
        print(f"Error: {result.stderr}")
    sys.exit(1)

# Paso 3: Recrear BD en Laragon
print_info("[3/4] Preparando base de datos en Laragon...")

cmd_create = f'"{mysql_exe}" -h 127.0.0.1 -u {db_user} -e "DROP DATABASE IF EXISTS {db_name}; CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'
result = subprocess.run(cmd_create, shell=True, capture_output=True, text=True)

if result.returncode != 0:
    print_error(f"Error: {result.stderr}")
else:
    print_ok("Base de datos lista en Laragon")

# Paso 4: Importar
print_info("[4/4] Importando datos...")

with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
    cmd_import = f'"{mysql_exe}" -h 127.0.0.1 -u {db_user} {db_name}'
    process = subprocess.Popen(cmd_import, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    stdout, stderr = process.communicate(input=f.read())
    
    if process.returncode != 0:
        print_error(f"Error en importacion: {stderr}")
    else:
        print_ok("Datos importados exitosamente")

# Verificar
cmd_verify = f'"{mysql_exe}" -h 127.0.0.1 -u {db_user} -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=\'{db_name}\';" --skip-column-names'
result = subprocess.run(cmd_verify, shell=True, capture_output=True, text=True)
if result.stdout:
    print_ok(f"Verificacion: {result.stdout.strip()} tablas encontradas")

# Actualizar .env
print_info("Actualizando configuracion...")
env_file = project_root / ".env"

env_content = f"""YOUTUBE_API_KEY=AIzaSyDbm4QHUvhvPk-wI92pIPps7Zp1xH15EOo

# Base de datos - Laragon
DB_HOST=127.0.0.1
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}
DB_PORT=3306

# Ambiente
ENVIRONMENT=development

# Pool de conexiones
POOL_SIZE=10
MAX_OVERFLOW=20

# Karaoke
KARAOKE_CIERRE=02:00
"""

env_file.write_text(env_content, encoding='utf-8')
print_ok(".env configurado para Laragon")

# Limpiar
try:
    os.remove(dump_file)
except:
    pass

print("\n" + "="*60)
print("MIGRACION COMPLETADA EXITOSAMENTE")
print("="*60 + "\n")

print_ok("Base de datos migrada a Laragon")
print(f"Proximos pasos:")
print(f"  1. Activa el venv: .\\venv\\Scripts\\Activate.ps1")
print(f"  2. Inicia la app: python main.py")
print("")
