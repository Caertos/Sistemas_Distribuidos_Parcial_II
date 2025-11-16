from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .patient import PatientOut


class PatientSummaryOut(BaseModel):
    patient: PatientOut
    appointments: List[dict] = []
    encounters: List[dict] = []

    class Config:
        orm_mode = True
