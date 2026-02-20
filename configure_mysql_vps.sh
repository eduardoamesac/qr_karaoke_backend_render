#!/bin/bash
# ============================================================
# 🔧 CONFIGURACIÓN PROFESIONAL DE MYSQL PARA VPS
# ============================================================
# Script para optimizar MySQL en tu servidor VPS
# Basado en recomendaciones profesionales de la IA
# 
# USO:
# chmod +x configure_mysql_vps.sh
# sudo ./configure_mysql_vps.sh
# ============================================================

set -e

echo "🚀 Iniciando configuración de MySQL para VPS..."

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ============================================================
# PASO 1: Verificar si somos root
# ============================================================
print_header "PASO 1: Verificando permisos"

if [ "$EUID" -ne 0 ]; then 
   print_error "Este script debe ejecutarse con sudo"
   echo "Ejecuta: sudo ./configure_mysql_vps.sh"
   exit 1
fi

print_success "Permisos de root verificados"

# ============================================================
# PASO 2: Detectar RAM del VPS
# ============================================================
print_header "PASO 2: Detectando RAM disponible"

TOTAL_RAM=$(free -g | awk '/^Mem:/ {print $2}')
print_success "RAM Total: ${TOTAL_RAM}GB"

# Calcular valores recomendados basados en RAM
if [ "$TOTAL_RAM" -le 4 ]; then
    INNODB_BUFFER_POOL="1G"
    MAX_CONNECTIONS=100
    POOL_SIZE=10
    print_warning "VPS 4GB o menor detectado"
elif [ "$TOTAL_RAM" -le 8 ]; then
    INNODB_BUFFER_POOL="2G"
    MAX_CONNECTIONS=150
    POOL_SIZE=15
    print_success "VPS 8GB detectado"
elif [ "$TOTAL_RAM" -le 16 ]; then
    INNODB_BUFFER_POOL="4G"
    MAX_CONNECTIONS=200
    POOL_SIZE=20
    print_success "VPS 16GB detectado"
else
    INNODB_BUFFER_POOL="8G"
    MAX_CONNECTIONS=300
    POOL_SIZE=30
    print_success "VPS 16GB+ (Premium) detectado"
fi

echo ""
echo "📊 Valores recomendados para tu VPS:"
echo "   innodb_buffer_pool_size = $INNODB_BUFFER_POOL"
echo "   max_connections = $MAX_CONNECTIONS"
echo "   Connection Pool Size = $POOL_SIZE"
echo ""

# ============================================================
# PASO 3: Encontrar archivo de configuración MySQL
# ============================================================
print_header "PASO 3: Localizando archivo de configuración"

MYSQL_CONFIG=""
if [ -f "/etc/mysql/mysql.conf.d/mysqld.cnf" ]; then
    MYSQL_CONFIG="/etc/mysql/mysql.conf.d/mysqld.cnf"
    print_success "Encontrado: $MYSQL_CONFIG"
elif [ -f "/etc/mysql/my.cnf" ]; then
    MYSQL_CONFIG="/etc/mysql/my.cnf"
    print_success "Encontrado: $MYSQL_CONFIG"
elif [ -f "/etc/my.cnf" ]; then
    MYSQL_CONFIG="/etc/my.cnf"
    print_success "Encontrado: $MYSQL_CONFIG"
else
    print_error "No se encontró archivo de configuración MySQL"
    exit 1
fi

# Crear backup
BACKUP_FILE="${MYSQL_CONFIG}.backup_$(date +%Y%m%d_%H%M%S)"
cp "$MYSQL_CONFIG" "$BACKUP_FILE"
print_success "Backup creado: $BACKUP_FILE"

# ============================================================
# PASO 4: Actualizar configuración
# ============================================================
print_header "PASO 4: Actualizando configuración MySQL"

# Crear archivo temporal con nuevas configuraciones
cat > /tmp/mysql_optimization.cnf << EOF

# ========================================
# 🔧 OPTIMIZACIONES PROFESIONALES
# ========================================
# Aplicadas el: $(date)
# VPS RAM: ${TOTAL_RAM}GB
# ========================================

# ========== Conexiones ==========
max_connections = $MAX_CONNECTIONS
max_allowed_packet = 256M

# ========== InnoDB ==========
# Buffer pool es el CORAZÓN de MySQL
# Debe ser 50-80% de RAM disponible
innodb_buffer_pool_size = $INNODB_BUFFER_POOL
innodb_buffer_pool_instances = 8
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT

# ========== Query ==========
query_cache_type = 0
query_cache_size = 0
tmp_table_size = 32M
max_heap_table_size = 32M

# ========== Logging ==========
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# ========== Seguridad ==========
skip_external_locking = 1
symbolic_links = 0

# ========== Performance ==========
sort_buffer_size = 256K
bulk_insert_buffer_size = 16M
net_buffer_length = 16K

EOF

# Agregar configuraciones
print_warning "Agregando configuraciones al archivo..."

# Buscar la sección [mysqld] y agregar antes del final
if grep -q "\[mysqld\]" "$MYSQL_CONFIG"; then
    # Crear archivo temporal
    TMP_FILE="${MYSQL_CONFIG}.tmp"
    
    # Copiar hasta antes del siguiente [section]
    sed '/^\[mysqld\]/,/^\[/!b;/^\[mysqld\]/!b;r /tmp/mysql_optimization.cnf
    :a;$!{N;ba;};s/\n\(\[^\]/\n\1/' "$MYSQL_CONFIG" > "$TMP_FILE"
    
    # Alternativa más simple: solo agregar al final del [mysqld]
    cat /tmp/mysql_optimization.cnf >> "$MYSQL_CONFIG"
    
    print_success "Configuraciones agregadas"
else
    print_warning "[mysqld] section not found, agregando al final..."
    echo "[mysqld]" >> "$MYSQL_CONFIG"
    cat /tmp/mysql_optimization.cnf >> "$MYSQL_CONFIG"
fi

# Limpiar
rm /tmp/mysql_optimization.cnf

# ============================================================
# PASO 5: Reiniciar MySQL
# ============================================================
print_header "PASO 5: Reiniciando MySQL"

print_warning "Deteniendo MySQL..."
systemctl stop mysql || service mysql stop || true

sleep 2

print_warning "Iniciando MySQL..."
systemctl start mysql || service mysql start || true

sleep 3

# Verificar si está corriendo
if systemctl is-active --quiet mysql; then
    print_success "MySQL reiniciado correctamente"
else
    print_error "MySQL no se reinició. Verificar logs:"
    echo "sudo tail -50 /var/log/mysql/error.log"
    exit 1
fi

# ============================================================
# PASO 6: Verificar configuraciones aplicadas
# ============================================================
print_header "PASO 6: Verificando configuraciones"

# Conectar a MySQL sin contraseña (requiere acceso root)
echo "Verificando variables en MySQL..."

mysql -u root << MYSQL_EOF
SELECT VARIABLE_NAME, VARIABLE_VALUE 
FROM INFORMATION_SCHEMA.GLOBAL_VARIABLES 
WHERE VARIABLE_NAME IN (
    'max_connections',
    'innodb_buffer_pool_size',
    'innodb_log_file_size'
)
ORDER BY VARIABLE_NAME;
MYSQL_EOF

print_success "Configuraciones verificadas"

# ============================================================
# PASO 7: Reporte Final
# ============================================================
print_header "✅ CONFIGURACIÓN COMPLETADA"

cat << EOF

📊 CONFIGURACIÓN APLICADA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Max Connections:        $MAX_CONNECTIONS
InnoDB Buffer Pool:     $INNODB_BUFFER_POOL
Recommended Pool Size:  $POOL_SIZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 PRÓXIMOS PASOS:
1. Actualizar .env en tu aplicación:
   POOL_SIZE=$POOL_SIZE

2. Reiniciar tu aplicación FastAPI

3. Monitorear MySQL:
   watch -n 1 'mysql -u root -e "SHOW PROCESSLIST;" mi_base_datos'

4. Ver logs lento:
   tail -f /var/log/mysql/slow.log

⚠️  BACKUP REALIZADO EN:
   $BACKUP_FILE

🔙 RESTAURAR SI ES NECESARIO:
   sudo cp $BACKUP_FILE $MYSQL_CONFIG
   sudo systemctl restart mysql

EOF

print_success "¡Configuración profesional de MySQL completada!"
