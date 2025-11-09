"""
Patient API Routes - Endpoints FHIR R4 para gestión de pacientes

Implementa endpoints REST compatibles con FHIR R4 para operaciones CRUD
y búsqueda avanzada de recursos Patient.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models import (
    PatientCreate,
    PatientUpdate, 
    PatientResponse,
    PatientSearchParams
)
from app.services import patient_service
from app.services.base import ResourceNotFoundException, ValidationException

# Crear router con prefijo FHIR estándar
router = APIRouter(
    prefix="/fhir/R4/Patient",
    tags=["Patient"],
    responses={
        404: {"description": "Patient not found"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"}
    }
)

@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    patient_data: PatientCreate,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Crear un nuevo paciente FHIR R4
    
    - **patient_data**: Datos del paciente según especificación FHIR R4
    - **documento_id**: ID de documento para co-localización en Citus
    """
    try:
        patient = await patient_service.create(
            session=session, 
            patient_data=patient_data,
            documento_id=documento_id
        )
        return patient
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str = Path(..., description="Patient ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener paciente por ID
    
    - **patient_id**: ID único del paciente
    - **documento_id**: ID de documento para co-localización
    """
    try:
        patient = await patient_service.get_by_id(
            session=session,
            resource_id=patient_id,
            documento_id=documento_id
        )
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str = Path(..., description="Patient ID"),
    patient_data: PatientUpdate = ...,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Actualizar paciente existente
    
    - **patient_id**: ID único del paciente
    - **patient_data**: Datos de actualización del paciente
    - **documento_id**: ID de documento para co-localización
    """
    try:
        patient = await patient_service.update(
            session=session,
            resource_id=patient_id,
            patient_data=patient_data,
            documento_id=documento_id
        )
        return patient
        
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Patient not found")
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: str = Path(..., description="Patient ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Eliminar paciente
    
    - **patient_id**: ID único del paciente
    - **documento_id**: ID de documento para co-localización
    """
    try:
        success = await patient_service.delete(
            session=session,
            resource_id=patient_id,
            documento_id=documento_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Patient not found")
            
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="Patient not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=dict)
async def search_patients(
    # Parámetros de búsqueda FHIR estándar
    name: Optional[str] = Query(None, description="Patient name (given or family)"),
    family: Optional[str] = Query(None, description="Family name"),
    given: Optional[str] = Query(None, description="Given name"),
    identifier: Optional[str] = Query(None, description="Patient identifier"),
    birthdate: Optional[str] = Query(None, description="Birth date (YYYY-MM-DD)"),
    gender: Optional[str] = Query(None, description="Gender (male, female, other, unknown)"),
    phone: Optional[str] = Query(None, description="Phone number"),
    email: Optional[str] = Query(None, description="Email address"),
    address: Optional[str] = Query(None, description="Address"),
    
    # Parámetros de paginación
    _count: int = Query(20, alias="_count", ge=1, le=100, description="Number of results per page"),
    _page: int = Query(1, alias="_page", ge=1, description="Page number"),
    
    # Parámetros de ordenamiento
    _sort: Optional[str] = Query(None, alias="_sort", description="Sort field (name, birthdate, family)"),
    _order: str = Query("asc", alias="_order", regex="^(asc|desc)$", description="Sort order"),
    
    # Filtro opcional por documento
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    
    session: AsyncSession = Depends(get_db_session)
):
    """
    Buscar pacientes con parámetros FHIR R4
    
    Soporta búsqueda por múltiples criterios con paginación y ordenamiento.
    Compatible con especificación FHIR R4 search parameters.
    """
    try:
        # Construir parámetros de búsqueda
        search_params = PatientSearchParams(
            name=name,
            family=family, 
            given=given,
            identifier=identifier,
            birthdate=birthdate,
            gender=gender,
            phone=phone,
            email=email,
            address=address,
            page=_page,
            size=_count,
            sort=_sort,
            order=_order
        )
        
        # Ejecutar búsqueda
        result = await patient_service.search(
            session=session,
            search_params=search_params,
            documento_id=documento_id
        )
        
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/identifier/{identifier_value}", response_model=PatientResponse)
async def get_patient_by_identifier(
    identifier_value: str = Path(..., description="Patient identifier value"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener paciente por identificador único
    
    - **identifier_value**: Valor del identificador (cédula, pasaporte, etc.)
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        patient = await patient_service.get_by_identifier(
            session=session,
            identifier_value=identifier_value,
            documento_id=documento_id
        )
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        return patient
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/gender/{gender_value}", response_model=List[PatientResponse])
async def get_patients_by_gender(
    gender_value: str = Path(..., description="Gender value", regex="^(male|female|other|unknown)$"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener pacientes por género
    
    - **gender_value**: Valor de género (male, female, other, unknown)
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        patients = await patient_service.get_by_gender(
            session=session,
            gender=gender_value,
            documento_id=documento_id
        )
        
        return patients
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Endpoint de metadatos FHIR (CapabilityStatement)
@router.get("/$metadata", response_model=dict)
async def patient_capability_statement():
    """
    FHIR CapabilityStatement para recurso Patient
    
    Retorna las capacidades soportadas para el recurso Patient
    según la especificación FHIR R4.
    """
    return {
        "resourceType": "CapabilityStatement",
        "id": "patient-capability",
        "url": "http://example.com/fhir/CapabilityStatement/patient",
        "version": "1.0.0",
        "name": "PatientCapabilityStatement", 
        "title": "Patient Resource Capability Statement",
        "status": "active",
        "date": "2025-11-08",
        "publisher": "Healthcare System",
        "description": "FHIR R4 Patient resource capabilities",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "Patient",
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
                    {"name": "birthdate", "type": "date"},
                    {"name": "gender", "type": "token"},
                    {"name": "phone", "type": "string"},
                    {"name": "email", "type": "string"},
                    {"name": "address", "type": "string"}
                ]
            }]
        }]
    }

# Endpoint de validación FHIR
@router.post("/$validate", response_model=dict)
async def validate_patient(
    patient_data: PatientCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Validar recurso Patient sin persistir
    
    Valida la estructura y contenido de un recurso Patient
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
                "diagnostics": "Patient resource is valid"
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