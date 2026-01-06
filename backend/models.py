from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Member(Base):
    __tablename__ = "member"

    member_id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)  # 해시 저장 전제
    nickname = Column(String(50), nullable=False)
    gender = Column(String(10), nullable=True)
    country = Column(String(50), nullable=True)
    create_member = Column(DateTime, nullable=False, server_default=func.now())
    modify_member = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # 관계
    restrictions = relationship("MemberRestrictions", back_populates="member", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="member", cascade="all, delete-orphan")
    communities = relationship("Community", back_populates="member", cascade="all, delete-orphan")


class RestrictionCategory(Base):
    __tablename__ = "restriction_category"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_label = Column(String(50), nullable=False)
    category_code = Column(String(50), nullable=False, unique=True)

    items = relationship("RestrictionItems", back_populates="category", cascade="all, delete-orphan")


class RestrictionItems(Base):
    __tablename__ = "restriction_items"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    item_label_ko = Column(String(100), nullable=False)
    item_label_en = Column(String(100), nullable=False, unique=True)
    category_id = Column(Integer, ForeignKey("restriction_category.category_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)

    category = relationship("RestrictionCategory", back_populates="items")
    members = relationship("MemberRestrictions", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_items_category_id", "category_id"),
    )


class MemberRestrictions(Base):
    __tablename__ = "member_restrictions"

    member_restrictions_id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("restriction_items.item_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    member_id = Column(Integer, ForeignKey("member.member_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)

    member = relationship("Member", back_populates="restrictions")
    item = relationship("RestrictionItems", back_populates="members")

    __table_args__ = (
        UniqueConstraint("member_id", "item_id", name="uq_member_item"),
        Index("idx_mr_item_id", "item_id"),
        Index("idx_mr_member_id", "member_id"),
    )


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


class Community(Base):
    __tablename__ = "community"

    community_id = Column(Integer, primary_key=True, autoincrement=True)
    field = Column(Text, nullable=True)  # ERD의 Field(추후 구체화)
    member_id = Column(Integer, ForeignKey("member.member_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)

    member = relationship("Member", back_populates="communities")

    __table_args__ = (
        Index("idx_community_member_id", "member_id"),
    )
