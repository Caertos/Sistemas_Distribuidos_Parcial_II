from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import validator


PRIORITY_VALUES = {"urgente", "normal", "baja"}
CONSCIOUSNESS_VALUES = {"alerta", "somnoliento", "confuso", "inconsciente"}


class AdmissionCreate(BaseModel):
    paciente_id: int
    cita_id: Optional[int] = None
    motivo_consulta: Optional[str] = None
    prioridad: Optional[str] = "normal"
    # Signos vitales iniciales (opcionales)
    presion_arterial_sistolica: Optional[int] = None
    presion_arterial_diastolica: Optional[int] = None
    frecuencia_cardiaca: Optional[int] = None
    frecuencia_respiratoria: Optional[int] = None
    temperatura: Optional[float] = None
    saturacion_oxigeno: Optional[int] = None
    peso: Optional[float] = None
    altura: Optional[int] = None
    nivel_dolor: Optional[int] = None
    nivel_conciencia: Optional[str] = None
    sintomas_principales: Optional[str] = None
    notas_enfermeria: Optional[str] = None

    @validator("prioridad")
    def _check_prioridad(cls, v):
        if v is None:
            return v
        if v not in PRIORITY_VALUES:
            raise ValueError(f"prioridad must be one of {sorted(PRIORITY_VALUES)}")
        return v

    @validator("nivel_conciencia")
    def _check_conciencia(cls, v):
        if v is None:
            return v
        if v not in CONSCIOUSNESS_VALUES:
            raise ValueError(f"nivel_conciencia must be one of {sorted(CONSCIOUSNESS_VALUES)}")
        return v


class AdmissionOut(BaseModel):
    admission_id: str
    paciente_id: int
    cita_id: Optional[int] = None
    fecha_admision: Optional[datetime] = None
    estado_admision: Optional[str] = None
    prioridad: Optional[str] = None
    motivo_consulta: Optional[str] = None

    class Config:
        orm_mode = True


class VitalSignCreate(BaseModel):
    paciente_id: int
    encuentro_id: Optional[int] = None
    fecha: Optional[datetime] = None
    presion_sistolica: Optional[int] = None
    presion_diastolica: Optional[int] = None
    frecuencia_cardiaca: Optional[int] = None
    frecuencia_respiratoria: Optional[int] = None
    temperatura: Optional[float] = None
    saturacion_oxigeno: Optional[int] = None
    peso: Optional[float] = None
    talla: Optional[int] = None

    @validator("temperatura")
    def _check_temperatura(cls, v):
        if v is None:
            return v
        if v <= 30 or v >= 45:
            raise ValueError("temperatura debe estar entre 30 y 45 Celsius")
        return v

    @validator("saturacion_oxigeno")
    def _check_sat(cls, v):
        if v is None:
            return v
        if v < 0 or v > 100:
            raise ValueError("saturacion_oxigeno debe estar entre 0 y 100")
        return v

    @validator("presion_sistolica", "presion_diastolica", "frecuencia_cardiaca", "frecuencia_respiratoria")
    def _check_positive_ints(cls, v):
        if v is None:
            return v
        if v <= 0:
            raise ValueError("Los valores deben ser positivos")
        return v



class VitalSignOut(BaseModel):
    signo_id: int
    paciente_id: int
    fecha: Optional[datetime] = None

    class Config:
        orm_mode = True


class NursingNoteCreate(BaseModel):
    paciente_id: int
    admission_id: Optional[str] = None
    nota: str


class DemographicsUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    sexo: Optional[str] = None
    fecha_nacimiento: Optional[datetime] = None
    contacto: Optional[str] = None
    ciudad: Optional[str] = None



class AdmissionActionResponse(BaseModel):
    admission_id: str
    estado_admision: Optional[str] = None
    fecha_admision: Optional[datetime] = None


class ReferralCreate(BaseModel):
    motivo: Optional[str] = None
    destino: Optional[str] = None
    notas: Optional[str] = None


class MedicationAdminCreate(BaseModel):
    nombre_medicamento: str
    dosis: Optional[str] = None
    notas: Optional[str] = None

    @validator("nombre_medicamento")
    def _not_empty_name(cls, v):
        if not v or not v.strip():
            raise ValueError("nombre_medicamento no puede estar vacío")
        return v.strip()


class TaskOut(BaseModel):
    tarea_id: int
    estado: Optional[str] = None

    class Config:
        orm_mode = True
