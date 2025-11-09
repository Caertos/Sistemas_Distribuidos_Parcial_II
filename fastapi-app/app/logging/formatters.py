"""
Custom Logging Formatters
Formatters personalizados para diferentes tipos de logs
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Formatter JSON estructurado para logs"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatear record como JSON"""
        
        # Información básica del log
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Agregar campos extra si están disponibles
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                    'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                    'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                    'thread', 'threadName', 'processName', 'process', 'message'
                ]:
                    log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class FHIRFormatter(logging.Formatter):
    """Formatter específico para operaciones FHIR"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatear record para operaciones FHIR"""
        
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Extraer información FHIR del record
        resource_type = getattr(record, 'resource_type', 'Unknown')
        resource_id = getattr(record, 'resource_id', '')
        operation = getattr(record, 'fhir_operation', 'Unknown')
        user_id = getattr(record, 'user_id', 'Anonymous')
        duration = getattr(record, 'duration_ms', 0)
        
        # Formato específico para FHIR
        resource_info = f"{resource_type}"
        if resource_id:
            resource_info += f"/{resource_id}"
        
        message = (
            f"{timestamp} | {record.levelname} | "
            f"FHIR {operation} | {resource_info} | "
            f"User: {user_id} | {duration:.2f}ms | "
            f"{record.getMessage()}"
        )
        
        return message


class AuditFormatter(logging.Formatter):
    """Formatter específico para logs de auditoría"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatear record para auditoría"""
        
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Extraer información de auditoría
        action = getattr(record, 'action', 'Unknown')
        user_id = getattr(record, 'user_id', 'System')
        ip_address = getattr(record, 'ip_address', 'Unknown')
        resource_type = getattr(record, 'resource_type', '')
        resource_id = getattr(record, 'resource_id', '')
        
        # Construir mensaje de auditoría
        message_parts = [
            timestamp,
            record.levelname,
            f"ACTION:{action}",
            f"USER:{user_id}",
            f"IP:{ip_address}"
        ]
        
        if resource_type:
            resource_info = resource_type
            if resource_id:
                resource_info += f"/{resource_id}"
            message_parts.append(f"RESOURCE:{resource_info}")
        
        message_parts.append(record.getMessage())
        
        return " | ".join(message_parts)


class ColoredConsoleFormatter(logging.Formatter):
    """Formatter con colores para consola (desarrollo)"""
    
    # Códigos de color ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatear record con colores"""
        
        # Color basado en nivel
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Mensaje básico
        message = (
            f"{color}[{timestamp}] {record.levelname:8s}{reset} "
            f"{record.name}: {record.getMessage()}"
        )
        
        # Agregar información adicional si existe
        extras = []
        
        # Información FHIR
        if hasattr(record, 'resource_type'):
            resource_info = record.resource_type
            if hasattr(record, 'resource_id') and record.resource_id:
                resource_info += f"/{record.resource_id}"
            extras.append(f"Resource: {resource_info}")
        
        # Información de usuario
        if hasattr(record, 'user_id') and record.user_id:
            extras.append(f"User: {record.user_id}")
        
        # Duración
        if hasattr(record, 'duration_ms') and record.duration_ms:
            extras.append(f"{record.duration_ms:.2f}ms")
        
        # Request ID
        if hasattr(record, 'request_id') and record.request_id:
            extras.append(f"ReqID: {record.request_id}")
        
        if extras:
            message += f" [{', '.join(extras)}]"
        
        # Agregar excepción si existe
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


class MetricsFormatter(logging.Formatter):
    """Formatter específico para métricas y monitoring"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatear record para métricas"""
        
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        
        # Si es un log de métrica, formatear especialmente
        if hasattr(record, 'event_type') and record.event_type == 'performance':
            metric_name = getattr(record, 'metric_name', 'unknown')
            metric_value = getattr(record, 'metric_value', 0)
            metric_unit = getattr(record, 'metric_unit', '')
            metric_labels = getattr(record, 'metric_labels', {})
            
            # Formato de métrica (estilo Prometheus)
            labels_str = ''
            if metric_labels:
                label_pairs = [f'{k}="{v}"' for k, v in metric_labels.items()]
                labels_str = '{' + ','.join(label_pairs) + '}'
            
            return f"{timestamp} METRIC {metric_name}{labels_str} {metric_value}{metric_unit}"
        
        # Formato general para otros logs
        return f"{timestamp} {record.levelname} {record.getMessage()}"


class StructuredTextFormatter(logging.Formatter):
    """Formatter que combina legibilidad humana con estructura"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatear record como texto estructurado"""
        
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Línea principal
        main_line = f"{timestamp} [{record.levelname:8s}] {record.name}: {record.getMessage()}"
        
        # Recopilar información adicional
        context_info = []
        
        # Información de request
        if hasattr(record, 'request_id'):
            context_info.append(f"request_id={record.request_id}")
        
        # Información de usuario
        if hasattr(record, 'user_id'):
            context_info.append(f"user_id={record.user_id}")
        
        # Información FHIR
        if hasattr(record, 'resource_type'):
            resource_info = record.resource_type
            if hasattr(record, 'resource_id') and record.resource_id:
                resource_info += f"/{record.resource_id}"
            context_info.append(f"resource={resource_info}")
        
        # Información de timing
        if hasattr(record, 'duration_ms'):
            context_info.append(f"duration={record.duration_ms:.2f}ms")
        
        # IP Address
        if hasattr(record, 'ip_address'):
            context_info.append(f"ip={record.ip_address}")
        
        # Agregar contexto si existe
        if context_info:
            main_line += f" [{', '.join(context_info)}]"
        
        # Agregar excepción si existe
        if record.exc_info:
            main_line += f"\n{self.formatException(record.exc_info)}"
        
        return main_line