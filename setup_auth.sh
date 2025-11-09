#!/bin/bash

# =============================================================================
# Script de Setup de Autenticación
# Ejecuta las migraciones de autenticación en el clúster Citus
# =============================================================================

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables de configuración
DB_HOST="${CITUS_COORDINATOR_HOST:-localhost}"
DB_PORT="${CITUS_COORDINATOR_PORT:-5432}"
DB_NAME="${DB_NAME:-clinical_records}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
MIGRATION_DIR="./app/database/migrations"

echo -e "${BLUE}=== Setup de Sistema de Autenticación ===${NC}"
echo -e "Ejecutando migraciones de autenticación..."
echo -e "Coordinador: ${DB_HOST}:${DB_PORT}"
echo -e "Base de datos: ${DB_NAME}"
echo -e "Usuario: ${DB_USER}"
echo ""

# Función para ejecutar SQL
run_sql() {
    local sql_file=$1
    local description=$2
    
    echo -e "${YELLOW}Ejecutando: ${description}${NC}"
    
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$sql_file" -v ON_ERROR_STOP=1; then
        echo -e "${GREEN}✅ ${description} - Completado${NC}"
    else
        echo -e "${RED}❌ Error ejecutando: ${description}${NC}"
        exit 1
    fi
    echo ""
}

# Verificar conexión
echo -e "${YELLOW}Verificando conexión a la base de datos...${NC}"
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Conexión establecida${NC}"
else
    echo -e "${RED}❌ No se puede conectar a la base de datos${NC}"
    echo -e "Verifica que PostgreSQL/Citus esté ejecutándose y las credenciales sean correctas"
    exit 1
fi
echo ""

# Verificar que Citus esté disponible
echo -e "${YELLOW}Verificando extensión Citus...${NC}"
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT citus_version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Citus disponible${NC}"
else
    echo -e "${RED}❌ Citus no está disponible${NC}"
    echo -e "Ejecuta primero el setup de Citus"
    exit 1
fi
echo ""

# Ejecutar migración de autenticación
if [ -f "$MIGRATION_DIR/004_create_auth_tables.sql" ]; then
    run_sql "$MIGRATION_DIR/004_create_auth_tables.sql" "Migración de tablas de autenticación"
else
    echo -e "${RED}❌ No se encuentra el archivo de migración: $MIGRATION_DIR/004_create_auth_tables.sql${NC}"
    exit 1
fi

# Verificar tablas creadas
echo -e "${YELLOW}Verificando tablas de autenticación...${NC}"
TABLES_QUERY="
SELECT schemaname, tablename, tableowner 
FROM pg_tables 
WHERE tablename IN ('users', 'user_roles', 'user_permissions', 'user_role_assignments', 'role_permission_assignments', 'refresh_tokens', 'api_keys')
ORDER BY tablename;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$TABLES_QUERY"; then
    echo -e "${GREEN}✅ Tablas de autenticación verificadas${NC}"
else
    echo -e "${RED}❌ Error verificando tablas${NC}"
    exit 1
fi
echo ""

# Verificar distribución de tablas
echo -e "${YELLOW}Verificando distribución de tablas en Citus...${NC}"
DISTRIBUTION_QUERY="
SELECT logicalrelid::regclass as table_name, 
       partmethod, 
       partkey
FROM pg_dist_partition 
WHERE logicalrelid::regclass::text IN ('users', 'user_role_assignments', 'refresh_tokens', 'api_keys')
ORDER BY table_name;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$DISTRIBUTION_QUERY"; then
    echo -e "${GREEN}✅ Distribución de tablas verificada${NC}"
else
    echo -e "${YELLOW}⚠️  No se pudo verificar la distribución (normal si no hay workers)${NC}"
fi
echo ""

# Verificar datos iniciales
echo -e "${YELLOW}Verificando datos iniciales...${NC}"
INIT_DATA_QUERY="
SELECT 'Roles' as tipo, count(*) as cantidad FROM user_roles
UNION ALL
SELECT 'Permisos' as tipo, count(*) as cantidad FROM user_permissions  
UNION ALL
SELECT 'Usuarios' as tipo, count(*) as cantidad FROM users
UNION ALL
SELECT 'Asignaciones Rol-Permiso' as tipo, count(*) as cantidad FROM role_permission_assignments;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$INIT_DATA_QUERY"; then
    echo -e "${GREEN}✅ Datos iniciales verificados${NC}"
else
    echo -e "${RED}❌ Error verificando datos iniciales${NC}"
    exit 1
fi
echo ""

# Verificar usuario admin
echo -e "${YELLOW}Verificando usuario administrador...${NC}"
ADMIN_QUERY="
SELECT u.username, u.email, u.is_superuser, u.is_active,
       array_agg(r.name) as roles
FROM users u
LEFT JOIN user_role_assignments ura ON u.id = ura.user_id
LEFT JOIN user_roles r ON ura.role_id = r.id
WHERE u.username = 'admin'
GROUP BY u.id, u.username, u.email, u.is_superuser, u.is_active;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$ADMIN_QUERY"; then
    echo -e "${GREEN}✅ Usuario administrador verificado${NC}"
else
    echo -e "${RED}❌ Error verificando usuario administrador${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}=== Setup de Autenticación Completado ===${NC}"
echo -e "${BLUE}Información de acceso:${NC}"
echo -e "Usuario: admin"
echo -e "Email: admin@localhost" 
echo -e "Password: admin123"
echo -e ""
echo -e "${YELLOW}⚠️  IMPORTANTE: Cambia la contraseña del administrador en producción${NC}"
echo -e "Usa el endpoint: POST /auth/change-password"
echo ""
echo -e "${GREEN}✅ El sistema de autenticación está listo para usar${NC}"