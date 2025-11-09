"""
MedicationRequest API Routes - Endpoints FHIR R4 para gestión de solicitudes de medicamentos

Implementa endpoints REST compatibles con FHIR R4 para operaciones CRUD
y búsqueda avanzada de recursos MedicationRequest (recurso distribuido).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models import (
    MedicationRequestCreate,
    MedicationRequestUpdate, 
    MedicationRequestResponse,
    MedicationRequestSearchParams
)
from app.services import medication_request_service
from app.services.base import ResourceNotFoundException, ValidationException

# Crear router con prefijo FHIR estándar
router = APIRouter(
    prefix="/fhir/R4/MedicationRequest",
    tags=["MedicationRequest"],
    responses={
        404: {"description": "MedicationRequest not found"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"}
    }
)

@router.post("/", response_model=MedicationRequestResponse, status_code=201)
async def create_medication_request(
    medication_request_data: MedicationRequestCreate,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Crear una nueva solicitud de medicamento FHIR R4
    
    - **medication_request_data**: Datos de la solicitud según especificación FHIR R4
    - **documento_id**: ID de documento para co-localización en Citus
    """
    try:
        medication_request = await medication_request_service.create(
            session=session, 
            medication_request_data=medication_request_data,
            documento_id=documento_id
        )
        return medication_request
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{medication_request_id}", response_model=MedicationRequestResponse)
async def get_medication_request(
    medication_request_id: str = Path(..., description="MedicationRequest ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener solicitud de medicamento por ID
    
    - **medication_request_id**: ID único de la solicitud
    - **documento_id**: ID de documento para co-localización
    """
    try:
        medication_request = await medication_request_service.get_by_id(
            session=session,
            resource_id=medication_request_id,
            documento_id=documento_id
        )
        
        if not medication_request:
            raise HTTPException(status_code=404, detail="MedicationRequest not found")
        
        return medication_request
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{medication_request_id}", response_model=MedicationRequestResponse)
async def update_medication_request(
    medication_request_id: str = Path(..., description="MedicationRequest ID"),
    medication_request_data: MedicationRequestUpdate = ...,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Actualizar solicitud de medicamento existente
    
    - **medication_request_id**: ID único de la solicitud
    - **medication_request_data**: Datos de actualización de la solicitud
    - **documento_id**: ID de documento para co-localización
    """
    try:
        medication_request = await medication_request_service.update(
            session=session,
            resource_id=medication_request_id,
            medication_request_data=medication_request_data,
            documento_id=documento_id
        )
        return medication_request
        
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="MedicationRequest not found")
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{medication_request_id}", status_code=204)
async def delete_medication_request(
    medication_request_id: str = Path(..., description="MedicationRequest ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Eliminar solicitud de medicamento
    
    - **medication_request_id**: ID único de la solicitud
    - **documento_id**: ID de documento para co-localización
    """
    try:
        success = await medication_request_service.delete(
            session=session,
            resource_id=medication_request_id,
            documento_id=documento_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="MedicationRequest not found")
            
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="MedicationRequest not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=dict)
async def search_medication_requests(
    # Parámetros de búsqueda FHIR estándar
    patient: Optional[str] = Query(None, description="Patient ID"),
    medication: Optional[str] = Query(None, description="Medication code or name"),
    status: Optional[str] = Query(None, description="Request status"),
    intent: Optional[str] = Query(None, description="Request intent"),
    priority: Optional[str] = Query(None, description="Request priority"),
    requester: Optional[str] = Query(None, description="Practitioner ID"),
    authored_on: Optional[str] = Query(None, alias="authored-on", description="Authored date (YYYY-MM-DD)"),
    
    # Parámetros de paginación
    _count: int = Query(20, alias="_count", ge=1, le=100, description="Number of results per page"),
    _page: int = Query(1, alias="_page", ge=1, description="Page number"),
    
    # Parámetros de ordenamiento
    _sort: Optional[str] = Query(None, alias="_sort", description="Sort field (authored-on, status, medication)"),
    _order: str = Query("desc", alias="_order", regex="^(asc|desc)$", description="Sort order"),
    
    # Filtro opcional por documento
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    
    session: AsyncSession = Depends(get_db_session)
):
    """
    Buscar solicitudes de medicamentos con parámetros FHIR R4
    
    Soporta búsqueda por múltiples criterios con paginación y ordenamiento.
    Compatible con especificación FHIR R4 search parameters.
    """
    try:
        # Construir parámetros de búsqueda
        search_params = MedicationRequestSearchParams(
            patient=patient,
            medication=medication,
            status=status,
            intent=intent,
            priority=priority,
            requester=requester,
            authored_on=authored_on,
            page=_page,
            size=_count,
            sort=_sort,
            order=_order
        )
        
        # Ejecutar búsqueda
        result = await medication_request_service.search(
            session=session,
            search_params=search_params,
            documento_id=documento_id
        )
        
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}", response_model=List[MedicationRequestResponse])
async def get_medication_requests_by_patient(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener todas las solicitudes de medicamentos de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        medication_requests = await medication_request_service.get_by_patient(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return medication_requests
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}/active", response_model=List[MedicationRequestResponse])
async def get_active_prescriptions(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener prescripciones activas de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        prescriptions = await medication_request_service.get_active_prescriptions(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return prescriptions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/practitioner/{practitioner_id}", response_model=List[MedicationRequestResponse])
async def get_medication_requests_by_practitioner(
    practitioner_id: int = Path(..., description="Practitioner ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener solicitudes de medicamentos por profesional prescriptor
    
    - **practitioner_id**: ID del profesional
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        medication_requests = await medication_request_service.get_by_professional(
            session=session,
            profesional_id=practitioner_id,
            documento_id=documento_id
        )
        
        return medication_requests
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/medication/{medication_code}", response_model=List[MedicationRequestResponse])
async def get_medication_requests_by_medication(
    medication_code: str = Path(..., description="Medication code"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener solicitudes por medicamento específico
    
    - **medication_code**: Código del medicamento
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        medication_requests = await medication_request_service.get_by_medication(
            session=session,
            codigo_medicamento=medication_code,
            documento_id=documento_id
        )
        
        return medication_requests
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Endpoint de metadatos FHIR (CapabilityStatement)
@router.get("/$metadata", response_model=dict)
async def medication_request_capability_statement():
    """
    FHIR CapabilityStatement para recurso MedicationRequest
    """
    return {
        "resourceType": "CapabilityStatement",
        "id": "medication-request-capability",
        "url": "http://example.com/fhir/CapabilityStatement/medication-request",
        "version": "1.0.0",
        "name": "MedicationRequestCapabilityStatement", 
        "title": "MedicationRequest Resource Capability Statement",
        "status": "active",
        "date": "2025-11-08",
        "publisher": "Healthcare System",
        "description": "FHIR R4 MedicationRequest resource capabilities",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "MedicationRequest",
                "interaction": [
                    {"code": "read"},
                    {"code": "create"},
                    {"code": "update"},
                    {"code": "delete"},
                    {"code": "search-type"}
                ],
                "searchParam": [
                    {"name": "patient", "type": "reference"},
                    {"name": "medication", "type": "token"},
                    {"name": "status", "type": "token"},
                    {"name": "intent", "type": "token"},
                    {"name": "priority", "type": "token"},
                    {"name": "requester", "type": "reference"},
                    {"name": "authored-on", "type": "date"}
                ]
            }]
        }]
    }