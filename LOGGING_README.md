# Sistema de Logging y Auditoría FHIR

Este documento describe el sistema completo de logging, auditoría y monitoreo implementado para la API FHIR.

## Arquitectura del Sistema

### Componentes Principales

1. **Audit Logger** (`app/logging/audit_logger.py`)
   - Registro de eventos de auditoría
   - Almacenamiento en BD y archivos
   - Eventos estructurados con contexto completo

2. **Structured Logger** (`app/logging/structured_logger.py`)
   - Logging estructurado en formato JSON
   - Múltiples niveles y contextos
   - Integración con FastAPI

3. **Metrics System** (`app/logging/metrics.py`)
   - Colector de métricas en tiempo real
   - Sistema de alertas automáticas
   - Monitoreo de salud del sistema

4. **Middleware de Logging** (`app/logging/middleware.py`)
   - Logging automático de requests/responses
   - Auditoría de operaciones FHIR
   - Context managers para operaciones

5. **Formatters** (`app/logging/formatters.py`)
   - Formatters especializados (JSON, FHIR, Audit)
   - Salida coloreada para desarrollo
   - Formato Prometheus para métricas

## Características Implementadas

### ✅ Sistema de Auditoría Completo
- **Eventos FHIR**: CRUD de recursos, búsquedas, transacciones
- **Eventos de Autenticación**: Login, logout, cambios de contraseña
- **Eventos del Sistema**: Inicio, parada, errores críticos
- **Context Tracking**: Request ID, User ID, Session ID, IP
- **Almacenamiento Dual**: Base de datos + archivos de log

### ✅ Logging Estructurado
- **Formato JSON**: Logs estructurados y parseables
- **Múltiples Handlers**: Archivos rotativos, consola, errores
- **Context Enrichment**: Información automática de requests
- **Performance Tracking**: Duración de operaciones
- **Error Tracking**: Stack traces completos

### ✅ Sistema de Métricas
- **Métricas en Tiempo Real**: HTTP requests, operaciones FHIR, auth
- **Alertas Automáticas**: Umbrales configurables
- **Health Checks**: Estado de BD, memoria, CPU
- **Persistencia**: Almacenamiento en BD para análisis histórico
- **Formato Prometheus**: Compatible con sistemas de monitoreo

### ✅ Middleware Integrado
- **Request/Response Logging**: Automático para todos los endpoints
- **Audit Middleware**: Auditoría selectiva de operaciones críticas
- **Performance Monitoring**: Métricas de duración automáticas
- **Error Handling**: Captura y logging de excepciones

## Base de Datos

### Tablas Principales

#### `audit_logs`
```sql
- id (UUID): Identificador único
- event_id (VARCHAR): ID único del evento
- timestamp (TIMESTAMPTZ): Timestamp con zona horaria
- action (VARCHAR): Tipo de acción (create, read, update, delete, login, etc.)
- level (VARCHAR): Nivel de auditoría (info, warning, error, critical, security)
- user_id/username: Contexto del usuario
- resource_type/resource_id: Contexto FHIR
- message/description: Detalles del evento
- metadata (JSONB): Información adicional
- duration_ms: Tiempo de procesamiento
```

#### `system_metrics`
```sql
- id (UUID): Identificador único
- timestamp (TIMESTAMPTZ): Timestamp del punto de métrica
- metric_type/metric_name: Tipo y nombre de la métrica
- value (FLOAT): Valor de la métrica
- unit (VARCHAR): Unidad de medida
- labels (JSONB): Etiquetas/dimensiones
```

#### `alerts`
```sql
- id (UUID): Identificador único
- alert_type: Tipo de alerta (performance, security, error)
- severity: Severidad (low, medium, high, critical)
- title/description: Información de la alerta
- status: Estado (active, acknowledged, resolved)
- metadata (JSONB): Contexto adicional
```

### Índices Optimizados
- **Consultas temporales**: Índices en timestamp
- **Búsquedas por usuario**: user_id + timestamp
- **Análisis FHIR**: resource_type + action
- **Búsqueda de texto**: Índices GIN para mensaje y metadatos
- **Métricas**: metric_type + metric_name + timestamp

### Distribución Citus
- `audit_logs`: Distribuida por `user_id`
- `system_metrics`: Distribuida por `resource_type`
- `alerts`: Tabla de referencia (replicada)

## Endpoints de Monitoreo

### Health Checks
```
GET /health                # Health check básico
GET /health/db            # Estado de base de datos
GET /health/cluster       # Estado del clúster Citus
GET /health/detailed      # Health check completo
```

### Métricas
```
GET /metrics              # Métricas del sistema (JSON)
GET /metrics/prometheus   # Métricas formato Prometheus
```

### Auditoría
```
GET /audit/recent         # Logs de auditoría recientes
```

## Configuración

### Variables de Entorno
```bash
LOG_LEVEL=info           # Nivel de logging (debug, info, warning, error)
LOG_FORMAT=json          # Formato de logs (json, text)
DEBUG=false              # Modo debug (logs adicionales)
```

### Configuración de Alertas
```python
alert_thresholds = {
    "http_request_duration": {"warning": 1000, "critical": 5000},  # ms
    "fhir_operation_duration": {"warning": 2000, "critical": 10000},  # ms
    "database_query_duration": {"warning": 500, "critical": 2000},  # ms
    "memory_usage": {"warning": 80, "critical": 95},  # percent
    "cpu_usage": {"warning": 80, "critical": 95},  # percent
    "errors_total": {"warning": 10, "critical": 50}  # per 5 min
}
```

## Setup y Instalación

### 1. Ejecutar Migración
```bash
./setup_logging.sh
```

### 2. Verificar Instalación
- ✅ Tablas creadas (`audit_logs`, `system_metrics`, `alerts`)
- ✅ Índices optimizados
- ✅ Funciones de utilidad
- ✅ Vistas de reporting
- ✅ Directorio de logs (`logs/`)

## Uso en el Código

### Logging Estructurado
```python
from app.logging import structured_logger

# Log básico
structured_logger.info("Operation completed", user_id="123", duration_ms=45.2)

# Log de error con contexto  
structured_logger.error("Database connection failed", 
                       error=str(e), 
                       component="database")
```

### Auditoría
```python
from app.logging import audit_fhir_operation, AuditAction

# Auditar operación FHIR
await audit_fhir_operation(
    action=AuditAction.CREATE,
    resource_type="Patient",
    resource_id="patient-123",
    user_id=user.id,
    request=request,
    duration_ms=123.45
)
```

### Métricas
```python
from app.logging.metrics import record_http_request, measure_duration

# Registrar request HTTP
record_http_request("GET", "/fhir/R4/Patient", 200, 156.7)

# Medir duración automáticamente
with measure_duration("database_query", {"table": "patients"}):
    result = await db_operation()
```

### Context Managers
```python
from app.logging.middleware import logged_operation

# Operación con logging automático
async with logged_operation("create_patient", "Patient", user_id="123"):
    patient = await create_patient_in_db(data)
```

## Archivos de Log

### Estructura de Archivos
```
logs/
├── application.log     # Logs generales de aplicación
├── audit.log          # Logs de auditoría específicos
└── errors.log         # Logs de errores únicamente
```

### Rotación de Archivos
- **Tamaño máximo**: 50MB por archivo
- **Archivos de backup**: 10 archivos históricos
- **Encoding**: UTF-8
- **Rotación automática**: Basada en tamaño

## Vistas de Reporting

### Actividad Diaria
```sql
SELECT * FROM daily_activity_summary 
WHERE activity_date >= CURRENT_DATE - INTERVAL '7 days';
```

### Usuarios Más Activos
```sql
SELECT * FROM most_active_users 
ORDER BY total_operations DESC 
LIMIT 10;
```

### Métricas de Rendimiento
```sql
SELECT * FROM performance_metrics 
WHERE success_rate < 95 
ORDER BY error_count DESC;
```

## Funciones de Utilidad

### Estadísticas de Auditoría
```sql
-- Estadísticas de las últimas 24 horas
SELECT * FROM get_audit_stats(NOW() - INTERVAL '24 hours', NOW());
```

### Limpieza de Logs Antiguos
```sql
-- Limpiar logs mayores a 90 días
SELECT cleanup_old_logs(90);
```

## Integración con Monitoreo Externo

### Prometheus
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fhir-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/prometheus'
```

### Grafana Dashboards
- **System Overview**: Métricas generales del sistema
- **FHIR Operations**: Análisis de operaciones FHIR
- **Security Audit**: Eventos de seguridad y autenticación
- **Performance Monitoring**: Latencia y throughput

## Alertas y Notificaciones

### Tipos de Alertas Configuradas
1. **Performance**: Latencia alta, throughput bajo
2. **Security**: Fallos de autenticación, accesos no autorizados
3. **System**: Errores de BD, memoria alta, CPU alta
4. **Application**: Errores críticos, timeouts

### Gestión de Alertas
```python
# Verificar alertas activas
alerts = await system_monitor.check_alerts()

# Limpiar alerta específica
system_monitor.clear_alert("http_request_duration", "warning")
```

## Análisis y Consultas Comunes

### Top Endpoints por Uso
```sql
SELECT endpoint, http_method, COUNT(*) as requests
FROM audit_logs 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY endpoint, http_method
ORDER BY requests DESC;
```

### Errores por Usuario
```sql
SELECT username, COUNT(*) as error_count
FROM audit_logs 
WHERE status_code >= 400 
  AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY username
ORDER BY error_count DESC;
```

### Operaciones FHIR más Lentas
```sql
SELECT resource_type, action, AVG(duration_ms) as avg_duration
FROM audit_logs 
WHERE resource_type IS NOT NULL 
  AND duration_ms IS NOT NULL
GROUP BY resource_type, action
ORDER BY avg_duration DESC;
```

## Troubleshooting

### Logs No Aparecen
- Verificar nivel de logging en settings
- Verificar permisos del directorio `logs/`
- Verificar conexión a base de datos

### Métricas Faltantes
- Verificar middleware está habilitado
- Verificar configuración de colector de métricas
- Verificar persistencia en BD

### Alertas No Funcionan
- Verificar umbrales de configuración
- Verificar sistema de monitoreo activo
- Verificar logs de errores del sistema

## Rendimiento y Optimización

### Optimizaciones Implementadas
- **Índices especializados** para queries comunes
- **Logging asíncrono** para no bloquear requests
- **Rotación automática** de archivos de log
- **Particionado por tiempo** (preparado para gran volumen)
- **Distribución Citus** para escalabilidad

### Configuración para Producción
- Nivel de log: `INFO` o `WARNING`
- Rotación: Diaria o por tamaño
- Retención: 30-90 días en BD, 1 año en archivos
- Monitoreo: Alertas configuradas correctamente
- Backup: Incluir logs en strategy de backup

## Compliance y Auditoría

### Estándares Cumplidos
- **HIPAA**: Auditoría de acceso a datos médicos
- **SOX**: Trazabilidad de cambios críticos
- **GDPR**: Logging de acceso a datos personales
- **ISO 27001**: Gestión de eventos de seguridad

### Retención de Datos
- **Logs de auditoría**: 7 años (configurable)
- **Métricas de sistema**: 1 año
- **Alertas**: 2 años
- **Logs de aplicación**: 90 días

El sistema de logging está completamente integrado y listo para uso en producción, proporcionando visibilidad completa de la aplicación FHIR.