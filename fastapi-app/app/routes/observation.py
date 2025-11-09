"""
Observation API Routes - Endpoints FHIR R4 para gestión de observaciones

Implementa endpoints REST compatibles con FHIR R4 para operaciones CRUD
y búsqueda avanzada de recursos Observation (recurso distribuido).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models import (
    ObservationCreate,
    ObservationUpdate, 
    ObservationResponse,
    ObservationSearchParams
)
from app.services import observation_service
from app.services.base import ResourceNotFoundException, ValidationException

# Crear router con prefijo FHIR estándar
router = APIRouter(
    prefix="/fhir/R4/Observation",
    tags=["Observation"],
    responses={
        404: {"description": "Observation not found"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"}
    }
)

@router.post("/", response_model=ObservationResponse, status_code=201)
async def create_observation(
    observation_data: ObservationCreate,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Crear una nueva observación FHIR R4
    
    - **observation_data**: Datos de la observación según especificación FHIR R4
    - **documento_id**: ID de documento para co-localización en Citus
    """
    try:
        observation = await observation_service.create(
            session=session, 
            observation_data=observation_data,
            documento_id=documento_id
        )
        return observation
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{observation_id}", response_model=ObservationResponse)
async def get_observation(
    observation_id: str = Path(..., description="Observation ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener observación por ID
    
    - **observation_id**: ID único de la observación
    - **documento_id**: ID de documento para co-localización
    """
    try:
        observation = await observation_service.get_by_id(
            session=session,
            resource_id=observation_id,
            documento_id=documento_id
        )
        
        if not observation:
            raise HTTPException(status_code=404, detail="Observation not found")
        
        return observation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{observation_id}", response_model=ObservationResponse)
async def update_observation(
    observation_id: str = Path(..., description="Observation ID"),
    observation_data: ObservationUpdate = ...,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Actualizar observación existente
    
    - **observation_id**: ID único de la observación
    - **observation_data**: Datos de actualización de la observación  
    - **documento_id**: ID de documento para co-localización
    """
    try:
        observation = await observation_service.update(
            session=session,
            resource_id=observation_id,
            observation_data=observation_data,
            documento_id=documento_id
        )
        return observation
        
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Observation not found")
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{observation_id}", status_code=204)
async def delete_observation(
    observation_id: str = Path(..., description="Observation ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Eliminar observación
    
    - **observation_id**: ID único de la observación
    - **documento_id**: ID de documento para co-localización
    """
    try:
        success = await observation_service.delete(
            session=session,
            resource_id=observation_id,
            documento_id=documento_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Observation not found")
            
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Observation not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=dict)
async def search_observations(
    # Parámetros de búsqueda FHIR estándar
    patient: Optional[str] = Query(None, description="Patient ID"),
    code: Optional[str] = Query(None, description="LOINC code"),
    category: Optional[str] = Query(None, description="Observation category"),
    status: Optional[str] = Query(None, description="Observation status"),
    date: Optional[str] = Query(None, description="Observation date (YYYY-MM-DD)"),
    value_quantity: Optional[str] = Query(None, alias="value-quantity", description="Numeric value"),
    value_string: Optional[str] = Query(None, alias="value-string", description="Text value"),
    
    # Parámetros de paginación
    _count: int = Query(20, alias="_count", ge=1, le=100, description="Number of results per page"),
    _page: int = Query(1, alias="_page", ge=1, description="Page number"),
    
    # Parámetros de ordenamiento
    _sort: Optional[str] = Query(None, alias="_sort", description="Sort field (date, code, status)"),
    _order: str = Query("desc", alias="_order", regex="^(asc|desc)$", description="Sort order"),
    
    # Filtro opcional por documento
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    
    session: AsyncSession = Depends(get_db_session)
):
    """
    Buscar observaciones con parámetros FHIR R4
    
    Soporta búsqueda por múltiples criterios con paginación y ordenamiento.
    Compatible con especificación FHIR R4 search parameters.
    """
    try:
        # Construir parámetros de búsqueda
        search_params = ObservationSearchParams(
            patient=patient,
            code=code,
            category=category,
            status=status,
            date=date,
            value_quantity=value_quantity,
            value_string=value_string,
            page=_page,
            size=_count,
            sort=_sort,
            order=_order
        )
        
        # Ejecutar búsqueda
        result = await observation_service.search(
            session=session,
            search_params=search_params,
            documento_id=documento_id
        )
        
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}", response_model=List[ObservationResponse])
async def get_observations_by_patient(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener todas las observaciones de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        observations = await observation_service.get_by_patient(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return observations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/category/{category_value}", response_model=List[ObservationResponse])
async def get_observations_by_category(
    category_value: str = Path(..., description="Observation category"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener observaciones por categoría
    
    - **category_value**: Categoría de observación (vital-signs, laboratory, etc.)
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        observations = await observation_service.get_by_category(
            session=session,
            categoria=category_value,
            documento_id=documento_id
        )
        
        return observations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/vital-signs/patient/{patient_id}", response_model=List[ObservationResponse])
async def get_vital_signs(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener signos vitales de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        vital_signs = await observation_service.get_vital_signs(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return vital_signs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/laboratory/patient/{patient_id}", response_model=List[ObservationResponse])
async def get_laboratory_results(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener resultados de laboratorio de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        lab_results = await observation_service.get_laboratory_results(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return lab_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Endpoint de metadatos FHIR (CapabilityStatement)
@router.get("/$metadata", response_model=dict)
async def observation_capability_statement():
    """
    FHIR CapabilityStatement para recurso Observation
    """
    return {
        "resourceType": "CapabilityStatement",
        "id": "observation-capability",
        "url": "http://example.com/fhir/CapabilityStatement/observation",
        "version": "1.0.0",
        "name": "ObservationCapabilityStatement", 
        "title": "Observation Resource Capability Statement",
        "status": "active",
        "date": "2025-11-08",
        "publisher": "Healthcare System",
        "description": "FHIR R4 Observation resource capabilities",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Observation",
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
                    {"name": "status", "type": "token"},
                    {"name": "date", "type": "date"},
                    {"name": "value-quantity", "type": "quantity"},
                    {"name": "value-string", "type": "string"}
                ]
            }]
        }]
    }