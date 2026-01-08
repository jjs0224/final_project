from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Items(Base):
    __tablename__ = "restriction_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    item_label_ko = Column(String(100), nullable=False)
    item_label_en = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("restriction_category.category_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)

    category = relationship("Category", back_populates="items")
    member_restrictions = relationship("MemberRestrictions", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_items_category_id", "category_id"),
    )
