from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class MemberRestrictions(Base):
    __tablename__ = "member_restrictions"

    member_restrictions_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("restriction_items.item_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("member.member_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)

    member = relationship("Member", back_populates="restrictions")
    item = relationship("Item", back_populates="member_restrictions")

    __table_args__ = (
        UniqueConstraint("member_id", "item_id", name="uq_member_item"),
        Index("idx_mr_item_id", "item_id"),
        Index("idx_mr_member_id", "member_id"),
    )