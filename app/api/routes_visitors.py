# app/api/routes_visitors.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.db.crud import (
    create_visitor,
    get_visitor_by_id,
    get_all_visitors,
    update_visitor
)

router = APIRouter()

# Pydantic models
class CreateVisitorRequest(BaseModel):
    name: Optional[str] = None
    profile_image_url: Optional[str] = None

class UpdateVisitorRequest(BaseModel):
    name: Optional[str] = None
    profile_image_url: Optional[str] = None

@router.post("/create")
async def create_new_visitor(visitor_data: CreateVisitorRequest):
    """Create a new visitor"""
    try:
        visitor = await create_visitor(
            name=visitor_data.name,
            profile_image_url=visitor_data.profile_image_url
        )
        
        return {
            "status": "success",
            "message": "Visitor created successfully",
            "visitor": visitor
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{visitor_id}")
async def get_visitor_details(visitor_id: int):
    """Get visitor details by ID"""
    try:
        visitor = await get_visitor_by_id(visitor_id)
        
        if not visitor:
            raise HTTPException(status_code=404, detail="Visitor not found")
        
        return {
            "status": "success",
            "visitor": visitor
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_all_visitors_list():
    """Get all visitors"""
    try:
        visitors = await get_all_visitors()
        return {
            "status": "success",
            "total_visitors": len(visitors),
            "visitors": visitors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{visitor_id}")
async def update_visitor_details(visitor_id: int, visitor_data: UpdateVisitorRequest):
    """Update visitor information"""
    try:
        # Check if visitor exists
        existing_visitor = await get_visitor_by_id(visitor_id)
        if not existing_visitor:
            raise HTTPException(status_code=404, detail="Visitor not found")
        
        # Update visitor
        updated_visitor = await update_visitor(
            visitor_id=visitor_id,
            name=visitor_data.name,
            profile_image_url=visitor_data.profile_image_url
        )
        
        return {
            "status": "success",
            "message": "Visitor updated successfully",
            "visitor": updated_visitor
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))