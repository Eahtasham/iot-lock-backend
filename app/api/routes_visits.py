# app/api/routes_visits.py
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from app.db.crud import (
    get_visits_by_owner, 
    create_visit, 
    update_visit_status, 
    get_visit_by_id,
    get_pending_visits_by_owner,
    get_visit_statistics,
    get_recent_activity,
    create_visitor,
    get_visitor_by_id
)

router = APIRouter()

# Pydantic models
class CreateVisitRequest(BaseModel):
    visitor_id: Optional[int] = None
    owner_id: int
    image_url: str
    detected_label: Optional[str] = None
    visitor_name: Optional[str] = None  # For creating visitor on the fly

class UpdateVisitStatusRequest(BaseModel):
    visit_id: int
    status: str  # pending, granted, denied

class VisitResponse(BaseModel):
    status: str
    message: str
    visit: Optional[dict] = None

@router.get("/{owner_id}")
async def fetch_visits(owner_id: int):
    """Get all visits for a specific owner"""
    try:
        visits = await get_visits_by_owner(owner_id)
        return {
            "status": "success",
            "owner_id": owner_id,
            "total_visits": len(visits),
            "visits": visits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{owner_id}/pending")
async def fetch_pending_visits(owner_id: int):
    """Get pending visits for a specific owner"""
    try:
        visits = await get_pending_visits_by_owner(owner_id)
        return {
            "status": "success",
            "owner_id": owner_id,
            "pending_visits": len(visits),
            "visits": visits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{owner_id}/statistics")
async def get_visit_stats(owner_id: int):
    """Get visit statistics for an owner"""
    try:
        stats = await get_visit_statistics(owner_id)
        return {
            "status": "success",
            "owner_id": owner_id,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{owner_id}/recent")
async def get_recent_visits(owner_id: int, limit: int = Query(10, ge=1, le=50)):
    """Get recent visit activity for an owner"""
    try:
        visits = await get_recent_activity(owner_id, limit)
        return {
            "status": "success",
            "owner_id": owner_id,
            "recent_visits": visits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=VisitResponse)
async def create_new_visit(visit_data: CreateVisitRequest):
    """Create a new visit (called by IoT device)"""
    try:
        visitor_id = visit_data.visitor_id
        
        # If no visitor_id but visitor_name is provided, create new visitor
        if not visitor_id and visit_data.visitor_name:
            visitor = await create_visitor(name=visit_data.visitor_name)
            visitor_id = visitor["id"]
        
        # Create the visit
        visit = await create_visit(
            visitor_id=visitor_id,
            owner_id=visit_data.owner_id,
            image_url=visit_data.image_url,
            status="pending",
            detected_label=visit_data.detected_label
        )
        
        return VisitResponse(
            status="success",
            message="Visit created successfully",
            visit=visit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/status", response_model=VisitResponse)
async def update_status(status_data: UpdateVisitStatusRequest):
    """Update visit status (approve/deny access)"""
    try:
        # Validate status
        if status_data.status not in ["pending", "granted", "denied"]:
            raise HTTPException(
                status_code=400, 
                detail="Status must be 'pending', 'granted', or 'denied'"
            )
        
        # Update visit status
        updated_visit = await update_visit_status(status_data.visit_id, status_data.status)
        
        if not updated_visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        return VisitResponse(
            status="success",
            message=f"Visit status updated to {status_data.status}",
            visit=updated_visit
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/visit/{visit_id}")
async def get_visit_details(visit_id: int):
    """Get detailed information about a specific visit"""
    try:
        visit = await get_visit_by_id(visit_id)
        
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        return {
            "status": "success",
            "visit": visit
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve/{visit_id}")
async def approve_visit(visit_id: int):
    """Quick approve a visit (for mobile app)"""
    try:
        updated_visit = await update_visit_status(visit_id, "granted")
        
        if not updated_visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        return {
            "status": "success",
            "message": "Visit approved",
            "visit": updated_visit
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deny/{visit_id}")
async def deny_visit(visit_id: int):
    """Quick deny a visit (for mobile app)"""
    try:
        updated_visit = await update_visit_status(visit_id, "denied")
        
        if not updated_visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        return {
            "status": "success",
            "message": "Visit denied",
            "visit": updated_visit
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# For IoT device to check visit status
@router.get("/status/{visit_id}")
async def check_visit_status(visit_id: int):
    """Check if a visit has been approved/denied (for IoT device polling)"""
    try:
        visit = await get_visit_by_id(visit_id)
        
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        
        return {
            "status": "success",
            "visit_id": visit_id,
            "visit_status": visit["status"],
            "can_unlock": visit["status"] == "granted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))