"""
DiagnosticReport API Routes - Endpoints FHIR R4 para gestión de reportes diagnósticos

Implementa endpoints REST compatibles con FHIR R4 para operaciones CRUD
y búsqueda avanzada de recursos DiagnosticReport (recurso distribuido).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models import (
    DiagnosticReportCreate,
    DiagnosticReportUpdate, 
    DiagnosticReportResponse,
    DiagnosticReportSearchParams
)
from app.services import diagnostic_report_service
from app.services.base import ResourceNotFoundException, ValidationException

# Crear router con prefijo FHIR estándar
router = APIRouter(
    prefix="/fhir/R4/DiagnosticReport",
    tags=["DiagnosticReport"],
    responses={
        404: {"description": "DiagnosticReport not found"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"}
    }
)

@router.post("/", response_model=DiagnosticReportResponse, status_code=201)
async def create_diagnostic_report(
    diagnostic_report_data: DiagnosticReportCreate,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Crear un nuevo reporte diagnóstico FHIR R4
    
    - **diagnostic_report_data**: Datos del reporte según especificación FHIR R4
    - **documento_id**: ID de documento para co-localización en Citus
    """
    try:
        diagnostic_report = await diagnostic_report_service.create(
            session=session, 
            diagnostic_report_data=diagnostic_report_data,
            documento_id=documento_id
        )
        return diagnostic_report
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{diagnostic_report_id}", response_model=DiagnosticReportResponse)
async def get_diagnostic_report(
    diagnostic_report_id: str = Path(..., description="DiagnosticReport ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener reporte diagnóstico por ID
    
    - **diagnostic_report_id**: ID único del reporte
    - **documento_id**: ID de documento para co-localización
    """
    try:
        diagnostic_report = await diagnostic_report_service.get_by_id(
            session=session,
            resource_id=diagnostic_report_id,
            documento_id=documento_id
        )
        
        if not diagnostic_report:
            raise HTTPException(status_code=404, detail="DiagnosticReport not found")
        
        return diagnostic_report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.put("/{diagnostic_report_id}", response_model=DiagnosticReportResponse)
async def update_diagnostic_report(
    diagnostic_report_id: str = Path(..., description="DiagnosticReport ID"),
    diagnostic_report_data: DiagnosticReportUpdate = ...,
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Actualizar reporte diagnóstico existente
    
    - **diagnostic_report_id**: ID único del reporte
    - **diagnostic_report_data**: Datos de actualización del reporte
    - **documento_id**: ID de documento para co-localización
    """
    try:
        diagnostic_report = await diagnostic_report_service.update(
            session=session,
            resource_id=diagnostic_report_id,
            diagnostic_report_data=diagnostic_report_data,
            documento_id=documento_id
        )
        return diagnostic_report
        
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="DiagnosticReport not found")
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{diagnostic_report_id}", status_code=204)
async def delete_diagnostic_report(
    diagnostic_report_id: str = Path(..., description="DiagnosticReport ID"),
    documento_id: int = Query(..., description="Document ID for co-location"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Eliminar reporte diagnóstico
    
    - **diagnostic_report_id**: ID único del reporte
    - **documento_id**: ID de documento para co-localización
    """
    try:
        success = await diagnostic_report_service.delete(
            session=session,
            resource_id=diagnostic_report_id,
            documento_id=documento_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="DiagnosticReport not found")
            
    except ResourceNotFoundException:
        raise HTTPException(status_code=404, detail="DiagnosticReport not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=dict)
async def search_diagnostic_reports(
    # Parámetros de búsqueda FHIR estándar
    patient: Optional[str] = Query(None, description="Patient ID"),
    code: Optional[str] = Query(None, description="Study LOINC code"),
    category: Optional[str] = Query(None, description="Report category"),
    status: Optional[str] = Query(None, description="Report status"),
    performer: Optional[str] = Query(None, description="Practitioner ID"),
    date: Optional[str] = Query(None, description="Study date (YYYY-MM-DD)"),
    issued: Optional[str] = Query(None, description="Report issued date (YYYY-MM-DD)"),
    
    # Parámetros de paginación
    _count: int = Query(20, alias="_count", ge=1, le=100, description="Number of results per page"),
    _page: int = Query(1, alias="_page", ge=1, description="Page number"),
    
    # Parámetros de ordenamiento
    _sort: Optional[str] = Query(None, alias="_sort", description="Sort field (date, issued, status)"),
    _order: str = Query("desc", alias="_order", regex="^(asc|desc)$", description="Sort order"),
    
    # Filtro opcional por documento
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    
    session: AsyncSession = Depends(get_db_session)
):
    """
    Buscar reportes diagnósticos con parámetros FHIR R4
    
    Soporta búsqueda por múltiples criterios con paginación y ordenamiento.
    Compatible con especificación FHIR R4 search parameters.
    """
    try:
        # Construir parámetros de búsqueda
        search_params = DiagnosticReportSearchParams(
            patient=patient,
            code=code,
            category=category,
            status=status,
            performer=performer,
            date=date,
            issued=issued,
            page=_page,
            size=_count,
            sort=_sort,
            order=_order
        )
        
        # Ejecutar búsqueda
        result = await diagnostic_report_service.search(
            session=session,
            search_params=search_params,
            documento_id=documento_id
        )
        
        return result
        
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}", response_model=List[DiagnosticReportResponse])
async def get_diagnostic_reports_by_patient(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener todos los reportes diagnósticos de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        diagnostic_reports = await diagnostic_report_service.get_by_patient(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return diagnostic_reports
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}/laboratory", response_model=List[DiagnosticReportResponse])
async def get_laboratory_reports(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener reportes de laboratorio de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        lab_reports = await diagnostic_report_service.get_laboratory_reports(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return lab_reports
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/patient/{patient_id}/imaging", response_model=List[DiagnosticReportResponse])
async def get_imaging_reports(
    patient_id: int = Path(..., description="Patient ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener reportes de imagenología de un paciente
    
    - **patient_id**: ID del paciente
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        imaging_reports = await diagnostic_report_service.get_imaging_reports(
            session=session,
            paciente_id=patient_id,
            documento_id=documento_id
        )
        
        return imaging_reports
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/category/{category_value}", response_model=List[DiagnosticReportResponse])
async def get_diagnostic_reports_by_category(
    category_value: str = Path(..., description="Report category"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener reportes diagnósticos por categoría
    
    - **category_value**: Categoría del reporte (LAB, RAD, etc.)
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        diagnostic_reports = await diagnostic_report_service.get_by_category(
            session=session,
            categoria=category_value,
            documento_id=documento_id
        )
        
        return diagnostic_reports
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/practitioner/{practitioner_id}", response_model=List[DiagnosticReportResponse])
async def get_diagnostic_reports_by_practitioner(
    practitioner_id: int = Path(..., description="Practitioner ID"),
    documento_id: Optional[int] = Query(None, description="Document ID filter"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Obtener reportes diagnósticos por profesional ejecutor
    
    - **practitioner_id**: ID del profesional
    - **documento_id**: ID de documento opcional para filtrar
    """
    try:
        diagnostic_reports = await diagnostic_report_service.get_by_professional(
            session=session,
            profesional_id=practitioner_id,
            documento_id=documento_id
        )
        
        return diagnostic_reports
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Endpoint de metadatos FHIR (CapabilityStatement)
@router.get("/$metadata", response_model=dict)
async def diagnostic_report_capability_statement():
    """
    FHIR CapabilityStatement para recurso DiagnosticReport
    """
    return {
        "resourceType": "CapabilityStatement",
        "id": "diagnostic-report-capability",
        "url": "http://example.com/fhir/CapabilityStatement/diagnostic-report",
        "version": "1.0.0",
        "name": "DiagnosticReportCapabilityStatement", 
        "title": "DiagnosticReport Resource Capability Statement",
        "status": "active",
        "date": "2025-11-08",
        "publisher": "Healthcare System",
        "description": "FHIR R4 DiagnosticReport resource capabilities",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [{
                "type": "DiagnosticReport",
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
                    {"name": "performer", "type": "reference"},
                    {"name": "date", "type": "date"},
                    {"name": "issued", "type": "date"}
                ]
            }]
        }]
    }