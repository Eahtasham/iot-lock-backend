from pydantic import BaseModel
from typing import Optional

# Request model for creating visitor
class VisitorCreate(BaseModel):
    name: Optional[str] = None
    profile_image_url: Optional[str] = None

# Response model for visitor info
class VisitorOut(BaseModel):
    id: int
    name: Optional[str]
    profile_image_url: Optional[str]
    created_at: str

    class Config:
        orm_mode = True
