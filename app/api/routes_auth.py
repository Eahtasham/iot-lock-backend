# app/api/routes_auth.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login(username: str, password: str):
    # dummy example
    if username == "admin" and password == "1234":
        return {"status": "success", "message": "Logged in"}
    return {"status": "error", "message": "Invalid credentials"}

@router.post("/register")
async def register(username: str, password: str):
    # dummy example
    return {"status": "success", "message": f"User {username} registered"}

@router.post("/logout")
async def logout():
    # dummy example
    return {"status": "success", "message": "Logged out"}