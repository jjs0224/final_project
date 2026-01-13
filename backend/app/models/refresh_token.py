from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship

# refresh 원문 저장 아닌 hash 처리된 값 저장
class RefreshToken(Base):
    __tablename__ = "refresh_token"

    # ✅ 1인 1 refresh만 유지(현재 네 Redis 구조랑 동일)
    member_id = Column(Integer, ForeignKey("member.member_id", ondelete="CASCADE"), primary_key=True)

    jti = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    member = relationship("Member", back_populates="refresh_token")