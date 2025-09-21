from .init_db import get_pool

# =========================
# Visits
# =========================
async def get_all_visits():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM visits ORDER BY timestamp DESC",
        )
        return [dict(row) for row in rows]
    
async def get_visits_by_owner(owner_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM visits WHERE owner_id=$1 ORDER BY timestamp DESC", owner_id
        )
        return [dict(row) for row in rows]

async def create_visit(visitor_id, owner_id, image_url, status="pending", detected_label=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO visits(visitor_id, owner_id, image_url, status, detected_label)
            VALUES($1, $2, $3, $4, $5)
            RETURNING *
            """,
            visitor_id, owner_id, image_url, status, detected_label
        )
