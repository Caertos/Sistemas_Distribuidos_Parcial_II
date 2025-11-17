from typing import List, Dict, Any
from fastapi import HTTPException


def list_logs(service: str = None, tail: int = 200) -> List[Dict[str, Any]]:
    """Stub: devuelve una lista de logs de ejemplo.

    Parámetros opcionales para simular filtrado.
    """
    # Ejemplo estático; en producción se conectaría a admin_monitoring.get_logs
    sample = [
        {"id": 1, "service": service or "api", "message": "User login", "who": "user:123", "when": "2025-11-17T10:00:00Z"},
        {"id": 2, "service": service or "api", "message": "Accessed patient record", "who": "user:auditor1", "when": "2025-11-17T10:05:00Z"},
    ]
    return sample[:tail]


def get_log(log_id: int) -> Dict[str, Any]:
    """Stub: devuelve un log de ejemplo o 404 si no existe."""
    if log_id == 1:
        return {"id": 1, "service": "api", "message": "User login", "who": "user:123", "when": "2025-11-17T10:00:00Z"}
    if log_id == 2:
        return {"id": 2, "service": "api", "message": "Accessed patient record", "who": "user:auditor1", "when": "2025-11-17T10:05:00Z"}
    raise HTTPException(status_code=404, detail="Log not found")


def export_audit(format: str = "csv", service: str = None) -> bytes:
    """Stub: genera un export simple en CSV o PDF (simulado).

    Retorna bytes que pueden ser devueltos con el content-type adecuado.
    """
    if format == "csv":
        csv = "id,service,who,when,message\n"
        for l in list_logs(service=service, tail=100):
            csv += f"{l['id']},{l['service']},{l['who']},{l['when']},{l['message']}\n"
        return csv.encode("utf-8")
    if format == "pdf":
        # PDF real requeriría ReportLab u otra librería; aquí devolvemos un marcador
        return b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n% Fake PDF content for audit export\n"
    raise HTTPException(status_code=400, detail="Unsupported format")
