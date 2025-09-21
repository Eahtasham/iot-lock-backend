from fastapi import APIRouter
router = APIRouter()

from fastapi import APIRouter
from app.db.crud import get_visits_by_owner


router = APIRouter()

@router.get("/{owner_id}")
async def fetch_visits(owner_id: int):
    visits = await get_visits_by_owner(owner_id)
    return {"owner_id": owner_id, "visits": visits}
