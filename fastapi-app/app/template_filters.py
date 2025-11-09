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

# Registrar todos los filtros
TEMPLATE_FILTERS = {
    'tojsonfilter': tojsonfilter,
    'dateformat': dateformat,
    'currency': currency,
}
