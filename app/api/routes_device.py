from fastapi import APIRouter

router = APIRouter()

@router.post("/register")
async def register_device(device_token: str):
    # dummy example
    return {"status": "success", "message": f"Device {device_token} registered"}

@router.post("/unregister")
async def unregister_device(device_token: str):
    # dummy example
    return {"status": "success", "message": f"Device {device_token} unregistered"}