from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PatientOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    fhir_patient_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
