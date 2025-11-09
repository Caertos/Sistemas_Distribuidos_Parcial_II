"""
Metrics and Monitoring System
Sistema de métricas y monitoreo para la aplicación FHIR
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_

from app.config.database import get_db_session
from app.logging.structured_logger import structured_logger


@dataclass
class MetricPoint:
    """Punto de métrica individual"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Serie temporal de métricas"""
    name: str
    unit: str
    description: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Agregar punto a la serie"""
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            labels=labels or {}
        )
        self.points.append(point)
    
    def get_average(self, minutes: int = 5) -> float:
        """Obtener promedio de los últimos N minutos"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_points = [p for p in self.points if p.timestamp > cutoff]
        
        if not recent_points:
            return 0.0
        
        return sum(p.value for p in recent_points) / len(recent_points)
    
    def get_latest(self) -> Optional[float]:
        """Obtener valor más reciente"""
        return self.points[-1].value if self.points else None


class MetricsCollector:
    """Colector de métricas en memoria"""
    
    def __init__(self):
        self._metrics: Dict[str, MetricSeries] = {}
        self._lock = Lock()
        
        # Métricas predefinidas
        self._init_default_metrics()
    
    def _init_default_metrics(self):
        """Inicializar métricas por defecto"""
        default_metrics = [
            ("http_requests_total", "count", "Total HTTP requests"),
            ("http_request_duration", "ms", "HTTP request duration"),
            ("fhir_operations_total", "count", "Total FHIR operations"),
            ("fhir_operation_duration", "ms", "FHIR operation duration"),
            ("auth_events_total", "count", "Total authentication events"),
            ("database_connections", "count", "Active database connections"),
            ("database_query_duration", "ms", "Database query duration"),
            ("memory_usage", "bytes", "Memory usage"),
            ("cpu_usage", "percent", "CPU usage"),
            ("active_users", "count", "Currently active users"),
            ("errors_total", "count", "Total errors"),
            ("audit_events_total", "count", "Total audit events")
        ]
        
        for name, unit, description in default_metrics:
            self._metrics[name] = MetricSeries(name, unit, description)
    
    def record_metric(
        self, 
        name: str, 
        value: float, 
        unit: str = "count",
        description: str = "",
        labels: Optional[Dict[str, str]] = None
    ):
        """Registrar métrica"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = MetricSeries(name, unit, description)
            
            self._metrics[name].add_point(value, labels)
    
    def increment_counter(
        self, 
        name: str, 
        amount: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ):
        """Incrementar contador"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = MetricSeries(name, "count", f"Counter: {name}")
            
            current = self._metrics[name].get_latest() or 0
            self._metrics[name].add_point(current + amount, labels)
    
    def record_duration(
        self, 
        name: str, 
        duration_ms: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Registrar duración"""
        self.record_metric(name, duration_ms, "ms", f"Duration: {name}", labels)
    
    def get_metric(self, name: str) -> Optional[MetricSeries]:
        """Obtener serie de métrica"""
        with self._lock:
            return self._metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, MetricSeries]:
        """Obtener todas las métricas"""
        with self._lock:
            return self._metrics.copy()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Obtener resumen de métricas"""
        with self._lock:
            summary = {}
            
            for name, series in self._metrics.items():
                latest = series.get_latest()
                avg_5min = series.get_average(5)
                
                summary[name] = {
                    "unit": series.unit,
                    "description": series.description,
                    "latest": latest,
                    "avg_5min": round(avg_5min, 2),
                    "data_points": len(series.points)
                }
            
            return summary


class SystemMonitor:
    """Monitor del sistema con alertas"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.alert_thresholds = {
            "http_request_duration": {"warning": 1000, "critical": 5000},  # ms
            "fhir_operation_duration": {"warning": 2000, "critical": 10000},  # ms
            "database_query_duration": {"warning": 500, "critical": 2000},  # ms
            "memory_usage": {"warning": 80, "critical": 95},  # percent
            "cpu_usage": {"warning": 80, "critical": 95},  # percent
            "errors_total": {"warning": 10, "critical": 50}  # per 5 min
        }
        
        self.alerts_generated = set()
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Verificar y generar alertas"""
        alerts = []
        
        for metric_name, thresholds in self.alert_thresholds.items():
            metric = self.metrics.get_metric(metric_name)
            if not metric:
                continue
            
            current_value = metric.get_average(5)  # Promedio de 5 minutos
            
            # Determinar nivel de alerta
            alert_level = None
            if current_value >= thresholds["critical"]:
                alert_level = "critical"
            elif current_value >= thresholds["warning"]:
                alert_level = "warning"
            
            if alert_level:
                alert_key = f"{metric_name}_{alert_level}"
                
                # Evitar alertas duplicadas
                if alert_key not in self.alerts_generated:
                    alert = {
                        "metric": metric_name,
                        "level": alert_level,
                        "current_value": current_value,
                        "threshold": thresholds[alert_level],
                        "unit": metric.unit,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "description": f"{metric_name} is {current_value}{metric.unit}, exceeding {alert_level} threshold of {thresholds[alert_level]}{metric.unit}"
                    }
                    
                    alerts.append(alert)
                    self.alerts_generated.add(alert_key)
                    
                    # Log alerta
                    structured_logger.warning(
                        f"Alert: {metric_name} threshold exceeded",
                        alert_level=alert_level,
                        metric_name=metric_name,
                        current_value=current_value,
                        threshold=thresholds[alert_level]
                    )
        
        return alerts
    
    def clear_alert(self, metric_name: str, level: str):
        """Limpiar alerta específica"""
        alert_key = f"{metric_name}_{level}"
        self.alerts_generated.discard(alert_key)


class HealthChecker:
    """Verificador de salud del sistema"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Obtener estado de salud del sistema"""
        
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": time.time() - self._get_start_time(),
            "checks": {}
        }
        
        # Verificar base de datos
        db_health = await self._check_database_health()
        health_status["checks"]["database"] = db_health
        
        # Verificar métricas
        metrics_health = self._check_metrics_health()
        health_status["checks"]["metrics"] = metrics_health
        
        # Verificar memoria
        memory_health = self._check_memory_health()
        health_status["checks"]["memory"] = memory_health
        
        # Determinar estado general
        failed_checks = [name for name, check in health_status["checks"].items() if not check["healthy"]]
        
        if failed_checks:
            health_status["status"] = "unhealthy"
            health_status["failed_checks"] = failed_checks
        
        return health_status
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Verificar salud de la base de datos"""
        try:
            async with get_db_session() as session:
                # Query simple para verificar conectividad
                result = await session.execute("SELECT 1")
                result.fetchone()
                
                return {
                    "healthy": True,
                    "message": "Database connection successful",
                    "response_time_ms": 10  # Placeholder
                }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Database connection failed: {str(e)}",
                "error": str(e)
            }
    
    def _check_metrics_health(self) -> Dict[str, Any]:
        """Verificar salud del sistema de métricas"""
        try:
            metrics_count = len(self.metrics.get_all_metrics())
            
            return {
                "healthy": True,
                "message": f"Metrics system operational with {metrics_count} metrics",
                "metrics_count": metrics_count
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Metrics system error: {str(e)}",
                "error": str(e)
            }
    
    def _check_memory_health(self) -> Dict[str, Any]:
        """Verificar uso de memoria"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            return {
                "healthy": memory_percent < 90,
                "message": f"Memory usage: {memory_percent}%",
                "memory_percent": memory_percent,
                "available_mb": memory.available // (1024 * 1024)
            }
        except ImportError:
            return {
                "healthy": True,
                "message": "Memory monitoring not available (psutil not installed)",
                "warning": "Install psutil for memory monitoring"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Memory check failed: {str(e)}",
                "error": str(e)
            }
    
    def _get_start_time(self) -> float:
        """Obtener tiempo de inicio de la aplicación"""
        # Placeholder - idealmente esto se establecería al inicio de la app
        return time.time() - 3600  # 1 hora atrás como ejemplo


class MetricsPersistence:
    """Persistencia de métricas en base de datos"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    async def save_metrics_to_db(self):
        """Guardar métricas actuales en base de datos"""
        try:
            async with get_db_session() as session:
                from app.models.orm.audit import SystemMetricsORM
                
                metrics_to_save = []
                current_time = datetime.now(timezone.utc)
                
                for name, series in self.metrics.get_all_metrics().items():
                    latest_value = series.get_latest()
                    if latest_value is not None:
                        metric_record = SystemMetricsORM(
                            timestamp=current_time,
                            metric_type="application",
                            metric_name=name,
                            value=latest_value,
                            unit=series.unit,
                            labels={"component": "fhir_api"}
                        )
                        metrics_to_save.append(metric_record)
                
                if metrics_to_save:
                    session.add_all(metrics_to_save)
                    await session.commit()
                    
                    structured_logger.info(
                        f"Saved {len(metrics_to_save)} metrics to database",
                        saved_metrics=len(metrics_to_save),
                        timestamp=current_time.isoformat()
                    )
        
        except Exception as e:
            structured_logger.error(
                "Failed to save metrics to database",
                error=str(e),
                error_type=type(e).__name__
            )
    
    async def cleanup_old_metrics(self, days_to_keep: int = 30):
        """Limpiar métricas antiguas de la base de datos"""
        try:
            async with get_db_session() as session:
                from app.models.orm.audit import SystemMetricsORM
                
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
                
                result = await session.execute(
                    "DELETE FROM system_metrics WHERE timestamp < :cutoff_date",
                    {"cutoff_date": cutoff_date}
                )
                
                await session.commit()
                
                deleted_count = result.rowcount
                structured_logger.info(
                    f"Cleaned up {deleted_count} old metric records",
                    deleted_count=deleted_count,
                    cutoff_date=cutoff_date.isoformat()
                )
        
        except Exception as e:
            structured_logger.error(
                "Failed to cleanup old metrics",
                error=str(e),
                error_type=type(e).__name__
            )


# Instancias globales
metrics_collector = MetricsCollector()
system_monitor = SystemMonitor(metrics_collector)
health_checker = HealthChecker(metrics_collector)
metrics_persistence = MetricsPersistence(metrics_collector)


# Context manager para medir duración automáticamente
class measure_duration:
    """Context manager para medir duración de operaciones"""
    
    def __init__(
        self, 
        metric_name: str, 
        labels: Optional[Dict[str, str]] = None
    ):
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            metrics_collector.record_duration(
                self.metric_name, 
                duration_ms, 
                self.labels
            )


# Funciones de conveniencia
def record_http_request(method: str, endpoint: str, status_code: int, duration_ms: float):
    """Registrar métrica de request HTTP"""
    labels = {
        "method": method,
        "endpoint": endpoint,
        "status_code": str(status_code)
    }
    
    metrics_collector.increment_counter("http_requests_total", labels=labels)
    metrics_collector.record_duration("http_request_duration", duration_ms, labels)


def record_fhir_operation(operation: str, resource_type: str, success: bool, duration_ms: float):
    """Registrar métrica de operación FHIR"""
    labels = {
        "operation": operation,
        "resource_type": resource_type,
        "success": str(success)
    }
    
    metrics_collector.increment_counter("fhir_operations_total", labels=labels)
    metrics_collector.record_duration("fhir_operation_duration", duration_ms, labels)


def record_auth_event(event_type: str, success: bool):
    """Registrar evento de autenticación"""
    labels = {
        "event_type": event_type,
        "success": str(success)
    }
    
    metrics_collector.increment_counter("auth_events_total", labels=labels)


def record_database_query(duration_ms: float, table: Optional[str] = None):
    """Registrar consulta de base de datos"""
    labels = {"table": table} if table else {}
    metrics_collector.record_duration("database_query_duration", duration_ms, labels)


def record_error(error_type: str, component: str):
    """Registrar error"""
    labels = {
        "error_type": error_type,
        "component": component
    }
    
    metrics_collector.increment_counter("errors_total", labels=labels)