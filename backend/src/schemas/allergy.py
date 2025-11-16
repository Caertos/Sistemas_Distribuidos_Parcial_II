from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime, timezone


class AllergyOut(BaseModel):
    alergia_id: Optional[int] = None
    agente: Optional[str] = None
    severidad: Optional[str] = None
    nota: Optional[str] = None
    onset: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    clinical_status: Optional[str] = None
    reacciones: Optional[List[str]] = None

    class Config:
        orm_mode = True

    @validator("onset", "resolved_at", pre=False, always=False)
    def _ensure_dates_tz(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
