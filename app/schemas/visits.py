from pydantic import BaseModel
from typing import Optional

class VisitCreate(BaseModel):
    visitor_id: Optional[int] = None
    owner_id: int
    image_url: str

class VisitOut(BaseModel):
    id: int
    visitor_id: Optional[int]
    owner_id: int
    image_url: str
    status: str
    detected_label: Optional[str]
    timestamp: str

    class Config:
        orm_mode = True

class VisitUpdate(BaseModel):
    status: str