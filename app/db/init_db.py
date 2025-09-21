import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL")

pool: asyncpg.pool.Pool = None

async def init_db():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL, max_size=10)

async def get_pool():
    if pool is None:
        await init_db()
    return pool

async def close_pool():
    global pool
    if pool is not None:
        await pool.close()
        pool = None