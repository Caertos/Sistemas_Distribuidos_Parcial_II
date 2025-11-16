from pydantic import BaseModel
from typing import Optional


class MedicationOut(BaseModel):
    medicamento_id: Optional[int] = None
    nombre: Optional[str] = None
    dosis: Optional[str] = None
    frecuencia: Optional[str] = None

    class Config:
        orm_mode = True
