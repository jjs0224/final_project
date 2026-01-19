from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.core.database import Base

class Member(Base):
    __tablename__ = "member"

    member_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)  # 해시 저장 전제
    nickname = Column(String(50), nullable=False, unique=True)
    gender = Column(String(10), nullable=False)
    country = Column(String(50), nullable=False)
    create_member = Column(DateTime, nullable=False, server_default=func.now())
    modify_member = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    role = Column(String(20), nullable=False, default="USER") # USER / ADMIN

    # 관계
    restrictions = relationship("MemberRestrictions", back_populates="member", cascade="all, delete-orphan", passive_deletes=True)
    dislike = relationship("Dislike", back_populates="member", cascade="all, delete-orphan", passive_deletes=True)
    refresh_token = relationship("RefreshToken", uselist=False, back_populates="member", cascade="all, delete-orphan")
    # review = relationship("Review", back_populates="member", cascade="all, delete-orphan")
    # community = relationship("Community", back_populates="member", cascade="all, delete-orphan")