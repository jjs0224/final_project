from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base

class Category(Base):
    __tablename__ = "restriction_category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_label_ko = Column(String(50), nullable=False)
    category_label_en = Column(String(50), nullable=False)

    items = relationship("Items", back_populates="category", cascade="all, delete-orphan")