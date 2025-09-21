# app/api/routes_visits.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_visits():
    return {"visits": []}

@router.post("/")
async def add_visit(visitor_name: str):
    return {"status": "success", "visitor_name": visitor_name}

@router.get("/{visit_id}")
async def get_visit(visit_id: int):
    return {"visit": {"id": visit_id}}