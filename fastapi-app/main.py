"""
FastAPI Main Application
Sistema Distribuido de Historias Clínicas - FHIR
PostgreSQL + Citus Backend
"""

from fastapi import FastAPI, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from datetime import datetime, timedelta, timezone
import os

# Configuración local
from app.config.settings import settings
from app.config.database import db_manager, get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_connection_test, get_cluster_health

# Importar routers FHIR
from app.routes import register_all_routers

# Importar rutas de autenticación
from app.routes.auth import router as auth_router

# Importar middleware de autenticación
from app.auth import AuthMiddleware, get_current_user, require_roles

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

# Configurar templates y archivos estáticos
templates = Jinja2Templates(directory="templates")

# Agregar filtros personalizados para compatibilidad con templates Flask
from app.template_filters import TEMPLATE_FILTERS
for filter_name, filter_func in TEMPLATE_FILTERS.items():
    templates.env.filters[filter_name] = filter_func

# Montar archivos estáticos
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

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
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Página de inicio del sistema FHIR"""
    return templates.TemplateResponse("homepage.html", {
        "request": request,
        "version": settings.app_version,
        "environment": settings.environment,
        "app_name": settings.app_name
    })

@app.get("/api")
async def api_info():
    """Endpoint de información de la API (JSON)"""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Rutas de autenticación y dashboards
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "version": settings.app_version,
        "environment": settings.environment
    })

@app.get("/dashboard/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: dict = Depends(require_roles(["admin"])), db: AsyncSession = Depends(get_db_session)):
    """Dashboard de administrador - Requiere rol admin"""
    from app.models.orm.patient import PatientORM
    from app.models.orm.practitioner import PractitionerORM
    from sqlalchemy import func, select
    
    # Obtener estadísticas reales de la base de datos
    total_patients_result = await db.execute(select(func.count(PatientORM.id)))
    total_patients = total_patients_result.scalar() or 0
    
    total_practitioners_result = await db.execute(select(func.count(PractitionerORM.id)))
    total_practitioners = total_practitioners_result.scalar() or 0
    
    # Datos de ejemplo para gráficos (luego se pueden hacer dinámicos)
    chart_data = {
        "labels": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"],
        "encounters": [120, 150, 180, 200, 170, 190],
        "patients": [80, 95, 110, 125, 115, 130]
    }
    
    stats = {
        "total_patients": total_patients,
        "total_practitioners": total_practitioners,
        "monthly_encounters": 1250,  # TODO: calcular dinámicamente
        "system_uptime": "99.8%"
    }
    
    return templates.TemplateResponse("admin_simple.html", {
        "request": request,
        "user_role": current_user.get("role", "admin"),
        "current_user": current_user,
        "chart_data": chart_data,
        "stats": stats,
        "theme": "light"
    })

@app.get("/dashboard/practitioner", response_class=HTMLResponse)  
async def practitioner_dashboard(request: Request, current_user: dict = Depends(require_roles(["practitioner", "admin"])), db: AsyncSession = Depends(get_db_session)):
    """Dashboard de médico - Requiere rol practitioner o admin"""
    from app.models.orm.patient import PatientORM
    from sqlalchemy import func, select
    
    # Obtener estadísticas reales del médico
    user_id = current_user.get("id")
    
    # Contar pacientes totales (se podría filtrar por médico si hubiera relación)
    total_patients_result = await db.execute(select(func.count(PatientORM.id)))
    total_patients = total_patients_result.scalar() or 0
    
    # Datos de ejemplo para citas (luego se pueden hacer dinámicos)
    appointments = [
        {"time": "09:00", "patient": "María García", "type": "Consulta General"},
        {"time": "10:30", "patient": "José López", "type": "Control"},
        {"time": "11:15", "patient": "Ana Martín", "type": "Seguimiento"}
    ]
    
    stats = {
        "patients_today": 5,  # TODO: calcular dinámicamente
        "pending_reports": 3,  # TODO: calcular dinámicamente
        "appointments_week": 28,  # TODO: calcular dinámicamente
        "total_patients": total_patients
    }

@app.get("/dashboard/patient", response_class=HTMLResponse)
async def patient_dashboard(request: Request, current_user: dict = Depends(require_roles(["patient", "admin"])), db: AsyncSession = Depends(get_db_session)):
    """Dashboard de paciente - Requiere rol patient o admin"""
    from app.models.orm.condition import ConditionORM
    from app.models.orm.observation import ObservationORM
    from sqlalchemy import func, select
    
    # Obtener datos médicos del paciente
    user_id = current_user.get("id")
    username = current_user.get("username", "")
    
    # Buscar condiciones médicas del paciente (por identificador similar al username)
    conditions_result = await db.execute(
        select(func.count(ConditionORM.id)).where(
            ConditionORM.patient_reference.like(f"%{username}%")
        )
    )
    total_conditions = conditions_result.scalar() or 0
    
    # Datos de ejemplo para historial médico (luego se pueden hacer dinámicos)
    medical_history = [
        {"date": "2025-11-05", "type": "Consulta General", "doctor": "Dr. García", "status": "Completada"},
        {"date": "2025-10-20", "type": "Laboratorio", "doctor": "Dr. López", "status": "Resultados disponibles"},
        {"date": "2025-09-15", "type": "Control", "doctor": "Dr. García", "status": "Completada"}
    ]
    
    next_appointments = [
        {"date": "2025-11-15", "time": "10:30", "doctor": "Dr. García", "type": "Control"},
        {"date": "2025-11-20", "time": "09:00", "doctor": "Dr. López", "type": "Seguimiento"}
    ]

@app.get("/dashboard/auditor", response_class=HTMLResponse)
async def auditor_dashboard(request: Request, current_user: dict = Depends(require_roles(["auditor", "admin"])), db: AsyncSession = Depends(get_db_session)):
    """Dashboard de auditor - Requiere rol auditor o admin"""
    from app.models.orm.audit import AuditLogORM
    from sqlalchemy import func, select, desc
    
    # Obtener logs de auditoría reales
    recent_logs_result = await db.execute(
        select(AuditLogORM)
        .order_by(desc(AuditLogORM.timestamp))
        .limit(10)
    )
    recent_logs = recent_logs_result.scalars().all()
    
    # Convertir logs a formato para template
    audit_logs = []
    for log in recent_logs:
        audit_logs.append({
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "",
            "user": log.user_id or "system",
            "action": log.action or "UNKNOWN",
            "resource": log.resource_type or "N/A",
            "status": "success" if log.status_code and log.status_code < 400 else "error"
        })
    
    # Obtener estadísticas de auditoría
    total_logs_result = await db.execute(select(func.count(AuditLogORM.id)))
    total_logs = total_logs_result.scalar() or 0
    
    stats = {
        "total_events": total_logs,
        "failed_auth": 3,  # TODO: calcular dinámicamente
        "data_access": 98,  # TODO: calcular dinámicamente
        "compliance_score": "98.5%"
    }
    
    return templates.TemplateResponse("audit/dashboard.html", {
        "request": request,
        "user_role": current_user.get("role", "auditor"),
        "current_user": current_user,
        "audit_logs": audit_logs,
        "stats": stats,
        "theme": "light"
    })

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