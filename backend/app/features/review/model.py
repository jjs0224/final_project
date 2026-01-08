from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class Review(Base):
    __tablename__ = "review"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    review_title = Column(Text, nullable=False)
    review_content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    location = Column(String(100), nullable=True)
    create_review = Column(DateTime, nullable=False, server_default=func.now())
    member_id = Column(Integer, ForeignKey("member.member_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)

    member = relationship("Member", back_populates="reviews")

    __table_args__ = (
        Index("idx_review_member_id", "member_id"),
    )