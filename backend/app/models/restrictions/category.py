from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index, Boolean
)
from sqlalchemy.orm import relationship

from backend.app.core.database import Base

class Category(Base):
    __tablename__ = "restriction_category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_label_ko = Column(String(50), nullable=False)
    category_label_en = Column(String(50), nullable=False)
    category_active = Column(Boolean, nullable=False, server_default="1")
    item = relationship("Item", back_populates="category")