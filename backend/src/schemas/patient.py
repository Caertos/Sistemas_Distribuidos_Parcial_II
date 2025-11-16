from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, timezone


class PatientOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    fhir_patient_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

    @validator("created_at", pre=False, always=False)
    def _ensure_created_at_tz(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
