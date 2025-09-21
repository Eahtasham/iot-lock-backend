from pydantic import BaseModel
from typing import Literal

class DeviceTokenCreate(BaseModel):
    owner_id: int
    fcm_token: str
    platform: Literal['android','ios']

class DeviceTokenOut(BaseModel):
    id: int
    owner_id: int
    fcm_token: str
    platform: str

    class Config:
        orm_mode = True

class DeviceTokenUpdate(BaseModel):
    fcm_token: str