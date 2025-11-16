from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .patient import PatientOut
from .appointment import AppointmentOut
from .encounter import EncounterOut


class PatientSummaryOut(BaseModel):
    patient: PatientOut
    appointments: List[AppointmentOut] = []
    encounters: List[EncounterOut] = []

    class Config:
        orm_mode = True
