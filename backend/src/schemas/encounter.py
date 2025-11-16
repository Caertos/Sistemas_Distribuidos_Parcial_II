from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EncounterOut(BaseModel):
    encuentro_id: int
    fecha: Optional[datetime] = None
    motivo: Optional[str] = None
    diagnostico: Optional[str] = None

    class Config:
        orm_mode = True
