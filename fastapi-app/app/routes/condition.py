"""
Condition API Routes - Endpoints FHIR R4 para gestión de condiciones

Implementa endpoints REST compatibles con FHIR R4 para operaciones CRUD
y búsqueda avanzada de recursos Condition (recurso distribuido).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models import (
    ConditionCreate,
    ConditionUpdate, 
    ConditionResponse,
    ConditionSearchParams
)
from app.services import condition_service
from app.services.base import ResourceNotFoundException, ValidationException

# Crear router con prefijo FHIR estándar
router = APIRouter(
    prefix="/fhir/R4/Condition",
    tags=["Condition"],
    responses={
        404: {"description": "Condition not found"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"}
    }
)

@router.post("/", response_model=ConditionResponse, status_code=201)
async def create_condition(
    condition_data: ConditionCreate,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Crear una nueva condición FHIR R4
    
    - **condition_data**: Datos de la condición según especificación FHIR R4
    - **documento_id**: ID de documento para co-localización en Citus
    """
    try:
        condition = await condition_service.create(
            session=session, 
            condition_data=condition_data,
            documento_id=documento_id
        )
        return condition
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{condition_id}", response_model=ConditionResponse)
async def get_condition(
    condition_id: str = Path(..., description="Condition ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener condición por ID
    
    - **condition_id**: ID único de la condición
    - **documento_id**: ID de documento para co-localización
    """
    try:
        condition = await condition_service.get_by_id(
            session=session,
            resource_id=condition_id,
            documento_id=documento_id
        )
        
        if not condition:
            raise HTTPException(status_code=404, detail="Condition not found")
        
        return condition
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{condition_id}", response_model=ConditionResponse)
async def update_condition(
    condition_id: str = Path(..., description="Condition ID"),
    condition_data: ConditionUpdate = ...,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Actualizar condición existente
    
    - **condition_id**: ID único de la condición
    - **condition_data**: Datos de actualización de la condición
    - **documento_id**: ID de documento para co-localización
    """
    try:
        condition = await condition_service.update(
            session=session,
            resource_id=condition_id,
            condition_data=condition_data,
            documento_id=documento_id
        )
        return condition
        
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Condition not found")
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{condition_id}", status_code=204)
async def delete_condition(
    condition_id: str = Path(..., description="Condition ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Eliminar condición
    
    - **condition_id**: ID único de la condición
    - **documento_id**: ID de documento para co-localización
    """
    try:
        success = await condition_service.delete(
            session=session,
            resource_id=condition_id,
            documento_id=documento_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Condition not found")
            
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Condition not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=dict)
async def search_conditions(
    # Parámetros de búsqueda FHIR estándar
    patient: Optional[str] = Query(None, description="Patient ID"),
    code: Optional[str] = Query(None, description="SNOMED-CT code"),
    category: Optional[str] = Query(None, description="Condition category"),
    clinical_status: Optional[str] = Query(None, alias="clinical-status", description="Clinical status"),
    verification_status: Optional[str] = Query(None, alias="verification-status", description="Verification status"),
    severity: Optional[str] = Query(None, description="Condition severity"),
    onset_date: Optional[str] = Query(None, alias="onset-date", description="Onset date (YYYY-MM-DD)"),
    recorded_date: Optional[str] = Query(None, alias="recorded-date", description="Recorded date (YYYY-MM-DD)"),
    
    # Parámetros de paginación
    _count: int = Query(20, alias="_count", ge=1, le=100, description="Number of results per page"),
    _page: int = Query(1, alias="_page", ge=1, description="Page number"),
    
    # Parámetros de ordenamiento
    _sort: Optional[str] = Query(None, alias="_sort", description="Sort field (onset-date, recorded-date, clinical-status)"),
    _order: str = Query("desc", alias="_order", regex="^(asc|desc)$", description="Sort order"),
    
    # Filtro opcional por documento
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    
    session: AsyncSession = Depends(get_db_session)
):
    """
    Buscar condiciones con parámetros FHIR R4
    
    Soporta búsqueda por múltiples criterios con paginación y ordenamiento.
    Compatible con especificación FHIR R4 search parameters.
    """
    try:
        # Construir parámetros de búsqueda
        search_params = ConditionSearchParams(
            patient=patient,
            code=code,
            category=category,
            clinical_status=clinical_status,
            verification_status=verification_status,
            severity=severity,
            onset_date=onset_date,
            recorded_date=recorded_date,
            page=_page,
            size=_count,
            sort=_sort,
            order=_order
        )
        
        # Ejecutar búsqueda
        result = await condition_service.search(
            session=session,
            search_params=search_params,
            documento_id=documento_id
        )
        
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}", response_model=List[ConditionResponse])
async def get_conditions_by_patient(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener todas las condiciones de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        conditions = await condition_service.get_by_patient(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return conditions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}/active", response_model=List[ConditionResponse])
async def get_active_conditions(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener condiciones activas de un paciente
    
    - **patient_id**: ID del paciente  
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        conditions = await condition_service.get_active_conditions(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return conditions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}/chronic", response_model=List[ConditionResponse])
async def get_chronic_conditions(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener condiciones crónicas de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        conditions = await condition_service.get_chronic_conditions(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return conditions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/category/{category_value}", response_model=List[ConditionResponse])
async def get_conditions_by_category(
    category_value: str = Path(..., description="Condition category"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener condiciones por categoría
    
    - **category_value**: Categoría de condición (problem-list-item, encounter-diagnosis, etc.)
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        conditions = await condition_service.get_by_category(
            session=session,
            categoria=category_value,
            documento_id=documento_id
        )
        
        return conditions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Endpoint de metadatos FHIR (CapabilityStatement)
@router.get("/$metadata", response_model=dict)
async def condition_capability_statement():
    """
    FHIR CapabilityStatement para recurso Condition
    """
    return {
        "resourceType": "CapabilityStatement",
        "id": "condition-capability",
        "url": "http://example.com/fhir/CapabilityStatement/condition",
        "version": "1.0.0",
        "name": "ConditionCapabilityStatement", 
        "title": "Condition Resource Capability Statement",
        "status": "active",
        "date": "2025-11-08",
        "publisher": "Healthcare System",
        "description": "FHIR R4 Condition resource capabilities",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Condition",
                "interaction": [
                    {"code": "read"},
                    {"code": "create"},
                    {"code": "update"},
                    {"code": "delete"},
                    {"code": "search-type"}
                ],
                "searchParam": [
                    {"name": "patient", "type": "reference"},
                    {"name": "code", "type": "token"},
                    {"name": "category", "type": "token"},
                    {"name": "clinical-status", "type": "token"},
                    {"name": "verification-status", "type": "token"},
                    {"name": "severity", "type": "token"},
                    {"name": "onset-date", "type": "date"},
                    {"name": "recorded-date", "type": "date"}
                ]
            }]
        }]
    }