# app/api/routes_notify.py
from fastapi import APIRouter, HTTPException, BackgroundTasks , Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import json
import numpy as np
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import cv2
from datetime import datetime
from app.db.crud import get_device_tokens_by_owner, get_visit_by_id, remove_invalid_tokens

router = APIRouter()

# Expo Push Notification Configuration
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

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

async def send_expo_notification(expo_token: str, title: str, body: str, data: Optional[Dict] = None):
    """Send Expo push notification to a specific token"""
    headers = {
        "Accept": "application/json",
        "Accept-encoding": "gzip, deflate",
        "Content-Type": "application/json"
    }
    
    payload = {
        "to": expo_token,
        "title": title,
        "body": body,
        "data": data or {},
        "sound": "default",
        "priority": "high",
        "channelId": "default"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(EXPO_PUSH_URL, json=payload, headers=headers)
            result = response.json()
            
            # Check for errors in the response
            if response.status_code == 200:
                if "data" in result and len(result["data"]) > 0:
                    ticket = result["data"][0]
                    if ticket.get("status") == "error":
                        return {"success": 0, "error": ticket.get("message", "Unknown error")}
                    else:
                        return {"success": 1, "id": ticket.get("id")}
                else:
                    return {"success": 0, "error": "No data in response"}
            else:
                return {"success": 0, "error": f"HTTP {response.status_code}: {result}"}
                
        except Exception as e:
            print(f"Expo Push Error: {e}")
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
            expo_token = device.get("expo_push_token")
            if not expo_token:
                continue
                
            result = await send_expo_notification(
                expo_token=expo_token,
                title=title,
                body=body,
                data=data
            )
            
            results.append({
                "token": expo_token[:30] + "...",  # Truncate for privacy
                "platform": device["platform"],
                "device_name": device.get("device_name", "Unknown Device"),
                "result": result
            })
            
            # Check for invalid tokens
            if result.get("success") == 0 and "DeviceNotRegistered" in str(result.get("error", "")):
                invalid_tokens.append(expo_token)
        
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
        title = "🔔 New Visitor Alert!"
        body = f"{visitor_name} is at your door"
        
        # Additional data for the mobile app
        data = {
            "visit_id": str(visit["id"]),
            "visitor_name": visitor_name or "",
            "image_url": visit.get("image_url", ""),
            "detected_label": visit.get("detected_label", ""),
            "timestamp": visit["timestamp"].isoformat() if visit.get("timestamp") else "",
            "action": "new_visit",
            "screen": "VisitDetails"  # For navigation
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
    """Send test notification to verify Expo setup"""
    try:
        result = await send_notifications_to_owner(
            owner_id=owner_id,
            title="🔔 Someone has arrived",
            body="Open the app to accept or reject the entry request.",
            data={
                "action": "test", 
                "timestamp": "2024-01-01T00:00:00Z",
                "screen": "Home"
            }
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
                    "device_name": device.get("device_name", "Unknown Device"),
                    "token_preview": device["expo_push_token"][:30] + "..." if device.get("expo_push_token") else None
                }
                for device in device_tokens
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def notification_health_check():
    """Health check endpoint for notification service"""
    return {
        "status": "success",
        "message": "Expo notification service is running",
        "service_type": "expo_push_notifications"
    }

# Raspberry Pi endpoint - call this from your Pi
@router.post("/raspberry-pi/visitor-detected")
async def raspberry_pi_visitor_detected(
    owner_id: int,
    visitor_name: Optional[str] = "Unknown visitor",
    image_url: Optional[str] = None,
    detected_label: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Endpoint for Raspberry Pi to trigger visitor notifications"""
    try:
        title = "🚪 Someone's at the Door!"
        body = f"{visitor_name} detected at your door"
        
        data = {
            "visitor_name": visitor_name or "Unknown visitor",
            "image_url": image_url or "",
            "detected_label": detected_label or "",
            "timestamp": datetime.utcnow().isoformat(),
            "action": "visitor_detected",
            "screen": "VisitorAlert"
        }
        
        background_tasks.add_task(
            send_notifications_to_owner,
            owner_id=owner_id,
            title=title,
            body=body,
            data=data
        )
        
        return {
            "status": "success",
            "message": "Visitor detection notification queued",
            "owner_id": owner_id,
            "visitor_name": visitor_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# ======================
# Database connection
# ======================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "ml", "data")

recognizer_path = os.path.join(DATA_DIR, "face_trained.yml")
people_path = os.path.join(DATA_DIR, "people.npy")

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(recognizer_path)
people = np.load(people_path, allow_pickle=True)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

CONFIDENCE_THRESHOLD = 60
NOTIFICATION_ENDPOINT = "https://iot-lock-backend.onrender.com/api/notify/raspberry-pi/visitor-detected"

# ======================
# Database connection
# ======================
DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
DB_PORT = "6543"
DB_NAME = "postgres"
DB_USER = "postgres.nqurgqrqauaxboujobca"
DB_PASS = "Iot@12345"

def get_visitor_id(visitor_name: str) -> int:
    """Fetch visitor_id from DB using visitor_name."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id FROM visitors WHERE name = %s LIMIT 1", (visitor_name,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row["id"]
        else:
            return 0
    except Exception as e:
        print(f"DB error: {e}")
        return 0

def insert_visit(visitor_id: int, owner_id: int, image_url: str):
    """Insert a visit record into visits table."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO visits (visitor_id, owner_id, image_url)
            VALUES (%s, %s, %s)
        """, (visitor_id if visitor_id != 0 else None, owner_id, image_url))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Failed to insert visit record: {e}")

# ======================
# Request model
# ======================
class DetectRequest(BaseModel):
    image_url: str  # Single S3 URL

# ======================
# Endpoint
# ======================
@router.post("/detect-visitor")
async def detect_visitor(
    req: DetectRequest
):
    visitor_name = "Unknown"
    detected_label = "Unknown"
    visitor_id = 0
    owner_id = 12
    try:
        # Download image
        img_data = requests.get(req.image_url, timeout=10).content
        img_array = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=8,
            minSize=(80, 80)
        )

        if len(faces) > 0:
            # Take the first detected face
            x, y, w, h = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            label, confidence = recognizer.predict(face_roi)

            if confidence < CONFIDENCE_THRESHOLD:
                visitor_name = people[label].replace("_", " ")
                detected_label = "Known"
                visitor_id = get_visitor_id(visitor_name)
            else:
                visitor_name = "Unknown"
                detected_label = "Unknown"
                visitor_id = 0
        else:
            visitor_name = "No face detected"
            detected_label = "Unknown"
            visitor_id = 0

    except Exception as e:
        print(f"Error processing {req.image_url}: {e}")
        visitor_name = "Error"
        detected_label = "Unknown"
        visitor_id = 0

    payload = {
        "visitor_id": visitor_id,
        "owner_id": owner_id,
        "image url": req.image_url,
        "detected label": detected_label,
        "visitor name": visitor_name
    }

    # Insert into visits table
    insert_visit(visitor_id, owner_id, req.image_url)

    # Send notification
    try:
        notification_url = f"https://iot-lock-backend.onrender.com/api/notify/test/{owner_id}"
        requests.post(notification_url, timeout=5)
    except Exception as e:
        print(f"Failed to send visitor notification: {e}")

    return payload