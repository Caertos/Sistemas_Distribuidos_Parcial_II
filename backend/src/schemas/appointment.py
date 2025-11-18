from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, timezone


class AppointmentOut(BaseModel):
    cita_id: int
    fecha_hora: Optional[datetime] = None
    duracion_minutos: Optional[int] = None
    estado: Optional[str] = None
    motivo: Optional[str] = None

    class Config:
        orm_mode = True

    @validator("fecha_hora", pre=False, always=False)
    def _ensure_fecha_hora_tz(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class AppointmentCreate(BaseModel):
    fecha_hora: datetime
    duracion_minutos: Optional[int] = None
    motivo: Optional[str] = None
    profesional_id: Optional[int] = None

    class Config:
        schema_extra = {
            "example": {
                "fecha_hora": "2025-11-20T10:30:00",
                "duracion_minutos": 30,
                "motivo": "Consulta general",
                "profesional_id": 10
            }
        }

    @validator("fecha_hora", pre=False, always=True)
    def _ensure_fecha_hora_create_tz(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class AppointmentUpdate(BaseModel):
    fecha_hora: Optional[datetime] = None
    duracion_minutos: Optional[int] = None
    motivo: Optional[str] = None
    estado: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "fecha_hora": "2025-11-30T11:00:00",
                "duracion_minutos": 45,
                "motivo": "Cambio de horas",
                "estado": "reprogramada"
            }
        }

    @validator("fecha_hora", pre=False, always=False)
    def _ensure_fecha_hora_update_tz(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
# end