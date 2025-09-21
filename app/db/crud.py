# app/db/crud.py
from .init_db import get_pool
from datetime import datetime
import hashlib
import secrets
from typing import Optional, List, Dict, Any

# =========================
# Utility Functions
# =========================
def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = secrets.token_hex(32)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return salt + password_hash.hex()

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    salt = hashed_password[:64]
    stored_hash = hashed_password[64:]
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return password_hash.hex() == stored_hash

# =========================
# Owners CRUD
# =========================
async def create_owner(name: str, email: str, password: str) -> Optional[Dict[str, Any]]:
    """Create a new owner"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if email already exists
        existing = await conn.fetchrow("SELECT id FROM owners WHERE email = $1", email)
        if existing:
            return None  # Email already exists
        
        password_hash = hash_password(password)
        row = await conn.fetchrow(
            """
            INSERT INTO owners (name, email, password_hash)
            VALUES ($1, $2, $3)
            RETURNING id, name, email, created_at
            """,
            name, email, password_hash
        )
        return dict(row) if row else None

async def get_owner_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get owner by email"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM owners WHERE email = $1", email
        )
        return dict(row) if row else None

async def get_owner_by_id(owner_id: int) -> Optional[Dict[str, Any]]:
    """Get owner by ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, email, created_at FROM owners WHERE id = $1", owner_id
        )
        return dict(row) if row else None

async def authenticate_owner(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate owner with email and password"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM owners WHERE email = $1", email
        )
        if row and verify_password(password, row['password_hash']):
            return {
                'id': row['id'],
                'name': row['name'],
                'email': row['email'],
                'created_at': row['created_at']
            }
        return None

async def update_owner_password(owner_id: int, new_password: str) -> bool:
    """Update owner password"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        password_hash = hash_password(new_password)
        result = await conn.execute(
            "UPDATE owners SET password_hash = $1 WHERE id = $2",
            password_hash, owner_id
        )
        return result == "UPDATE 1"

# =========================
# Visitors CRUD
# =========================
async def create_visitor(name: Optional[str] = None, profile_image_url: Optional[str] = None) -> Dict[str, Any]:
    """Create a new visitor"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO visitors (name, profile_image_url)
            VALUES ($1, $2)
            RETURNING *
            """,
            name, profile_image_url
        )
        return dict(row)

async def get_visitor_by_id(visitor_id: int) -> Optional[Dict[str, Any]]:
    """Get visitor by ID"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM visitors WHERE id = $1", visitor_id
        )
        return dict(row) if row else None

async def get_all_visitors() -> List[Dict[str, Any]]:
    """Get all visitors"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM visitors ORDER BY created_at DESC")
        return [dict(row) for row in rows]

async def update_visitor(visitor_id: int, name: Optional[str] = None, profile_image_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update visitor information"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Build dynamic update query
        updates = []
        params = []
        param_count = 1
        
        if name is not None:
            updates.append(f"name = ${param_count}")
            params.append(name)
            param_count += 1
        
        if profile_image_url is not None:
            updates.append(f"profile_image_url = ${param_count}")
            params.append(profile_image_url)
            param_count += 1
        
        if not updates:
            return await get_visitor_by_id(visitor_id)
        
        params.append(visitor_id)
        query = f"UPDATE visitors SET {', '.join(updates)} WHERE id = ${param_count} RETURNING *"
        
        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None

# =========================
# Visits CRUD
# =========================
async def get_all_visits() -> List[Dict[str, Any]]:
    """Get all visits with visitor and owner details"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT v.*, vis.name as visitor_name, vis.profile_image_url, o.name as owner_name, o.email as owner_email
            FROM visits v
            LEFT JOIN visitors vis ON v.visitor_id = vis.id
            LEFT JOIN owners o ON v.owner_id = o.id
            ORDER BY v.timestamp DESC
            """
        )
        return [dict(row) for row in rows]

async def get_visits_by_owner(owner_id: int) -> List[Dict[str, Any]]:
    """Get visits for a specific owner with visitor details"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT v.*, vis.name as visitor_name, vis.profile_image_url
            FROM visits v
            LEFT JOIN visitors vis ON v.visitor_id = vis.id
            WHERE v.owner_id = $1
            ORDER BY v.timestamp DESC
            """,
            owner_id
        )
        return [dict(row) for row in rows]

async def create_visit(visitor_id: Optional[int], owner_id: int, image_url: str, 
                      status: str = "pending", detected_label: Optional[str] = None) -> Dict[str, Any]:
    """Create a new visit"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO visits (visitor_id, owner_id, image_url, status, detected_label)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            visitor_id, owner_id, image_url, status, detected_label
        )
        return dict(row)

async def update_visit_status(visit_id: int, status: str) -> Optional[Dict[str, Any]]:
    """Update visit status (pending/granted/denied)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE visits SET status = $1 WHERE id = $2 RETURNING *",
            status, visit_id
        )
        return dict(row) if row else None

async def get_visit_by_id(visit_id: int) -> Optional[Dict[str, Any]]:
    """Get visit by ID with visitor and owner details"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT v.*, vis.name as visitor_name, vis.profile_image_url, o.name as owner_name, o.email as owner_email
            FROM visits v
            LEFT JOIN visitors vis ON v.visitor_id = vis.id
            LEFT JOIN owners o ON v.owner_id = o.id
            WHERE v.id = $1
            """,
            visit_id
        )
        return dict(row) if row else None

async def get_pending_visits_by_owner(owner_id: int) -> List[Dict[str, Any]]:
    """Get pending visits for a specific owner"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT v.*, vis.name as visitor_name, vis.profile_image_url
            FROM visits v
            LEFT JOIN visitors vis ON v.visitor_id = vis.id
            WHERE v.owner_id = $1 AND v.status = 'pending'
            ORDER BY v.timestamp DESC
            """,
            owner_id
        )
        return [dict(row) for row in rows]

# =========================
# Device Tokens CRUD
# =========================
async def register_device_token(owner_id: int, fcm_token: str, platform: Optional[str] = None) -> Dict[str, Any]:
    """Register or update device token for push notifications"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if token already exists for this owner
        existing = await conn.fetchrow(
            "SELECT id FROM device_tokens WHERE owner_id = $1 AND fcm_token = $2",
            owner_id, fcm_token
        )
        
        if existing:
            # Update existing token
            row = await conn.fetchrow(
                "UPDATE device_tokens SET platform = $1 WHERE id = $2 RETURNING *",
                platform, existing['id']
            )
        else:
            # Create new token
            row = await conn.fetchrow(
                """
                INSERT INTO device_tokens (owner_id, fcm_token, platform)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                owner_id, fcm_token, platform
            )
        return dict(row)

async def unregister_device_token(owner_id: int, fcm_token: str) -> bool:
    """Remove device token"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM device_tokens WHERE owner_id = $1 AND fcm_token = $2",
            owner_id, fcm_token
        )
        return result == "DELETE 1"

async def get_device_tokens_by_owner(owner_id: int) -> List[Dict[str, Any]]:
    """Get all device tokens for an owner"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM device_tokens WHERE owner_id = $1",
            owner_id
        )
        return [dict(row) for row in rows]

async def remove_invalid_tokens(invalid_tokens: List[str]) -> int:
    """Remove invalid FCM tokens"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not invalid_tokens:
            return 0
        
        placeholders = ','.join(f'${i+1}' for i in range(len(invalid_tokens)))
        result = await conn.execute(
            f"DELETE FROM device_tokens WHERE fcm_token IN ({placeholders})",
            *invalid_tokens
        )
        return int(result.split()[-1]) if result.startswith("DELETE") else 0

# =========================
# Analytics and Statistics
# =========================
async def get_visit_statistics(owner_id: int) -> Dict[str, Any]:
    """Get visit statistics for an owner"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow(
            """
            SELECT 
                COUNT(*) as total_visits,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_visits,
                COUNT(CASE WHEN status = 'granted' THEN 1 END) as granted_visits,
                COUNT(CASE WHEN status = 'denied' THEN 1 END) as denied_visits,
                COUNT(CASE WHEN DATE(timestamp) = CURRENT_DATE THEN 1 END) as today_visits
            FROM visits
            WHERE owner_id = $1
            """,
            owner_id
        )
        return dict(stats) if stats else {}

async def get_recent_activity(owner_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent visit activity for an owner"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT v.*, vis.name as visitor_name, vis.profile_image_url
            FROM visits v
            LEFT JOIN visitors vis ON v.visitor_id = vis.id
            WHERE v.owner_id = $1
            ORDER BY v.timestamp DESC
            LIMIT $2
            """,
            owner_id, limit
        )
        return [dict(row) for row in rows]