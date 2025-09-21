from pydantic import BaseModel, EmailStr

class OwnerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class OwnerOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: str  # ISO timestamp

    class Config:
        orm_mode = True  # important for SQLAlchemy models

class OwnerLogin(BaseModel):
    email: EmailStr
    password: str