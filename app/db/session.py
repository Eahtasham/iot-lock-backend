from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("SUPABASE_DB_URL") 


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=5,       # max persistent connections
    max_overflow=10,   # additional temporary connections
)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
