# app/api/routes_notify.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import json
from app.db.crud import get_device_tokens_by_owner, get_visit_by_id, remove_invalid_tokens

router = APIRouter()

# FCM Configuration - In production, use environment variables
FCM_SERVER_KEY = "your-fcm-server-key"  # Replace with your actual FCM server key
FCM_URL = "https://fcm.googleapis.com/fcm/send"

# Pydantic models
class SendNotificationRequest(BaseModel):
    owner_id: int
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None

class VisitNotificationRequest(BaseModel):
    visit_id: int

class BulkNotificationRequest(BaseModel):
    owner_ids: List[int]
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None

async def send_fcm_notification(fcm_token: str, title: str, body: str, data: Optional[Dict] = None):
    """Send FCM notification to a specific token"""
    headers = {
        "Authorization": f"key={FCM_SERVER_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "to": fcm_token,
        "notification": {
            "title": title,
            "body": body,
            "sound": "default"
        },
        "data": data or {},
        "priority": "high"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(FCM_URL, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            print(f"FCM Error: {e}")
            return {"success": 0, "error": str(e)}

async def send_notifications_to_owner(owner_id: int, title: str, body: str, data: Optional[Dict] = None):
    """Send notification to all devices of an owner"""
    try:
        # Get all device tokens for the owner
        device_tokens = await get_device_tokens_by_owner(owner_id)
        
        if not device_tokens:
            return {"success": 0, "message": "No devices registered for this owner"}
        
        results = []
        invalid_tokens = []
        
        for device in device_tokens:
            result = await send_fcm_notification(
                fcm_token=device["fcm_token"],
                title=title,
                body=body,
                data=data
            )
            
            results.append({
                "token": device["fcm_token"][:20] + "...",  # Truncate for privacy
                "platform": device["platform"],
                "result": result
            })
            
            # Check for invalid tokens
            if result.get("success") == 0 and "InvalidRegistration" in str(result.get("results", [])):
                invalid_tokens.append(device["fcm_token"])
        
        # Remove invalid tokens
        if invalid_tokens:
            await remove_invalid_tokens(invalid_tokens)
        
        return {
            "total_sent": len(device_tokens),
            "invalid_tokens_removed": len(invalid_tokens),
            "results": results
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.post("/send")
async def send_notification(notification_data: SendNotificationRequest, background_tasks: BackgroundTasks):
    """Send notification to a specific owner"""
    try:
        # Send notification in background
        background_tasks.add_task(
            send_notifications_to_owner,
            owner_id=notification_data.owner_id,
            title=notification_data.title,
            body=notification_data.body,
            data=notification_data.data
        )
        
        return {
            "status": "success",
            "message": "Notification queued for sending",
            "owner_id": notification_data.owner_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visit-notification")
async def send_visit_notification(notification_data: VisitNotificationRequest, background_tasks: BackgroundTasks):
    """Send notification about a new visit"""
    try:
        # Get visit details
        visit = await get_visit_by_id(notification_data.visit_id)
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        # Prepare notification content
        visitor_name = visit.get("visitor_name", "Unknown visitor")
        title = "New Visitor Alert!"
        body = f"{visitor_name} is at your door"
        
        # Additional data for the mobile app
        data = {
            "visit_id": str(visit["id"]),
            "visitor_name": visitor_name or "",
            "image_url": visit["image_url"],
            "detected_label": visit.get("detected_label", ""),
            "timestamp": visit["timestamp"].isoformat() if visit.get("timestamp") else "",
            "action": "new_visit"
        }
        
        # Send notification in background
        background_tasks.add_task(
            send_notifications_to_owner,
            owner_id=visit["owner_id"],
            title=title,
            body=body,
            data=data
        )
        
        return {
            "status": "success",
            "message": "Visit notification queued for sending",
            "visit_id": notification_data.visit_id,
            "owner_id": visit["owner_id"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-send")
async def send_bulk_notification(notification_data: BulkNotificationRequest, background_tasks: BackgroundTasks):
    """Send notification to multiple owners"""
    try:
        # Send notifications to all owners in background
        for owner_id in notification_data.owner_ids:
            background_tasks.add_task(
                send_notifications_to_owner,
                owner_id=owner_id,
                title=notification_data.title,
                body=notification_data.body,
                data=notification_data.data
            )
        
        return {
            "status": "success",
            "message": f"Bulk notification queued for {len(notification_data.owner_ids)} owners",
            "owner_count": len(notification_data.owner_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/{owner_id}")
async def send_test_notification(owner_id: int):
    """Send test notification to verify FCM setup"""
    try:
        result = await send_notifications_to_owner(
            owner_id=owner_id,
            title="Test Notification",
            body="This is a test notification from your IoT lock system",
            data={"action": "test", "timestamp": "2024-01-01T00:00:00Z"}
        )
        
        return {
            "status": "success",
            "message": "Test notification sent",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{owner_id}")
async def get_notification_status(owner_id: int):
    """Get notification setup status for an owner"""
    try:
        device_tokens = await get_device_tokens_by_owner(owner_id)
        
        return {
            "status": "success",
            "owner_id": owner_id,
            "notifications_enabled": len(device_tokens) > 0,
            "registered_devices": len(device_tokens),
            "devices": [
                {
                    "platform": device["platform"],
                    "token_preview": device["fcm_token"][:20] + "..." if device["fcm_token"] else None
                }
                for device in device_tokens
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoint for receiving notifications (if needed)
@router.post("/receive")
async def receive_notification(payload: Dict[str, Any]):
    """Receive notification webhook (for external integrations)"""
    try:
        # Process incoming notification/webhook
        # This could be used for external service integrations
        
        return {
            "status": "success",
            "message": "Notification received and processed",
            "payload": payload
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def notification_health_check():
    """Health check endpoint for notification service"""
    return {
        "status": "success",
        "message": "Notification service is running",
        "fcm_configured": bool(FCM_SERVER_KEY and FCM_SERVER_KEY != "your-fcm-server-key")
    }