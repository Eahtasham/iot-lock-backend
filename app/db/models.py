from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from app.db.session import engine
import asyncio

Base = declarative_base()

# =========================
# Owners Table
# =========================
class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    visits = relationship("Visit", back_populates="owner", cascade="all, delete")
    device_tokens = relationship("DeviceToken", back_populates="owner", cascade="all, delete")


# =========================
# Visitors Table
# =========================
class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    profile_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    visits = relationship("Visit", back_populates="visitor")


# =========================
# Visits Table
# =========================
class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(Integer, ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True)
    owner_id = Column(Integer, ForeignKey("owners.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(Text, nullable=False)
    status = Column(String, nullable=False, server_default="pending")  # pending/granted/denied
    detected_label = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    visitor = relationship("Visitor", back_populates="visits")
    owner = relationship("Owner", back_populates="visits")


# =========================
# Device Tokens Table
# =========================
class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id", ondelete="CASCADE"), nullable=False)
    fcm_token = Column(Text, nullable=False)
    platform = Column(String, nullable=True)  # 'android' or 'ios'

    # Relationships
    owner = relationship("Owner", back_populates="device_tokens")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
