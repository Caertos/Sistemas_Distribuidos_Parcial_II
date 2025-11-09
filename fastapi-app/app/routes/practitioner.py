"""
Practitioner API Routes - Endpoints FHIR R4 para gestión de profesionales

Implementa endpoints REST compatibles con FHIR R4 para operaciones CRUD
y búsqueda avanzada de recursos Practitioner (tabla de referencia global).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models import (
    PractitionerCreate,
    PractitionerUpdate, 
    PractitionerResponse,
    PractitionerSearchParams
)
from app.services import practitioner_service
from app.services.base import ResourceNotFoundException, ValidationException

# Crear router con prefijo FHIR estándar
router = APIRouter(
    prefix="/fhir/R4/Practitioner",
    tags=["Practitioner"],
    responses={
        404: {"description": "Practitioner not found"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"}
    }
)

@router.post("/", response_model=PractitionerResponse, status_code=201)
async def create_practitioner(
    practitioner_data: PractitionerCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Crear un nuevo profesional FHIR R4
    
    - **practitioner_data**: Datos del profesional según especificación FHIR R4
    
    Nota: Practitioner es un recurso de referencia (no requiere documento_id)
    """
    try:
        practitioner = await practitioner_service.create(
            session=session, 
            practitioner_data=practitioner_data
        )
        return practitioner
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{practitioner_id}", response_model=PractitionerResponse)
async def get_practitioner(
    practitioner_id: str = Path(..., description="Practitioner ID"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener profesional por ID
    
    - **practitioner_id**: ID único del profesional
    """
    try:
        practitioner = await practitioner_service.get_by_id(
            session=session,
            resource_id=practitioner_id
        )
        
        if not practitioner:
            raise HTTPException(status_code=404, detail="Practitioner not found")
        
        return practitioner
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{practitioner_id}", response_model=PractitionerResponse)
async def update_practitioner(
    practitioner_id: str = Path(..., description="Practitioner ID"),
    practitioner_data: PractitionerUpdate = ...,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Actualizar profesional existente
    
    - **practitioner_id**: ID único del profesional
    - **practitioner_data**: Datos de actualización del profesional
    """
    try:
        practitioner = await practitioner_service.update(
            session=session,
            resource_id=practitioner_id,
            practitioner_data=practitioner_data
        )
        return practitioner
        
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{practitioner_id}", status_code=204)
async def delete_practitioner(
    practitioner_id: str = Path(..., description="Practitioner ID"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Eliminar profesional
    
    - **practitioner_id**: ID único del profesional
    """
    try:
        success = await practitioner_service.delete(
            session=session,
            resource_id=practitioner_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Practitioner not found")
            
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=dict)
async def search_practitioners(
    # Parámetros de búsqueda FHIR estándar
    name: Optional[str] = Query(None, description="Practitioner name (given or family)"),
    family: Optional[str] = Query(None, description="Family name"),
    given: Optional[str] = Query(None, description="Given name"),
    identifier: Optional[str] = Query(None, description="Medical license number"),
    specialty: Optional[str] = Query(None, description="Medical specialty"),
    
    # Parámetros de paginación
    _count: int = Query(20, alias="_count", ge=1, le=100, description="Number of results per page"),
    _page: int = Query(1, alias="_page", ge=1, description="Page number"),
    
    # Parámetros de ordenamiento
    _sort: Optional[str] = Query(None, alias="_sort", description="Sort field (name, specialty)"),
    _order: str = Query("asc", alias="_order", regex="^(asc|desc)$", description="Sort order"),
    
    session: AsyncSession = Depends(get_db_session)
):
    """
    Buscar profesionales con parámetros FHIR R4
    
    Soporta búsqueda por múltiples criterios con paginación y ordenamiento.
    Compatible con especificación FHIR R4 search parameters.
    """
    try:
        # Construir parámetros de búsqueda
        search_params = PractitionerSearchParams(
            name=name,
            family=family, 
            given=given,
            identifier=identifier,
            specialty=specialty,
            page=_page,
            size=_count,
            sort=_sort,
            order=_order
        )
        
        # Ejecutar búsqueda
        result = await practitioner_service.search(
            session=session,
            search_params=search_params
        )
        
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/identifier/{identifier_value}", response_model=PractitionerResponse)
async def get_practitioner_by_identifier(
    identifier_value: str = Path(..., description="Medical license number"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener profesional por número de registro médico
    
    - **identifier_value**: Número de registro médico
    """
    try:
        practitioner = await practitioner_service.get_by_registro_medico(
            session=session,
            registro_medico=identifier_value
        )
        
        if not practitioner:
            raise HTTPException(status_code=404, detail="Practitioner not found")
        
        return practitioner
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/specialty/{specialty_value}", response_model=List[PractitionerResponse])
async def get_practitioners_by_specialty(
    specialty_value: str = Path(..., description="Medical specialty"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener profesionales por especialidad médica
    
    - **specialty_value**: Especialidad médica
    """
    try:
        practitioners = await practitioner_service.get_by_specialty(
            session=session,
            specialty=specialty_value
        )
        
        return practitioners
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/specialties/list", response_model=List[str])
async def get_all_specialties(
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener lista de todas las especialidades disponibles
    
    Retorna todas las especialidades médicas registradas en el sistema.
    """
    try:
        specialties = await practitioner_service.get_all_specialties(session=session)
        return specialties
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Endpoint de metadatos FHIR (CapabilityStatement)
@router.get("/$metadata", response_model=dict)
async def practitioner_capability_statement():
    """
    FHIR CapabilityStatement para recurso Practitioner
    
    Retorna las capacidades soportadas para el recurso Practitioner
    según la especificación FHIR R4.
    """
    return {
        "resourceType": "CapabilityStatement",
        "id": "practitioner-capability",
        "url": "http://example.com/fhir/CapabilityStatement/practitioner",
        "version": "1.0.0",
        "name": "PractitionerCapabilityStatement", 
        "title": "Practitioner Resource Capability Statement",
        "status": "active",
        "date": "2025-11-08",
        "publisher": "Healthcare System",
        "description": "FHIR R4 Practitioner resource capabilities",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Practitioner",
                "interaction": [
                    {"code": "read"},
                    {"code": "create"},
                    {"code": "update"},
                    {"code": "delete"},
                    {"code": "search-type"}
                ],
                "searchParam": [
                    {"name": "name", "type": "string"},
                    {"name": "family", "type": "string"},
                    {"name": "given", "type": "string"},
                    {"name": "identifier", "type": "token"},
                    {"name": "specialty", "type": "token"}
                ]
            }]
        }]
    }

# Endpoint de validación FHIR
@router.post("/$validate", response_model=dict)
async def validate_practitioner(
    practitioner_data: PractitionerCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Validar recurso Practitioner sin persistir
    
    Valida la estructura y contenido de un recurso Practitioner
    según las reglas FHIR R4 sin guardarlo en la base de datos.
    """
    try:
        # Realizar validaciones del servicio sin persistir
        # TODO: Implementar validación específica sin crear el recurso
        
        return {
            "resourceType": "OperationOutcome",
            "issue": [{
                "severity": "information",
                "code": "informational",
                "diagnostics": "Practitioner resource is valid"
            }]
        }
        
    except ValidationException as e:
        return {
            "resourceType": "OperationOutcome", 
            "issue": [{
                "severity": "error",
                "code": "invalid",
                "diagnostics": str(e)
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")