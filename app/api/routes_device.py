# app/api/routes_device.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db.crud import (
    register_device_token,
    unregister_device_token,
    get_device_tokens_by_owner,
    get_owner_by_id
)

router = APIRouter()

# =========================
# Pydantic Models
# =========================
class RegisterDeviceRequest(BaseModel):
    owner_id: int
    fcm_token: str
    platform: Optional[str] = None  # "android" or "ios"
    device_name: Optional[str] = None
    app_version: Optional[str] = None

class UnregisterDeviceRequest(BaseModel):
    owner_id: int
    fcm_token: str

class DeviceStatusResponse(BaseModel):
    status: str
    message: str
    device: Optional[Dict[str, Any]] = None

# =========================
# Routes
# =========================

@router.post("/register", response_model=DeviceStatusResponse)
async def register_device(device_data: RegisterDeviceRequest):
    """Register device for push notifications"""
    owner = await get_owner_by_id(device_data.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    if device_data.platform and device_data.platform.lower() not in ["android", "ios"]:
        raise HTTPException(status_code=400, detail="Platform must be 'android' or 'ios'")
    
    if not device_data.fcm_token or len(device_data.fcm_token) < 20:
        raise HTTPException(status_code=400, detail="Invalid FCM token format")
    
    device_token = await register_device_token(
        owner_id=device_data.owner_id,
        fcm_token=device_data.fcm_token,
        platform=device_data.platform.lower() if device_data.platform else None
    )
    
    return DeviceStatusResponse(
        status="success",
        message="Device registered successfully",
        device=dict(device_token)
    )


@router.post("/unregister", response_model=DeviceStatusResponse)
async def unregister_device(device_data: UnregisterDeviceRequest):
    """Unregister device from push notifications"""
    owner = await get_owner_by_id(device_data.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    success = await unregister_device_token(owner_id=device_data.owner_id, fcm_token=device_data.fcm_token)
    if not success:
        raise HTTPException(status_code=404, detail="Device token not found")
    
    return DeviceStatusResponse(status="success", message="Device unregistered successfully")


@router.get("/{owner_id}/tokens")
async def get_owner_devices(owner_id: int):
    """Get all registered devices for an owner"""
    owner = await get_owner_by_id(owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    devices = await get_device_tokens_by_owner(owner_id)
    return {
        "status": "success",
        "owner_id": owner_id,
        "owner_name": owner["name"],
        "total_devices": len(devices),
        "devices": [
            {
                "id": d["id"],
                "platform": d["platform"],
                "token_preview": d["fcm_token"][:20] + "...",
                "registered_at": d.get("created_at", "Unknown")
            } for d in devices
        ]
    }


@router.get("/health")
async def device_health_check():
    """Health check endpoint for device management"""
    return {
        "status": "healthy",
        "message": "Device management service is running",
        "timestamp": datetime.utcnow().isoformat()
    }
