from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime, timezone


class MedicationOut(BaseModel):
    medicamento_id: Optional[int] = None
    nombre: Optional[str] = None
    dosis: Optional[str] = None
    frecuencia: Optional[str] = None
    inicio: Optional[datetime] = None
    fin: Optional[datetime] = None
    via: Optional[str] = None  # route of administration
    prescriptor: Optional[str] = None
    estado: Optional[str] = None
    reacciones: Optional[List[str]] = None

    class Config:
        orm_mode = True

    @validator("inicio", "fin", pre=False, always=False)
    def _ensure_dates_tz(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
