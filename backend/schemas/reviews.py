from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from .base import ORMBase

class ReviewCreate(BaseModel):
    review_title: str
    review_content: str
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    location: Optional[str] = None
    member_id: int

class ReviewRead(ORMBase):
    review_id: int
    review_title: str
    review_content: str
    rating: Optional[int] = None
    location: Optional[str] = None
    create_review: datetime
    member_id: int

class ReviewUpdate(BaseModel):
    review_title: Optional[str] = None
    review_content: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    location: Optional[str] = None
    member_id: Optional[int] = None