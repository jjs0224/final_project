from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Community(Base):

    __tablename__ = "community"

    community_id = Column(Integer, primary_key=True, autoincrement=True)
    field = Column(Text, nullable=True)  # ERD의 Field(추후 구체화)
    member_id = Column(Integer, ForeignKey("member.member_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)

    member = relationship("Member", back_populates="community")

    __table_args__ = (
        Index("idx_community_member_id", "member_id"),
    )