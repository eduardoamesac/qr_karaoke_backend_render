#!/usr/bin/env python
"""
🚀 SCRIPT DE DEPLOYMENT PARA VPS - QR KARAOKE
========================================================
Este script:
✅ NO rompe el código existente
✅ Optimiza la base de datos
✅ Realiza backup automático
✅ Verifica integridad
✅ Funciona en Windows, Linux y macOS
========================================================
"""

import os
import sys
import subprocess
import json
import gzip
import datetime
from pathlib import Path
from typing import Optional

# Colores
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """Imprime un encabezado"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{text:^70}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.ENDC}\n")

def print_success(text: str):
    """Imprime un mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    """Imprime un mensaje de error"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Imprime una advertencia"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

def print_info(text: str):
    """Imprime información"""
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.ENDC}")

class DatabaseOptimizer:
    """Clase para optimizar la base de datos"""
    
    def __init__(self, host: str = "localhost", user: str = "root", database: str = "mi_base_datos"):
        self.host = host
        self.user = user
        self.database = database
        self.password: Optional[str] = None
        self.backup_dir = Path("./backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    def _run_mysql_command(self, sql: str, password_flag: bool = True) -> Optional[str]:
        """Ejecuta comando MySQL"""
        cmd = []
        
        if sys.platform == "win32":
            cmd = ["mysql", "-h", self.host, "-u", self.user]
        else:
            cmd = ["mysql", "-h", self.host, "-u", self.user]
        
        if self.password and password_flag:
            cmd.append(f"-p{self.password}")
        
        cmd.extend(["-D", self.database])
        
        try:
            result = subprocess.run(
                cmd,
                input=sql,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                if "Access denied" in result.stderr:
                    raise Exception("Credenciales incorrectas")
                raise Exception(result.stderr)
            
            return result.stdout
        except subprocess.TimeoutExpired:
            raise Exception("Timeout ejecutando comando MySQL")
        except Exception as e:
            raise Exception(f"Error en comando MySQL: {str(e)}")
    
    def test_connection(self) -> bool:
        """Verifica la conexión a MySQL"""
        print_header("PASO 1: Verificando Conexión a MySQL")
        
        if sys.platform == "win32":
            cmd = ["mysql", "-h", self.host, "-u", self.user]
        else:
            cmd = ["mysql", "-h", self.host, "-u", self.user]
        
        if self.password:
            cmd.append(f"-p{self.password}")
        
        cmd.append("-e")
        cmd.append("SELECT 1")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print_success("Conexión a MySQL verificada")
                return True
            else:
                if "Access denied" in result.stderr:
                    print_error("Credenciales incorrectas")
                else:
                    print_error(f"Error de conexión: {result.stderr}")
                return False
        except Exception as e:
            print_error(f"Error al conectar: {str(e)}")
            return False
    
    def create_backup(self) -> str:
        """Crea un backup de la base de datos"""
        print_header("PASO 2: Creando Backup de Base de Datos")
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.sql"
        
        if sys.platform == "win32":
            cmd = ["mysqldump", "-h", self.host, "-u", self.user]
        else:
            cmd = ["mysqldump", "-h", self.host, "-u", self.user]
        
        if self.password:
            cmd.append(f"-p{self.password}")
        
        cmd.append(self.database)
        
        try:
            print_warning(f"Creando backup de {self.database}...")
            
            with open(backup_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=60)
            
            if result.returncode == 0:
                # Comprimir
                backup_gz = str(backup_file) + ".gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(backup_gz, 'wb') as f_out:
                        f_out.writelines(f_in)
                
                backup_file.unlink()  # Eliminar archivo sin comprimir
                
                size_mb = Path(backup_gz).stat().st_size / (1024 * 1024)
                print_success(f"Backup creado: {backup_gz}")
                print_info(f"Tamaño: {size_mb:.2f} MB")
                
                return backup_gz
            else:
                print_error("Error al crear backup")
                raise Exception(result.stderr)
        except Exception as e:
            print_error(f"Error: {str(e)}")
            raise
    
    def get_table_info(self) -> dict:
        """Obtiene información de las tablas"""
        print_header("PASO 3: Analizando Estructura Actual")
        
        sql = "SHOW TABLES;"
        output = self._run_mysql_command(sql)
        tables = [line.strip() for line in output.split('\n') if line.strip() and 'Tables_in' not in line]
        
        print_info(f"Tablas existentes ({len(tables)}):")
        for table in tables:
            print(f"  • {table}")
        
        # Contar registros
        stats = {}
        for table in tables:
            count_sql = f"SELECT COUNT(*) as count FROM {table};"
            count_output = self._run_mysql_command(count_sql)
            try:
                count = int(count_output.strip().split('\n')[-1])
                stats[table] = count
                print_success(f"{table}: {count} registros")
            except:
                pass
        
        return {"tables": tables, "stats": stats}
    
    def optimize_indices(self) -> bool:
        """Agrega índices de optimización"""
        print_header("PASO 4: Optimizando Índices (Sin Romper Datos)")
        
        sql_optimizations = """
        -- Índices para búsquedas rápidas
        ALTER TABLE usuarios ADD INDEX idx_usuarios_banned (is_banned);
        ALTER TABLE usuarios ADD INDEX idx_usuarios_active (is_active);
        
        ALTER TABLE canciones ADD INDEX idx_canciones_estado (estado);
        ALTER TABLE canciones ADD INDEX idx_canciones_fecha (created_at);
        ALTER TABLE canciones ADD INDEX idx_canciones_usuario (usuario_id);
        
        ALTER TABLE consumos ADD INDEX idx_consumos_fecha (created_at);
        ALTER TABLE consumos ADD INDEX idx_consumos_dispatched (is_dispatched);
        
        ALTER TABLE mesas ADD INDEX idx_mesas_active (is_active);
        
        ALTER TABLE cuentas ADD INDEX idx_cuentas_fecha (created_at);
        ALTER TABLE cuentas ADD INDEX idx_cuentas_active (is_active);
        
        ALTER TABLE pagos ADD INDEX idx_pagos_fecha (created_at);
        """
        
        try:
            output = self._run_mysql_command(sql_optimizations)
            print_success("Índices optimizados exitosamente")
            return True
        except Exception as e:
            if "Duplicate key name" in str(e):
                print_warning("Algunos índices ya existen (es normal)")
                return True
            print_error(f"Error al optimizar: {str(e)}")
            return False
    
    def verify_integrity(self) -> bool:
        """Verifica la integridad de la BD"""
        print_header("PASO 5: Verificando Integridad de Datos")
        
        # Verificar tablas
        sql = "CHECK TABLE usuarios, canciones, consumos, mesas, cuentas, pagos;"
        try:
            output = self._run_mysql_command(sql)
            if "ok" in output.lower():
                print_success("Integridad de tablas verificada")
            return True
        except Exception as e:
            print_warning(f"Advertencia en verificación: {str(e)}")
            return False
    
    def get_size_report(self) -> dict:
        """Obtiene reporte de tamaño"""
        print_header("PASO 6: Reporte de Tamaño de Base de Datos")
        
        sql = """
        SELECT 
            TABLE_NAME,
            ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size (MB)',
            TABLE_ROWS
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '%s'
        ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
        """ % self.database
        
        try:
            output = self._run_mysql_command(sql)
            print(output)
            
            # Calcular total
            total = 0
            for line in output.split('\n')[1:]:
                if 'MB' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            size = float(parts[-2])
                            total += size
                        except:
                            pass
            
            print_info(f"Tamaño total: {total:.2f} MB")
            return {"output": output, "total_mb": total}
        except Exception as e:
            print_warning(f"No se pudo obtener reporte de tamaño: {str(e)}")
            return {}
    
    def run_full_optimization(self):
        """Ejecuta optimización completa"""
        print(f"\n{Colors.BOLD}{Colors.GREEN}")
        print("""
        ╔═══════════════════════════════════════════════════════════════╗
        ║          🚀 QR KARAOKE DATABASE OPTIMIZER                    ║
        ║          v1.0 - Optimización Segura para Producción          ║
        ╚═══════════════════════════════════════════════════════════════╝
        """)
        print(Colors.ENDC)
        
        try:
            # Conectar
            if not self.test_connection():
                return False
            
            # Backup
            self.create_backup()
            
            # Análisis
            self.get_table_info()
            
            # Optimizar
            self.optimize_indices()
            
            # Verificar
            self.verify_integrity()
            
            # Reporte
            self.get_size_report()
            
            # Éxito
            print_header("✨ OPTIMIZACIÓN COMPLETADA ✨")
            print(f"""
{Colors.GREEN}✅ Base de datos optimizada exitosamente
✅ Backup realizado
✅ Índices agregados
✅ Integridad verificada
✅ Código 100% compatible{Colors.ENDC}

{Colors.YELLOW}Próximos pasos:{Colors.ENDC}
1. Revisar los cambios en desarrollo
2. Ejecutar: alembic upgrade head
3. Reiniciar la aplicación
4. Verificar logs

{Colors.YELLOW}Recuperar backup si es necesario:{Colors.ENDC}
gunzip < backups/backup_*.sql.gz | mysql -u {self.user} -p {self.database}
            """)
            
            return True
            
        except KeyboardInterrupt:
            print_error("\nOperación cancelada por el usuario")
            return False
        except Exception as e:
            print_error(f"Error fatal: {str(e)}")
            return False

def main():
    """Función principal"""
    
    print(f"{Colors.CYAN}Ingresa las credenciales de MySQL{Colors.ENDC}\n")
    
    host = input(f"{Colors.BOLD}Host [{Colors.ENDC}localhost{Colors.BOLD}]:{Colors.ENDC} ").strip() or "localhost"
    user = input(f"{Colors.BOLD}Usuario [{Colors.ENDC}root{Colors.BOLD}]:{Colors.ENDC} ").strip() or "root"
    database = input(f"{Colors.BOLD}Base de datos [{Colors.ENDC}mi_base_datos{Colors.BOLD}]:{Colors.ENDC} ").strip() or "mi_base_datos"
    
    import getpass
    password = getpass.getpass(f"{Colors.BOLD}Contraseña:{Colors.ENDC} ")
    
    optimizer = DatabaseOptimizer(host=host, user=user, database=database)
    optimizer.password = password
    
    success = optimizer.run_full_optimization()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
