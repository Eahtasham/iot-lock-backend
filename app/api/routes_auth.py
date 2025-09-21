# app/api/routes_auth.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from jwt import encode, decode, PyJWTError
from datetime import datetime, timedelta, timezone
from app.db.crud import create_owner, authenticate_owner, get_owner_by_id, update_owner_password
import os

router = APIRouter()
security = HTTPBearer()

# Configuration
SECRET_KEY = os.getenv("API_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Pydantic models
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    name: str
    email: str

# JWT utilities
def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": str(user_id), "exp": expire}
    return encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[int]:
    """Verify JWT token and return user ID"""
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (PyJWTError, ValueError):
        return None

# Dependency for authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Get current user ID from JWT token"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id

# Routes
@router.post("/register")
async def register(user_data: UserRegister):
    """Register a new owner"""
    owner = await create_owner(
        name=user_data.name,
        email=user_data.email,
        password=user_data.password
    )
    
    if not owner:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return {
        "status": "success",
        "message": "Owner registered successfully",
        "owner": owner
    }

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Authenticate owner and return JWT token"""
    owner = await authenticate_owner(user_credentials.email, user_credentials.password)
    
    if not owner:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(owner["id"])
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": owner["id"],
        "name": owner["name"],
        "email": owner["email"]
    }

@router.post("/logout")
async def logout():
    """Logout endpoint (client should discard token)"""
    return {
        "status": "success",
        "message": "Logged out successfully. Please discard your token."
    }

@router.get("/me")
async def get_current_user_info(current_user_id: int = Depends(get_current_user)):
    """Get current user information"""
    owner = await get_owner_by_id(current_user_id)
    
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    return {
        "status": "success",
        "owner": owner
    }

@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user_id: int = Depends(get_current_user)
):
    """Change user password"""
    # Get current user
    owner = await get_owner_by_id(current_user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # Verify old password
    authenticated = await authenticate_owner(owner["email"], password_data.old_password)
    if not authenticated:
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    # Update password
    success = await update_owner_password(current_user_id, password_data.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    return {
        "status": "success",
        "message": "Password updated successfully"
    }