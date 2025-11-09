-- =============================================================================
-- Migration 005: Create Logging and Audit Tables
-- Sistema de logging, auditoría y métricas
-- =============================================================================

-- Crear extensión para índices GIN si no existe
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================================
-- Tabla de logs de auditoría
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Tipo de acción y nivel
    action VARCHAR(50) NOT NULL,
    level VARCHAR(20) NOT NULL,
    
    -- Contexto del usuario
    user_id VARCHAR(255),
    username VARCHAR(100),
    user_roles TEXT[],
    
    -- Contexto de sesión y request
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    
    -- Contexto FHIR
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    resource_version VARCHAR(50),
    endpoint VARCHAR(500),
    http_method VARCHAR(10),
    
    -- Detalles del evento
    message TEXT NOT NULL,
    description TEXT,
    status_code INTEGER,
    
    -- Metadatos adicionales (JSON)
    metadata JSONB,
    
    -- Información de rendimiento
    duration_ms FLOAT,
    
    -- Información de error
    error_code VARCHAR(50),
    error_details TEXT
);

-- =============================================================================
-- Tabla de métricas del sistema
-- =============================================================================

CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Tipo de métrica
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    
    -- Valores de la métrica
    value FLOAT NOT NULL,
    unit VARCHAR(20),
    
    -- Etiquetas/dimensiones (JSON)
    labels JSONB,
    
    -- Contexto opcional
    resource_type VARCHAR(100),
    endpoint VARCHAR(500)
);

-- =============================================================================
-- Tabla de alertas del sistema
-- =============================================================================

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Información de la alerta
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- low, medium, high, critical
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Estado de la alerta
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, acknowledged, resolved
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Contexto
    source VARCHAR(100), -- audit_log, metrics, etc.
    source_event_id VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    
    -- Metadatos adicionales
    metadata JSONB,
    
    -- Contadores
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    last_occurrence TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Índices para optimización de consultas
-- =============================================================================

-- Índices para audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_event_id ON audit_logs(event_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_level ON audit_logs(level);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_logs(username);
CREATE INDEX IF NOT EXISTS idx_audit_session_id ON audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_request_id ON audit_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_ip_address ON audit_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_audit_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_resource_id ON audit_logs(resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_endpoint ON audit_logs(endpoint);
CREATE INDEX IF NOT EXISTS idx_audit_http_method ON audit_logs(http_method);
CREATE INDEX IF NOT EXISTS idx_audit_status_code ON audit_logs(status_code);
CREATE INDEX IF NOT EXISTS idx_audit_duration_ms ON audit_logs(duration_ms);
CREATE INDEX IF NOT EXISTS idx_audit_error_code ON audit_logs(error_code);

-- Índices compuestos para consultas comunes
CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON audit_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id, action);
CREATE INDEX IF NOT EXISTS idx_audit_security ON audit_logs(level, action, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_ip_timestamp ON audit_logs(ip_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_performance ON audit_logs(endpoint, duration_ms, timestamp DESC);

-- Índice GIN para búsqueda en mensaje y metadatos
CREATE INDEX IF NOT EXISTS idx_audit_message_gin ON audit_logs USING GIN (message gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_audit_metadata_gin ON audit_logs USING GIN (metadata);

-- Índices para system_metrics
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON system_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_type_name_timestamp ON system_metrics(metric_type, metric_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_resource ON system_metrics(resource_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_labels_gin ON system_metrics USING GIN (labels);

-- Índice único para evitar duplicados en ventanas de tiempo específicas
CREATE UNIQUE INDEX IF NOT EXISTS idx_metrics_unique_minute ON system_metrics(
    metric_type, 
    metric_name, 
    date_trunc('minute', timestamp)
);

-- Índices para alerts
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_updated_at ON alerts(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_source_event_id ON alerts(source_event_id);
CREATE INDEX IF NOT EXISTS idx_alerts_resource_type ON alerts(resource_type);
CREATE INDEX IF NOT EXISTS idx_alerts_resource_id ON alerts(resource_id);

-- Índices compuestos para alertas
CREATE INDEX IF NOT EXISTS idx_alerts_status_severity ON alerts(status, severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_type_timestamp ON alerts(alert_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_dedup ON alerts(alert_type, title, status);

-- =============================================================================
-- Triggers para actualización automática de timestamps
-- =============================================================================

-- Función para actualizar timestamp (reutilizada de auth)
-- Ya existe de la migración anterior

-- Trigger para alerts
CREATE TRIGGER update_alerts_updated_at 
    BEFORE UPDATE ON alerts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Configuración de particionado por tiempo (opcional para grandes volúmenes)
-- =============================================================================

-- Para audit_logs (partition por mes)
/*
-- Crear tabla padre particionada
CREATE TABLE audit_logs_partitioned (
    LIKE audit_logs INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Crear particiones por mes
CREATE TABLE audit_logs_y2025m11 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE audit_logs_y2025m12 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
*/

-- =============================================================================
-- Configuración de distribución para Citus
-- =============================================================================

-- Distribuir tablas por campos apropiados para co-location
SELECT create_distributed_table('audit_logs', 'user_id');
SELECT create_distributed_table('system_metrics', 'resource_type'); 

-- Las alertas se mantienen como tabla de referencia
SELECT create_reference_table('alerts');

-- =============================================================================
-- Datos iniciales y configuración
-- =============================================================================

-- Insertar tipos de alertas predefinidos
INSERT INTO alerts (
    alert_type, 
    severity, 
    title, 
    description,
    status,
    metadata
) VALUES 
    ('system_startup', 'info', 'System Started', 'FHIR API system has started successfully', 'resolved', '{"initial": true}'),
    ('high_response_time', 'warning', 'High Response Time Detected', 'API response times are above normal thresholds', 'active', '{"threshold_ms": 1000}'),
    ('database_connection_error', 'critical', 'Database Connection Failed', 'Unable to connect to database', 'active', '{"component": "database"}'),
    ('authentication_failures', 'warning', 'Multiple Authentication Failures', 'Unusual number of failed login attempts detected', 'active', '{"threshold": 5})
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Funciones de utilidad para reporting
-- =============================================================================

-- Función para obtener estadísticas de auditoría por período
CREATE OR REPLACE FUNCTION get_audit_stats(
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '24 hours',
    end_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
RETURNS TABLE (
    action VARCHAR(50),
    resource_type VARCHAR(100),
    count BIGINT,
    avg_duration_ms FLOAT,
    success_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        al.action,
        al.resource_type,
        COUNT(*) as count,
        AVG(al.duration_ms) as avg_duration_ms,
        (COUNT(*) FILTER (WHERE al.status_code < 400)::FLOAT / COUNT(*) * 100) as success_rate
    FROM audit_logs al
    WHERE al.timestamp BETWEEN start_time AND end_time
    GROUP BY al.action, al.resource_type
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Función para limpiar logs antiguos
CREATE OR REPLACE FUNCTION cleanup_old_logs(
    days_to_keep INTEGER DEFAULT 90
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_logs 
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM system_metrics 
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Crear vistas para reporting común
-- =============================================================================

-- Vista de resumen de actividad diaria
CREATE OR REPLACE VIEW daily_activity_summary AS
SELECT 
    DATE(timestamp) as activity_date,
    action,
    resource_type,
    COUNT(*) as operation_count,
    AVG(duration_ms) as avg_duration_ms,
    COUNT(*) FILTER (WHERE status_code >= 400) as error_count,
    COUNT(DISTINCT user_id) as unique_users
FROM audit_logs
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(timestamp), action, resource_type
ORDER BY activity_date DESC, operation_count DESC;

-- Vista de usuarios más activos
CREATE OR REPLACE VIEW most_active_users AS
SELECT 
    username,
    user_id,
    COUNT(*) as total_operations,
    COUNT(DISTINCT resource_type) as resource_types_accessed,
    MAX(timestamp) as last_activity,
    COUNT(*) FILTER (WHERE timestamp >= NOW() - INTERVAL '24 hours') as operations_last_24h
FROM audit_logs
WHERE username IS NOT NULL
  AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY username, user_id
ORDER BY total_operations DESC;

-- Vista de métricas de rendimiento
CREATE OR REPLACE VIEW performance_metrics AS
SELECT 
    endpoint,
    http_method,
    COUNT(*) as request_count,
    AVG(duration_ms) as avg_duration_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as median_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms,
    COUNT(*) FILTER (WHERE status_code >= 400) as error_count,
    (COUNT(*) FILTER (WHERE status_code < 400)::FLOAT / COUNT(*) * 100) as success_rate
FROM audit_logs
WHERE endpoint IS NOT NULL
  AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY endpoint, http_method
ORDER BY request_count DESC;

COMMIT;