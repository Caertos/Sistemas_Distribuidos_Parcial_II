from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AppointmentOut(BaseModel):
    cita_id: int
    fecha_hora: Optional[datetime] = None
    duracion_minutos: Optional[int] = None
    estado: Optional[str] = None
    motivo: Optional[str] = None

    class Config:
        orm_mode = True


class AppointmentCreate(BaseModel):
    fecha_hora: datetime
    duracion_minutos: Optional[int] = None
    motivo: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "fecha_hora": "2025-11-20T10:30:00",
                "duracion_minutos": 30,
                "motivo": "Consulta general"
            }
        }


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

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AppointmentOut(BaseModel):
    cita_id: int
    fecha_hora: Optional[datetime] = None
    duracion_minutos: Optional[int] = None
    estado: Optional[str] = None
    motivo: Optional[str] = None

    class Config:
        orm_mode = True