"""
Filtros personalizados para templates Jinja2 en FastAPI
"""
import json
from datetime import datetime
from typing import Any

def tojsonfilter(obj: Any) -> str:
    """Convierte un objeto Python a JSON string"""
    if isinstance(obj, datetime):
        return json.dumps(obj.isoformat())
    return json.dumps(obj, ensure_ascii=False, default=str)

def dateformat(value: Any, format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Formatea una fecha"""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except:
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return str(value)

def currency(value: Any) -> str:
    """Formatea un número como moneda"""
    try:
        return f"${float(value):,.2f}"
    except:
        return str(value)

def get_flashed_messages(with_categories: bool = False) -> list:
    """Mock function para compatibilidad con Flask flash messages"""
    # FastAPI no tiene flash messages nativos, retornamos lista vacía
    return []

def url_for(endpoint: str, **values) -> str:
    """Mock function para compatibilidad con Flask url_for"""
    # Mapeo básico de rutas para FastAPI
    route_map = {
        'static': '/static',
        'dashboard_patient': '/',
        'dashboard_practitioner': '/',
        'dashboard_admin': '/',
        'dashboard_auditor': '/',
        'login': '/login',
        'logout': '/auth/logout'
    }
    
    base_url = route_map.get(endpoint, '/')
    
    # Manejar archivos estáticos
    if endpoint == 'static' and 'path' in values:
        return f"/static/{values['path']}"
    
    return base_url

def csrf_token() -> str:
    """Mock function para compatibilidad con Flask CSRF tokens"""
    # FastAPI no requiere CSRF tokens por defecto, retornamos token dummy
    import secrets
    return secrets.token_hex(16)

# Registrar todos los filtros
TEMPLATE_FILTERS = {
    'tojsonfilter': tojsonfilter,
    'dateformat': dateformat,
    'currency': currency,
}

# Funciones globales para templates
TEMPLATE_GLOBALS = {
    'get_flashed_messages': get_flashed_messages,
    'url_for': url_for,
    'csrf_token': csrf_token,
}
