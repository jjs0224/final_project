from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Member(Base):
    __tablename__ = "member"

    member_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)  # 해시 저장 전제
    nickname = Column(String(50), nullable=False, unique=True)
    gender = Column(String(10), nullable=True)
    country = Column(String(50), nullable=True)
    # create_member = Column(DateTime, nullable=False, server_default=func.now())
    # modify_member = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # 관계
    restrictions = relationship("MemberRestrictions", back_populates="member", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="member", cascade="all, delete-orphan")
    communities = relationship("Community", back_populates="member", cascade="all, delete-orphan")