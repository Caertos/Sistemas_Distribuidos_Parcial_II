"""Controladores skeleton para la capa Practitioner.

Estos son controladores mínimos que más adelante se reemplazarán por lógica
completa (DB, validaciones FHIR, auditable, etc.). Se dejan aquí para facilitar
la evolución, e incluir pruebas de permisos.
"""
from typing import Dict, Any


def to_api_response(obj: Dict[str, Any]) -> Dict[str, Any]:
    return obj


def get_patient_controller(patient_id: str):
    return to_api_response({"patient_id": patient_id, "name": "John Doe (ejemplo)"})


def list_appointments_controller(admitted: bool = True):
    sample = [
        {"id": 1, "patient_id": "P-001", "time": "2025-11-20T10:00:00Z", "admitted": True},
        {"id": 2, "patient_id": "P-002", "time": "2025-11-20T11:00:00Z", "admitted": False},
    ]
    results = [s for s in sample if s["admitted"] == admitted]
    return {"count": len(results), "items": results}


def create_encounter_controller(payload: Dict[str, Any]):
    # Return a 501-style payload describing the missing implementation
    return {"status": "not_implemented", "payload": payload}


def create_observation_controller(payload: Dict[str, Any]):
    return {"status": "not_implemented", "payload": payload}


def create_medication_controller(payload: Dict[str, Any]):
    return {"status": "not_implemented", "payload": payload}
