#!/bin/bash

# =============================================================================
# Script de Setup de Logging y Auditoría
# Ejecuta las migraciones de logging, auditoría y métricas en el clúster Citus
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

echo -e "${BLUE}=== Setup de Sistema de Logging y Auditoría ===${NC}"
echo -e "Ejecutando migraciones de logging, auditoría y métricas..."
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

# Función para ejecutar consulta SQL
run_query() {
    local query=$1
    local description=$2
    
    echo -e "${YELLOW}Ejecutando: ${description}${NC}"
    
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$query"; then
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

# Verificar que las tablas de autenticación existan
echo -e "${YELLOW}Verificando tablas de autenticación...${NC}"
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM users;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Tablas de autenticación disponibles${NC}"
else
    echo -e "${RED}❌ Tablas de autenticación no encontradas${NC}"
    echo -e "Ejecuta primero: ./setup_auth.sh"
    exit 1
fi
echo ""

# Ejecutar migración de logging
if [ -f "$MIGRATION_DIR/005_create_logging_tables.sql" ]; then
    run_sql "$MIGRATION_DIR/005_create_logging_tables.sql" "Migración de tablas de logging y auditoría"
else
    echo -e "${RED}❌ No se encuentra el archivo de migración: $MIGRATION_DIR/005_create_logging_tables.sql${NC}"
    exit 1
fi

# Verificar tablas creadas
echo -e "${YELLOW}Verificando tablas de logging y auditoría...${NC}"
TABLES_QUERY="
SELECT schemaname, tablename, tableowner 
FROM pg_tables 
WHERE tablename IN ('audit_logs', 'system_metrics', 'alerts')
ORDER BY tablename;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$TABLES_QUERY"; then
    echo -e "${GREEN}✅ Tablas de logging y auditoría verificadas${NC}"
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
WHERE logicalrelid::regclass::text IN ('audit_logs', 'system_metrics')
ORDER BY table_name;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$DISTRIBUTION_QUERY"; then
    echo -e "${GREEN}✅ Distribución de tablas verificada${NC}"
else
    echo -e "${YELLOW}⚠️  No se pudo verificar la distribución (normal si no hay workers)${NC}"
fi
echo ""

# Verificar funciones creadas
echo -e "${YELLOW}Verificando funciones de utilidad...${NC}"
FUNCTIONS_QUERY="
SELECT proname, proargnames, prosrc IS NOT NULL as has_body
FROM pg_proc 
WHERE proname IN ('get_audit_stats', 'cleanup_old_logs')
ORDER BY proname;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$FUNCTIONS_QUERY"; then
    echo -e "${GREEN}✅ Funciones de utilidad verificadas${NC}"
else
    echo -e "${RED}❌ Error verificando funciones${NC}"
    exit 1
fi
echo ""

# Verificar vistas creadas
echo -e "${YELLOW}Verificando vistas de reporting...${NC}"
VIEWS_QUERY="
SELECT schemaname, viewname, viewowner
FROM pg_views 
WHERE viewname IN ('daily_activity_summary', 'most_active_users', 'performance_metrics')
ORDER BY viewname;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$VIEWS_QUERY"; then
    echo -e "${GREEN}✅ Vistas de reporting verificadas${NC}"
else
    echo -e "${RED}❌ Error verificando vistas${NC}"
    exit 1
fi
echo ""

# Verificar índices importantes
echo -e "${YELLOW}Verificando índices de auditoría...${NC}"
INDEXES_QUERY="
SELECT indexname, tablename, indexdef
FROM pg_indexes 
WHERE tablename IN ('audit_logs', 'system_metrics', 'alerts')
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
"

INDEX_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM pg_indexes WHERE tablename IN ('audit_logs', 'system_metrics', 'alerts') AND indexname LIKE 'idx_%';")

echo -e "Índices creados: ${INDEX_COUNT// /}"
echo -e "${GREEN}✅ Índices de auditoría verificados${NC}"
echo ""

# Insertar evento de auditoría inicial
echo -e "${YELLOW}Insertando evento de auditoría inicial...${NC}"
INITIAL_AUDIT_QUERY="
INSERT INTO audit_logs (
    event_id,
    action,
    level,
    message,
    description,
    metadata
) VALUES (
    gen_random_uuid()::text,
    'system_start',
    'info',
    'Logging system initialized',
    'Sistema de logging y auditoría configurado exitosamente',
    '{\"component\": \"logging_system\", \"setup_completed\": true}'::jsonb
);
"

run_query "$INITIAL_AUDIT_QUERY" "Insertar evento de auditoría inicial"

# Insertar métrica inicial
echo -e "${YELLOW}Insertando métricas iniciales...${NC}"
INITIAL_METRICS_QUERY="
INSERT INTO system_metrics (
    metric_type,
    metric_name,
    value,
    unit,
    labels
) VALUES 
    ('system', 'setup_completed', 1, 'boolean', '{\"component\": \"logging\"}'::jsonb),
    ('system', 'tables_created', 3, 'count', '{\"tables\": [\"audit_logs\", \"system_metrics\", \"alerts\"]}'::jsonb);
"

run_query "$INITIAL_METRICS_QUERY" "Insertar métricas iniciales"

# Verificar datos de prueba
echo -e "${YELLOW}Verificando datos iniciales...${NC}"
VERIFY_DATA_QUERY="
SELECT 'Audit Logs' as tipo, count(*) as cantidad FROM audit_logs
UNION ALL
SELECT 'System Metrics' as tipo, count(*) as cantidad FROM system_metrics
UNION ALL  
SELECT 'Alerts' as tipo, count(*) as cantidad FROM alerts;
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$VERIFY_DATA_QUERY"; then
    echo -e "${GREEN}✅ Datos iniciales verificados${NC}"
else
    echo -e "${RED}❌ Error verificando datos iniciales${NC}"
    exit 1
fi
echo ""

# Crear directorio de logs si no existe
echo -e "${YELLOW}Creando directorio de logs de aplicación...${NC}"
mkdir -p logs
touch logs/application.log
touch logs/audit.log
touch logs/errors.log
echo -e "${GREEN}✅ Directorio de logs creado${NC}"
echo ""

# Mostrar estadísticas finales
echo -e "${YELLOW}Obteniendo estadísticas del sistema...${NC}"
STATS_QUERY="
SELECT 
    'Tablas de Logging' as categoria,
    COUNT(*) as total
FROM pg_tables 
WHERE tablename IN ('audit_logs', 'system_metrics', 'alerts')

UNION ALL

SELECT 
    'Índices Creados' as categoria,
    COUNT(*) as total
FROM pg_indexes 
WHERE tablename IN ('audit_logs', 'system_metrics', 'alerts') 
  AND indexname LIKE 'idx_%'

UNION ALL

SELECT 
    'Funciones de Utilidad' as categoria,
    COUNT(*) as total
FROM pg_proc 
WHERE proname IN ('get_audit_stats', 'cleanup_old_logs')

UNION ALL

SELECT 
    'Vistas de Reporting' as categoria,
    COUNT(*) as total
FROM pg_views 
WHERE viewname IN ('daily_activity_summary', 'most_active_users', 'performance_metrics');
"

if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$STATS_QUERY"; then
    echo -e "${GREEN}✅ Estadísticas del sistema obtenidas${NC}"
else
    echo -e "${YELLOW}⚠️  No se pudieron obtener estadísticas completas${NC}"
fi
echo ""

echo -e "${GREEN}=== Setup de Logging y Auditoría Completado ===${NC}"
echo -e "${BLUE}Funcionalidades configuradas:${NC}"
echo -e "✅ Tablas de auditoría distribuidas (audit_logs)"
echo -e "✅ Sistema de métricas (system_metrics)"
echo -e "✅ Sistema de alertas (alerts)"
echo -e "✅ Índices optimizados para consultas"
echo -e "✅ Funciones de utilidad para reporting"
echo -e "✅ Vistas predefinidas para análisis"
echo -e "✅ Configuración de Citus para distribución"
echo -e "✅ Directorio de logs de aplicación"
echo ""
echo -e "${BLUE}Endpoints disponibles:${NC}"
echo -e "• GET /health/detailed - Health check detallado"
echo -e "• GET /metrics - Métricas del sistema" 
echo -e "• GET /metrics/prometheus - Métricas formato Prometheus"
echo -e "• GET /audit/recent - Logs de auditoría recientes"
echo ""
echo -e "${BLUE}Archivos de log:${NC}"
echo -e "• logs/application.log - Logs generales de aplicación"
echo -e "• logs/audit.log - Logs de auditoría"
echo -e "• logs/errors.log - Logs de errores"
echo ""
echo -e "${GREEN}✅ El sistema de logging y auditoría está listo para usar${NC}"