"""
FastAPI Main Application
Sistema Distribuido de Historias Clínicas - FHIR
PostgreSQL + Citus Backend
"""

from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from datetime import datetime, timedelta, timezone

# Configuración local
from app.config.settings import settings
from app.config.database import db_manager, get_db_session
from app.utils.database import get_connection_test, get_cluster_health

# Importar routers FHIR
from app.routes import register_all_routers

# Importar rutas de autenticación
from app.routes.auth import router as auth_router

# Importar middleware de autenticación
from app.auth import AuthMiddleware

# Importar sistema de logging y métricas
from app.logging import (
    LoggingMiddleware, 
    AuditMiddleware,
    structured_logger,
    audit_logger,
    AuditAction,
    AuditLevel
)
from app.logging.metrics import (
    metrics_collector,
    system_monitor, 
    health_checker,
    metrics_persistence
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Metadata de la aplicación
app = FastAPI(
    title=settings.app_name,
    description="Sistema distribuido de historias clínicas basado en estándar FHIR R4 con PostgreSQL + Citus",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.debug
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware de logging (antes que otros)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuditMiddleware)

# Agregar middleware de autenticación
app.add_middleware(AuthMiddleware)

# Registrar rutas de autenticación
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Registrar todos los routers FHIR
register_all_routers(app)

# Eventos de aplicación
@app.on_event("startup")
async def startup_event():
    """Eventos de inicio de la aplicación"""
    logger.info(f"Iniciando {settings.app_name} v{settings.app_version}")
    logger.info(f"Entorno: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")
    
    # Log estructurado de inicio
    structured_logger.info(
        "Application starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug
    )
    
    # Auditar inicio del sistema
    await audit_logger.log_system_event(
        action=AuditAction.SYSTEM_START,
        level=AuditLevel.INFO,
        message=f"System starting - {settings.app_name} v{settings.app_version}",
        metadata={
            "environment": settings.environment,
            "debug": settings.debug
        }
    )
    
    # Test de conexión inicial
    connection_test = get_connection_test()
    if connection_test["success"]:
        logger.info("✅ Conexión a base de datos establecida")
        structured_logger.info("Database connection established", **connection_test)
    else:
        logger.error(f"❌ Error de conexión a base de datos: {connection_test.get('error')}")
        structured_logger.error("Database connection failed", **connection_test)

@app.on_event("shutdown")
async def shutdown_event():
    """Eventos de cierre de la aplicación"""
    logger.info("Cerrando conexiones de base de datos...")
    
    # Log estructurado de cierre
    structured_logger.info("Application shutting down")
    
    # Auditar cierre del sistema
    await audit_logger.log_system_event(
        action=AuditAction.SYSTEM_STOP,
        level=AuditLevel.INFO,
        message="System shutting down gracefully"
    )
    
    # Guardar métricas finales
    try:
        await metrics_persistence.save_metrics_to_db()
        structured_logger.info("Final metrics saved to database")
    except Exception as e:
        structured_logger.error("Failed to save final metrics", error=str(e))
    
    db_manager.close_connections()
    logger.info("Aplicación cerrada")

# Endpoints básicos
@app.get("/")
async def root():
    """Endpoint raíz - Información de la API"""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy", 
        "service": "fastapi-fhir-api",
        "version": settings.app_version,
        "environment": settings.environment
    }

@app.get("/health/db")
async def health_check_database():
    """Health check de conexión a base de datos"""
    connection_test = get_connection_test()
    return {
        "status": "healthy" if connection_test["success"] else "unhealthy",
        "database": connection_test
    }

@app.get("/health/cluster") 
async def health_check_cluster():
    """Health check del clúster Citus"""
    cluster_health = get_cluster_health()
    return {
        "status": "healthy" if cluster_health["database_connection"] else "unhealthy",
        "cluster": cluster_health
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Health check detallado del sistema"""
    health_status = await health_checker.get_health_status()
    
    # Registrar métrica de health check
    metrics_collector.increment_counter("health_checks_total")
    
    return health_status

@app.get("/metrics")
async def get_metrics():
    """Endpoint de métricas del sistema"""
    metrics_summary = metrics_collector.get_metrics_summary()
    
    # Verificar alertas
    alerts = await system_monitor.check_alerts()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics_summary,
        "alerts": alerts,
        "system_status": "healthy" if not alerts else "warning"
    }

@app.get("/metrics/prometheus")
async def get_metrics_prometheus():
    """Endpoint de métricas en formato Prometheus"""
    metrics = metrics_collector.get_all_metrics()
    
    prometheus_output = []
    
    for name, series in metrics.items():
        # Agregar metadata
        prometheus_output.append(f"# HELP {name} {series.description}")
        prometheus_output.append(f"# TYPE {name} gauge")
        
        # Agregar valor actual
        latest_value = series.get_latest()
        if latest_value is not None:
            prometheus_output.append(f"{name} {latest_value}")
    
    return Response(
        content="\n".join(prometheus_output),
        media_type="text/plain"
    )

@app.get("/audit/recent")
async def get_recent_audit_logs():
    """Obtener logs de auditoría recientes (último día)"""
    try:
        async with get_db_session() as session:
            from app.models.orm.audit import AuditLogORM
            from sqlalchemy import desc
            
            # Obtener logs de las últimas 24 horas
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            result = await session.execute(
                session.query(AuditLogORM)
                .filter(AuditLogORM.timestamp >= cutoff_time)
                .order_by(desc(AuditLogORM.timestamp))
                .limit(100)
            )
            
            audit_logs = result.scalars().all()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "total_logs": len(audit_logs),
                "logs": [log.to_dict() for log in audit_logs]
            }
    
    except Exception as e:
        structured_logger.error("Failed to fetch audit logs", error=str(e))
        return {
            "error": "Failed to fetch audit logs",
            "message": str(e)
        }

@app.get("/metrics")
async def metrics():
    """Métricas básicas del sistema"""
    cluster_info = db_manager.get_cluster_info()
    health_info = db_manager.health_check()
    
    return {
        "timestamp": "2024-11-08T19:00:00Z",
        "environment": settings.environment,
        "version": settings.app_version,
        "database": {
            "coordinator_healthy": health_info["coordinator"],
            "workers_total": health_info["total_workers"],
            "workers_healthy": health_info["healthy_workers"],
            "distributed_tables": len(cluster_info.get("distributed_tables", [])),
            "total_shards": cluster_info.get("shards", 0)
        }
    }

# Endpoints FHIR generales
@app.get("/fhir/R4/metadata")
async def fhir_capability_statement():
    """
    FHIR R4 Capability Statement del servidor
    
    Endpoint requerido por FHIR que describe las capacidades
    del servidor y recursos soportados.
    """
    from app.routes import get_endpoint_info
    
    endpoint_info = get_endpoint_info()
    resources = []
    
    for resource_type, info in endpoint_info.items():
        resource = {
            "type": resource_type,
            "interaction": [
                {"code": op} for op in info["operations"]
            ],
            "searchParam": [
                {"name": param, "type": "string"} for param in info["search_params"]
            ]
        }
        resources.append(resource)
    
    return {
        "resourceType": "CapabilityStatement",
        "id": "fhir-server-capability",
        "url": "http://example.com/fhir/CapabilityStatement",
        "version": settings.app_version,
        "name": "FHIRServerCapabilityStatement",
        "title": "FHIR R4 Server Capability Statement",
        "status": "active",
        "date": "2025-11-08",
        "publisher": "Healthcare System",
        "description": "FHIR R4 capabilities for distributed healthcare system with Citus",
        "kind": "instance",
        "software": {
            "name": settings.app_name,
            "version": settings.app_version
        },
        "implementation": {
            "description": "Distributed FHIR R4 server with PostgreSQL + Citus backend",
            "url": "http://localhost:8000/fhir/R4"
        },
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "documentation": "FHIR R4 REST API with distributed data storage",
            "security": {
                "description": "Healthcare system authentication required"
            },
            "resource": resources
        }]
    }

@app.get("/fhir/R4")
async def fhir_base():
    """
    Base endpoint FHIR R4
    
    Punto de entrada principal para la API FHIR.
    """
    return {
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": "information",
            "code": "informational",
            "diagnostics": f"FHIR R4 Server - {settings.app_name} v{settings.app_version}. Use /fhir/R4/metadata for capabilities."
        }]
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )