"""
Admission API Routes - Endpoints para gestión de admisiones y triage

Implementa endpoints REST para operaciones de admisión de pacientes,
gestión de triage y coordinación entre citas y consultas médicas.
"""

from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from app.config.database import get_db_session
from app.services.admission_service import AdmissionService
from app.auth.middleware import require_roles
from app.logging.structured_logger import structured_logger

logger = structured_logger

# Crear router para admisiones
router = APIRouter(
    prefix="/api/admission",
    tags=["Admission"],
    responses={
        404: {"description": "Resource not found"},
        400: {"description": "Invalid request"},
        422: {"description": "Validation error"},
        403: {"description": "Insufficient permissions"}
    }
)

# ==================== Modelos Pydantic ====================

class AdmissionCreate(BaseModel):
    """Modelo para crear una nueva admisión"""
    cita_id: int = Field(..., description="ID de la cita a admitir")
    
    # Signos vitales
    presion_arterial_sistolica: int = Field(..., ge=60, le=250, description="Presión sistólica en mmHg")
    presion_arterial_diastolica: int = Field(..., ge=40, le=150, description="Presión diastólica en mmHg")
    frecuencia_cardiaca: int = Field(..., ge=30, le=220, description="Frecuencia cardíaca en bpm")
    frecuencia_respiratoria: int = Field(..., ge=8, le=50, description="Frecuencia respiratoria por minuto")
    temperatura: float = Field(..., ge=35.0, le=42.0, description="Temperatura corporal en °C")
    saturacion_oxigeno: int = Field(..., ge=70, le=100, description="Saturación de oxígeno en %")
    
    # Datos antropométricos
    peso: Optional[float] = Field(None, ge=0.5, le=300, description="Peso en kg")
    altura: Optional[float] = Field(None, ge=0.3, le=2.5, description="Altura en metros")
    
    # Evaluación clínica
    nivel_dolor: Optional[int] = Field(None, ge=0, le=10, description="Nivel de dolor (escala 0-10)")
    nivel_conciencia: str = Field(..., description="Nivel de conciencia (alerta/somnoliento/estuporoso/comatoso)")
    motivo_consulta: str = Field(..., min_length=10, max_length=500, description="Motivo de la consulta")
    
    # Historia clínica inmediata
    alergias: Optional[str] = Field(None, max_length=500, description="Alergias conocidas")
    medicamentos_actuales: Optional[str] = Field(None, max_length=500, description="Medicamentos que toma actualmente")
    
    # Evaluación de urgencia
    requiere_atencion_inmediata: bool = Field(False, description="Si requiere atención médica inmediata")
    observaciones_enfermeria: Optional[str] = Field(None, max_length=1000, description="Observaciones de enfermería")
    
    @validator('nivel_conciencia')
    def validar_nivel_conciencia(cls, v):
        niveles_validos = ['alerta', 'somnoliento', 'estuporoso', 'comatoso']
        if v.lower() not in niveles_validos:
            raise ValueError(f"Nivel de conciencia debe ser uno de: {', '.join(niveles_validos)}")
        return v.lower()
    
    @validator('presion_arterial_diastolica')
    def validar_presiones(cls, v, values):
        if 'presion_arterial_sistolica' in values:
            if v >= values['presion_arterial_sistolica']:
                raise ValueError("Presión diastólica debe ser menor que la sistólica")
        return v


class TriageUpdate(BaseModel):
    """Modelo para actualizar datos de triage"""
    presion_arterial_sistolica: Optional[int] = Field(None, ge=60, le=250)
    presion_arterial_diastolica: Optional[int] = Field(None, ge=40, le=150)
    frecuencia_cardiaca: Optional[int] = Field(None, ge=30, le=220)
    frecuencia_respiratoria: Optional[int] = Field(None, ge=8, le=50)
    temperatura: Optional[float] = Field(None, ge=35.0, le=42.0)
    saturacion_oxigeno: Optional[int] = Field(None, ge=70, le=100)
    peso: Optional[float] = Field(None, ge=0.5, le=300)
    altura: Optional[float] = Field(None, ge=0.3, le=2.5)
    nivel_dolor: Optional[int] = Field(None, ge=0, le=10)
    nivel_conciencia: Optional[str] = None
    alergias: Optional[str] = Field(None, max_length=500)
    medicamentos_actuales: Optional[str] = Field(None, max_length=500)
    requiere_atencion_inmediata: Optional[bool] = None
    observaciones_enfermeria: Optional[str] = Field(None, max_length=1000)


class AdmissionStateUpdate(BaseModel):
    """Modelo para cambiar el estado de una admisión"""
    nuevo_estado: str = Field(..., description="Nuevo estado (activa/atendida/cancelada)")
    motivo: Optional[str] = Field(None, max_length=500, description="Motivo del cambio de estado")
    
    @validator('nuevo_estado')
    def validar_estado(cls, v):
        estados_validos = ['activa', 'atendida', 'cancelada']
        if v.lower() not in estados_validos:
            raise ValueError(f"Estado debe ser uno de: {', '.join(estados_validos)}")
        return v.lower()


class AdmissionResponse(BaseModel):
    """Modelo de respuesta para admisiones"""
    admission_id: str
    codigo_admision: str
    cita_id: int
    paciente_documento_id: int
    paciente_nombre: Optional[str]
    fecha_admision: datetime
    estado: str
    presion_arterial_sistolica: int
    presion_arterial_diastolica: int
    pam: Optional[float]
    frecuencia_cardiaca: int
    frecuencia_respiratoria: int
    temperatura: float
    saturacion_oxigeno: int
    peso: Optional[float]
    altura: Optional[float]
    imc: Optional[float]
    nivel_dolor: Optional[int]
    nivel_conciencia: str
    motivo_consulta: str
    alergias: Optional[str]
    medicamentos_actuales: Optional[str]
    requiere_atencion_inmediata: bool
    observaciones_enfermeria: Optional[str]
    admitido_por: int
    
    class Config:
        from_attributes = True


class PendingAppointmentResponse(BaseModel):
    """Modelo de respuesta para citas pendientes de admisión"""
    cita_id: int
    documento_id: int
    paciente_nombre: str
    paciente_genero: Optional[str]
    paciente_fecha_nacimiento: Optional[date]
    fecha_cita: datetime
    tipo_cita: str
    motivo: Optional[str]
    prioridad: Optional[str]
    
    class Config:
        from_attributes = True


class AdmissionStatisticsResponse(BaseModel):
    """Modelo de respuesta para estadísticas de admisión"""
    total_admisiones: int
    admisiones_activas: int
    admisiones_atendidas: int
    admisiones_canceladas: int
    citas_pendientes: int
    admisiones_urgentes: int
    promedio_signos_vitales: dict


# ==================== Endpoints ====================

@router.get("/pending-appointments", response_model=List[PendingAppointmentResponse])
async def get_pending_appointments(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "admin"]))
):
    """
    Obtener lista de citas pendientes de admisión
    
    Retorna todas las citas que han sido creadas pero aún no han sido
    admitidas por el personal de enfermería.
    
    - **Requiere rol**: admission o admin
    """
    try:
        service = AdmissionService()
        citas_pendientes = await service.obtener_citas_pendientes(session)
        
        logger.info(
            "Citas pendientes consultadas",
            extra={
                "user_id": current_user.get("user_id"),
                "total_pendientes": len(citas_pendientes)
            }
        )
        
        return citas_pendientes
        
    except Exception as e:
        logger.error(f"Error al obtener citas pendientes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener citas pendientes: {str(e)}"
        )


@router.post("/", response_model=AdmissionResponse, status_code=201)
async def create_admission(
    admission_data: AdmissionCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "admin"]))
):
    """
    Crear nueva admisión con datos de triage
    
    Admite a un paciente que tiene una cita pendiente, registrando todos
    los signos vitales y datos de triage necesarios. Genera automáticamente
    un código de admisión único.
    
    - **Requiere rol**: admission o admin
    - **admission_data**: Datos completos de triage y admisión
    """
    try:
        service = AdmissionService()
        
        # Crear la admisión
        admission = await service.crear_admision(
            session=session,
            cita_id=admission_data.cita_id,
            admitido_por=current_user["user_id"],
            presion_arterial_sistolica=admission_data.presion_arterial_sistolica,
            presion_arterial_diastolica=admission_data.presion_arterial_diastolica,
            frecuencia_cardiaca=admission_data.frecuencia_cardiaca,
            frecuencia_respiratoria=admission_data.frecuencia_respiratoria,
            temperatura=admission_data.temperatura,
            saturacion_oxigeno=admission_data.saturacion_oxigeno,
            peso=admission_data.peso,
            altura=admission_data.altura,
            nivel_dolor=admission_data.nivel_dolor,
            nivel_conciencia=admission_data.nivel_conciencia,
            motivo_consulta=admission_data.motivo_consulta,
            alergias=admission_data.alergias,
            medicamentos_actuales=admission_data.medicamentos_actuales,
            requiere_atencion_inmediata=admission_data.requiere_atencion_inmediata,
            observaciones_enfermeria=admission_data.observaciones_enfermeria
        )
        
        logger.info(
            "Admisión creada exitosamente",
            extra={
                "admission_id": admission.admission_id,
                "codigo_admision": admission.codigo_admision,
                "cita_id": admission_data.cita_id,
                "admitido_por": current_user["user_id"],
                "requiere_atencion_inmediata": admission_data.requiere_atencion_inmediata
            }
        )
        
        return admission
        
    except ValueError as e:
        logger.warning(f"Validación fallida al crear admisión: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear admisión: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear admisión: {str(e)}"
        )


@router.get("/active", response_model=List[AdmissionResponse])
async def get_active_admissions(
    limit: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    offset: int = Query(0, ge=0, description="Número de resultados a saltar"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "practitioner", "admin"]))
):
    """
    Obtener lista de admisiones activas
    
    Retorna todas las admisiones que están actualmente activas,
    ordenadas por prioridad (urgentes primero) y fecha de admisión.
    
    - **Requiere rol**: admission, practitioner o admin
    - **limit**: Número máximo de resultados (default: 50, max: 100)
    - **offset**: Paginación (default: 0)
    """
    try:
        service = AdmissionService()
        admisiones = await service.obtener_admisiones_activas(
            session=session,
            limit=limit,
            offset=offset
        )
        
        logger.info(
            "Admisiones activas consultadas",
            extra={
                "user_id": current_user.get("user_id"),
                "total_activas": len(admisiones),
                "limit": limit,
                "offset": offset
            }
        )
        
        return admisiones
        
    except Exception as e:
        logger.error(f"Error al obtener admisiones activas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener admisiones activas: {str(e)}"
        )


@router.get("/{admission_id}", response_model=AdmissionResponse)
async def get_admission(
    admission_id: str = Path(..., description="ID de la admisión"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "practitioner", "admin"]))
):
    """
    Obtener detalles de una admisión específica
    
    - **Requiere rol**: admission, practitioner o admin
    - **admission_id**: Código único de la admisión (ej: ADM-20231115-0001)
    """
    try:
        service = AdmissionService()
        admission = await service.obtener_admision_por_id(
            session=session,
            admission_id=admission_id
        )
        
        if not admission:
            raise HTTPException(
                status_code=404,
                detail=f"Admisión {admission_id} no encontrada"
            )
        
        logger.info(
            "Admisión consultada",
            extra={
                "admission_id": admission_id,
                "user_id": current_user.get("user_id")
            }
        )
        
        return admission
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener admisión {admission_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener admisión: {str(e)}"
        )


@router.put("/{admission_id}/triage", response_model=AdmissionResponse)
async def update_triage_data(
    admission_id: str = Path(..., description="ID de la admisión"),
    triage_data: TriageUpdate = Body(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "practitioner", "admin"]))
):
    """
    Actualizar datos de triage de una admisión
    
    Permite actualizar los signos vitales y observaciones de una admisión existente.
    Útil para re-evaluaciones o correcciones.
    
    - **Requiere rol**: admission, practitioner o admin
    - **admission_id**: Código único de la admisión
    - **triage_data**: Datos de triage a actualizar (solo se actualizan los campos proporcionados)
    """
    try:
        service = AdmissionService()
        
        # Convertir a diccionario y filtrar valores None
        update_data = {k: v for k, v in triage_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No se proporcionaron datos para actualizar"
            )
        
        admission = await service.actualizar_triage(
            session=session,
            admission_id=admission_id,
            **update_data
        )
        
        if not admission:
            raise HTTPException(
                status_code=404,
                detail=f"Admisión {admission_id} no encontrada"
            )
        
        logger.info(
            "Triage actualizado",
            extra={
                "admission_id": admission_id,
                "updated_by": current_user["user_id"],
                "fields_updated": list(update_data.keys())
            }
        )
        
        return admission
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validación fallida al actualizar triage: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al actualizar triage de {admission_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar triage: {str(e)}"
        )


@router.put("/{admission_id}/state", response_model=AdmissionResponse)
async def update_admission_state(
    admission_id: str = Path(..., description="ID de la admisión"),
    state_update: AdmissionStateUpdate = Body(...),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "practitioner", "admin"]))
):
    """
    Cambiar el estado de una admisión
    
    Permite cambiar el estado de una admisión (activa → atendida/cancelada).
    Solo el personal de admisión o médicos pueden cambiar estados.
    
    - **Requiere rol**: admission, practitioner o admin
    - **admission_id**: Código único de la admisión
    - **state_update**: Nuevo estado y motivo opcional
    """
    try:
        service = AdmissionService()
        
        admission = await service.cambiar_estado_admision(
            session=session,
            admission_id=admission_id,
            nuevo_estado=state_update.nuevo_estado,
            motivo=state_update.motivo
        )
        
        if not admission:
            raise HTTPException(
                status_code=404,
                detail=f"Admisión {admission_id} no encontrada"
            )
        
        logger.info(
            "Estado de admisión actualizado",
            extra={
                "admission_id": admission_id,
                "nuevo_estado": state_update.nuevo_estado,
                "updated_by": current_user["user_id"],
                "motivo": state_update.motivo
            }
        )
        
        return admission
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validación fallida al cambiar estado: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al cambiar estado de {admission_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al cambiar estado: {str(e)}"
        )


@router.get("/statistics/dashboard", response_model=AdmissionStatisticsResponse)
async def get_admission_statistics(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio para filtrar estadísticas"),
    fecha_fin: Optional[date] = Query(None, description="Fecha de fin para filtrar estadísticas"),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "admin"]))
):
    """
    Obtener estadísticas de admisiones para el dashboard
    
    Retorna estadísticas agregadas de admisiones, útiles para el panel
    de control de enfermería.
    
    - **Requiere rol**: admission o admin
    - **fecha_inicio**: Filtrar desde esta fecha (opcional)
    - **fecha_fin**: Filtrar hasta esta fecha (opcional)
    """
    try:
        service = AdmissionService()
        
        estadisticas = await service.obtener_estadisticas_admision(
            session=session,
            fecha_desde=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        logger.info(
            "Estadísticas de admisión consultadas",
            extra={
                "user_id": current_user.get("user_id"),
                "fecha_inicio": str(fecha_inicio) if fecha_inicio else None,
                "fecha_fin": str(fecha_fin) if fecha_fin else None
            }
        )
        
        return estadisticas
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


@router.get("/search/by-patient/{documento_id}", response_model=List[AdmissionResponse])
async def search_admissions_by_patient(
    documento_id: int = Path(..., description="Documento del paciente"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (activa/atendida/cancelada)"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_roles(["admission", "practitioner", "admin"]))
):
    """
    Buscar admisiones de un paciente específico
    
    Retorna el historial de admisiones de un paciente.
    
    - **Requiere rol**: admission, practitioner o admin
    - **documento_id**: Documento de identidad del paciente
    - **estado**: Filtrar por estado (opcional)
    - **limit**: Número máximo de resultados
    """
    try:
        service = AdmissionService()
        
        admisiones = await service.buscar_admisiones_por_paciente(
            session=session,
            documento_id=documento_id,
            estado=estado,
            limit=limit
        )
        
        logger.info(
            "Admisiones de paciente consultadas",
            extra={
                "user_id": current_user.get("user_id"),
                "documento_id": documento_id,
                "estado": estado,
                "total_encontradas": len(admisiones)
            }
        )
        
        return admisiones
        
    except Exception as e:
        logger.error(f"Error al buscar admisiones del paciente {documento_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al buscar admisiones: {str(e)}"
        )
