# app/api/routes_auth.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
import jwt
from datetime import datetime, timedelta
from app.db.crud import create_owner, authenticate_owner, get_owner_by_id, update_owner_password
import os

router = APIRouter()

# Configuration - In production, use environment variables
SECRET_KEY = os.getenv("API_KEY")  # Change this in production!
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

# JWT token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except jwt.PyJWTError:
        return None

@router.post("/register", response_model=dict)
async def register(user_data: UserRegister):
    """Register a new owner"""
    try:
        # Create new owner
        owner = await create_owner(
            name=user_data.name,
            email=user_data.email,
            password=user_data.password
        )
        
        if not owner:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        return {
            "status": "success",
            "message": "Owner registered successfully",
            "owner": owner
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Authenticate owner and return JWT token"""
    try:
        # Authenticate user
        owner = await authenticate_owner(user_credentials.email, user_credentials.password)
        
        if not owner:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(owner["id"])}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": owner["id"],
            "name": owner["name"],
            "email": owner["email"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout")
async def logout():
    """Logout endpoint (client should discard token)"""
    return {
        "status": "success",
        "message": "Logged out successfully. Please discard your token."
    }

@router.get("/me")
async def get_current_user(token: str):
    """Get current user information from token"""
    try:
        user_id = verify_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        owner = await get_owner_by_id(int(user_id))
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        
        return {
            "status": "success",
            "owner": owner
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change-password")
async def change_password(password_data: ChangePassword, token: str):
    """Change user password"""
    try:
        user_id = verify_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Verify old password
        owner = await get_owner_by_id(int(user_id))
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        
        # Authenticate with old password
        authenticated = await authenticate_owner(owner["email"], password_data.old_password)
        if not authenticated:
            raise HTTPException(status_code=400, detail="Invalid old password")
        
        # Update password
        success = await update_owner_password(int(user_id), password_data.new_password)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update password")
        
        return {
            "status": "success",
            "message": "Password updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Dependency to get current user from token
async def get_current_user_dependency(token: str) -> int:
    """Dependency to extract user ID from token"""
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return int(user_id)