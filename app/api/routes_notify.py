# app/api/routes_notify.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/send")
async def send_notification(message: str):
    # example: send notification
    return {"status": "success", "message": message}

@router.post("/receive")
async def receive_notification(message: str):
    # example: receive notification
    return {"status": "success", "message": message}