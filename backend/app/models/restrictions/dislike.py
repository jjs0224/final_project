from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, JSON, Text
from app.core.database import Base  # 네 Base 경로에 맞춰 수정
from sqlalchemy.orm import relationship

class Dislike(Base):
    __tablename__ = "restriction_dislike"

    dislike_id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("member.member_id", ondelete="CASCADE"), nullable=False, unique=True)
    dislike_tag = Column(Text, nullable=True)

    member = relationship("Member", back_populates="dislike")
