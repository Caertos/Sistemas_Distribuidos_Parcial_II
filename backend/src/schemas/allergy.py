from pydantic import BaseModel
from typing import Optional


class AllergyOut(BaseModel):
    alergia_id: Optional[int] = None
    agente: Optional[str] = None
    severidad: Optional[str] = None
    nota: Optional[str] = None

    class Config:
        orm_mode = True
