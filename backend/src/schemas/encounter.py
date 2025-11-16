from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, timezone


class EncounterOut(BaseModel):
    encuentro_id: int
    fecha: Optional[datetime] = None
    motivo: Optional[str] = None
    diagnostico: Optional[str] = None

    class Config:
        orm_mode = True

    @validator("fecha", pre=False, always=False)
    def _ensure_fecha_tz(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
