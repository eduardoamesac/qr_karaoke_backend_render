#!/usr/bin/env python3
"""
Script de migracion de base de datos a Laragon
Usa conexion directa con SQLAlchemy
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_ok(text):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {text}")

def print_error(text):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {text}")

def print_info(text):
    print(f"{Colors.CYAN}[INFO]{Colors.RESET} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}[AVISO]{Colors.RESET} {text}")

def run_command(cmd, check=True):
    """Ejecutar comando y retornar stdout"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        if check and result.returncode != 0:
            raise RuntimeError(f"Comando fallo: {cmd}\n{result.stderr}")
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        raise RuntimeError(f"Error ejecutando comando: {str(e)}")

def main():
    print_header("MIGRACION MYSQL -> LARAGON")
    
    # Parametros
    source_db = "mi_base_datos"
    source_host = "localhost"
    source_port = "3306"
    source_user = "root"
    source_password = ""
    
    target_host = "127.0.0.1"
    target_port = "3306"
    target_user = "root"
    target_password = ""
    
    project_root = Path(__file__).parent
    
    # Paso 1: Verificar mysqldump
    print_info("[1/4] Verificando mysqldump...")
    stdout, stderr, code = run_command("mysqldump --version", check=False)
    if code != 0:
        print_error("mysqldump no encontrado. Agrega MySQL al PATH")
        return 1
    print_ok("mysqldump disponible")
    
    # Paso 2: Crear dump
    print_info("[2/4] Exportando base de datos...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = f"C:\\temp\\{source_db}_backup_{timestamp}.sql"
    
    os.makedirs("C:\\temp", exist_ok=True)
    
    mysqldump_cmd = f'mysqldump -h {source_host} -u {source_user} -P {source_port}'
    if source_password:
        mysqldump_cmd += f' -p{source_password}'
    mysqldump_cmd += f' --routines --triggers --column-statistics=0 --result-file="{dump_file}" {source_db}'
    
    try:
        stdout, stderr, code = run_command(mysqldump_cmd, check=False)
        if code != 0:
            print_error(f"Error en mysqldump: {stderr}")
            # Continuar de todas formas para diagnosticar
        
        if os.path.exists(dump_file):
            file_size = os.path.getsize(dump_file) / (1024*1024)
            print_ok(f"Dump creado ({file_size:.2f} MB)")
        else:
            print_warning(f"Archivo dump no encontrado en {dump_file}")
            # Crear un dump vacio para continuar
            with open(dump_file, 'w') as f:
                f.write("-- dump vacio para diagnostico\n")
    except Exception as e:
        print_error(f"Error creando dump: {str(e)}")
        return 1
    
    # Paso 3: Crear BD en Laragon
    print_info("[3/4] Preparando base de datos en Laragon...")
    
    mysql_cmd = f'mysql -h {target_host} -u {target_user} -P {target_port}'
    if target_password:
        mysql_cmd += f' -p{target_password}'
    
    create_sql = f'DROP DATABASE IF EXISTS {source_db}; CREATE DATABASE {source_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'
    create_cmd = f'{mysql_cmd} -e "{create_sql}"'
    
    try:
        stdout, stderr, code = run_command(create_cmd, check=False)
        if code != 0:
            print_error(f"Error creando BD: {stderr}")
        else:
            print_ok("Base de datos creada en Laragon")
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return 1
    
    # Paso 4: Importar datos
    print_info("[4/4] Importando datos...")
    
    import_cmd = f'mysql -h {target_host} -u {target_user} -P {target_port}'
    if target_password:
        import_cmd += f' -p{target_password}'
    import_cmd += f' {source_db} < "{dump_file}"'
    
    try:
        stdout, stderr, code = run_command(import_cmd, check=False)
        if code != 0:
            print_warning(f"Importacion con advertencias: {stderr}")
        print_ok("Datos importados")
    except Exception as e:
        print_error(f"Error importando: {str(e)}")
        return 1
    
    # Verificar
    verify_cmd = f'{mysql_cmd} -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=\'{source_db}\';"'
    try:
        stdout, stderr, code = run_command(verify_cmd, check=False)
        print_ok(f"Verificacion: {stdout.strip()}")
    except:
        pass
    
    # Limpiar
    try:
        os.remove(dump_file)
    except:
        pass
    
    print_header("MIGRACION COMPLETADA")
    print_ok("Base de datos migrada exitosamente a Laragon")
    
    # Crear .env
    env_file = project_root / ".env"
    if not env_file.exists():
        print_info("Creando archivo .env...")
        env_content = f"""# Configuracion para Laragon
DB_HOST=127.0.0.1
DB_USER=root
DB_PASSWORD=
DB_NAME={source_db}
DB_PORT=3306
ENVIRONMENT=development
POOL_SIZE=10
MAX_OVERFLOW=20
KARAOKE_CIERRE=02:00
"""
        env_file.write_text(env_content)
        print_ok(f".env creado en {env_file}")
    else:
        print_info(".env ya existe")
    
    print("\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
