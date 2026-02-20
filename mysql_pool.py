"""
🔌 MySQL Connector Pool - Versión PROFESIONAL (Alternativa a SQLAlchemy)
=========================================================================
Usa esto si prefieres mysql.connector directamente en lugar de SQLAlchemy
"""

import mysql.connector
from mysql.connector import pooling, Error
import os
from dotenv import load_dotenv

load_dotenv()

class MySQLPool:
    """Connection Pool profesional con mysql.connector"""
    
    # Credenciales
    HOST = os.getenv("DB_HOST", "localhost")
    USER = os.getenv("DB_USER", "root")
    PASSWORD = os.getenv("DB_PASSWORD", "")
    DATABASE = os.getenv("DB_NAME", "mi_base_datos")
    PORT = int(os.getenv("DB_PORT", "3306"))
    
    # Ambiente
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Tamaño del pool según RAM
    # 📊 Importante: No hacer pool_size > 20 para VPS normales
    POOL_CONFIG = {
        "development": {
            "pool_name": "qr_karaoke_dev",
            "pool_size": 5,  # Desarrollo es pequeño
            "pool_reset_session": True,
        },
        "production": {
            "pool_name": "qr_karaoke_prod",
            "pool_size": 15,  # VPS 8GB RAM típicamente
            "pool_reset_session": True,
        }
    }
    
    # Seleccionar configuración según ambiente
    CONFIG = POOL_CONFIG.get(ENVIRONMENT, POOL_CONFIG["development"])
    
    @staticmethod
    def get_pool():
        """Obtiene o crea el pool de conexiones"""
        try:
            dbconfig = {
                "host": MySQLPool.HOST,
                "user": MySQLPool.USER,
                "password": MySQLPool.PASSWORD,
                "database": MySQLPool.DATABASE,
                "port": MySQLPool.PORT,
                "pool_name": MySQLPool.CONFIG["pool_name"],
                "pool_size": MySQLPool.CONFIG["pool_size"],
                "pool_reset_session": MySQLPool.CONFIG["pool_reset_session"],
                "autocommit": False,
                "use_unicode": True,
                "charset": "utf8mb4",
                "collation": "utf8mb4_unicode_ci",
            }
            
            return pooling.MySQLConnectionPool(**dbconfig)
            
        except Error as e:
            print(f"❌ Error creating pool: {e}")
            raise

# Instancia global del pool
try:
    connection_pool = MySQLPool.get_pool()
    print("✅ MySQL Connection Pool initialized")
except Exception as e:
    print(f"❌ Failed to initialize pool: {e}")
    connection_pool = None

# ============================================================
# FUNCIONES DE CONEXIÓN
# ============================================================

def get_connection():
    """Obtiene una conexión del pool"""
    if not connection_pool:
        raise Exception("Connection pool not initialized")
    
    try:
        conn = connection_pool.get_connection()
        return conn
    except Error as e:
        print(f"❌ Error getting connection: {e}")
        raise

def execute_query(sql, params=None, fetch_one=False):
    """
    Ejecuta query y retorna resultados
    
    Ejemplo:
        # SELECT
        users = execute_query("SELECT * FROM usuarios WHERE mesa_id = %s", (1,))
        
        # INSERT/UPDATE
        execute_query("UPDATE usuarios SET nick = %s WHERE id = %s", ("Nick", 5))
    """
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        # Para SELECT
        if sql.strip().upper().startswith("SELECT"):
            if fetch_one:
                return cursor.fetchone()
            return cursor.fetchall()
        
        # Para INSERT/UPDATE/DELETE
        conn.commit()
        return cursor.rowcount
        
    except Error as e:
        if conn:
            conn.rollback()
        print(f"❌ Query error: {e}")
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()  # ⚠️ IMPORTANTE: Devolver al pool, no destruir

def execute_transaction(queries):
    """
    Ejecuta múltiples queries en una transacción
    
    Ejemplo:
        queries = [
            ("INSERT INTO usuarios (nick) VALUES (%s)", ("Marco",)),
            ("UPDATE mesas SET activa = 1 WHERE id = %s", (1,)),
        ]
        execute_transaction(queries)
    """
    conn = None
    cursor = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        for sql, params in queries:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
        
        conn.commit()
        print(f"✅ {len(queries)} queries executed successfully")
        
    except Error as e:
        if conn:
            conn.rollback()
        print(f"❌ Transaction failed: {e}")
        raise
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ============================================================
# MONITOREO DEL POOL
# ============================================================

def get_pool_status():
    """Obtiene status actual del pool"""
    if not connection_pool:
        return None
    
    return {
        "pool_name": MySQLPool.CONFIG["pool_name"],
        "pool_size": MySQLPool.CONFIG["pool_size"],
        "environment": MySQLPool.ENVIRONMENT,
        "host": MySQLPool.HOST,
        "database": MySQLPool.DATABASE,
    }

def print_pool_info():
    """Imprime información del pool"""
    status = get_pool_status()
    if status:
        print(f"""
        📊 MySQL Connection Pool Info:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        Pool Name:    {status['pool_name']}
        Pool Size:    {status['pool_size']}
        Environment:  {status['environment']}
        Host:         {status['host']}
        Database:     {status['database']}
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

def test_connection():
    """Verifica que funciona la conexión"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print("✅ Connection pool test: OK")
        return True
        
    except Error as e:
        print(f"❌ Connection pool test FAILED: {e}")
        return False

# ============================================================
# INFORMACIÓN DE CONFIGURACIÓN PARA .env
# ============================================================

"""
Archivo .env recomendado:

# ========== DATABASE ==========
ENVIRONMENT=production
DB_HOST=localhost    # Cambiar según VPS
DB_PORT=3306
DB_USER=root         # Cambiar a usuario dedicado si es posible
DB_PASSWORD=tu_password_segura
DB_NAME=mi_base_datos

# ========== POOL SETTINGS ==========
# Ajusta según RAM de tu VPS:
# 4GB RAM:   pool_size 8-10
# 8GB RAM:   pool_size 15-20
# 16GB RAM:  pool_size 20-30
# NO: Nunca > 30 sin configuración avanzada

POOL_SIZE=15

# ========== LOGGING ==========
DEBUG=False
LOG_LEVEL=INFO
"""
