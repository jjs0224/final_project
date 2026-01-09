from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr

from app.common.models.base import ORMBase

class MemberCreate(BaseModel):
    email: str
    password: str
    nickname: str
    gender: Optional[str] = None
    country: Optional[str] = None

class MemberRegisterCreate(BaseModel):
    email: str
    password: str
    nickname: str
    gender: Optional[str] = None
    country: Optional[str] = None
    item_ids: List[int] = Field(default_factory=list)
    hate_input: Optional[List[str]] = None

class MemberRegisterRead(BaseModel):
    email: str
    nickname: str
    gender: Optional[str] = None
    country: Optional[str] = None
    item_ids: List[int] = Field(default_factory=list)
    hate_input: Optional[List[str]] = None

class MemberRead(ORMBase):
    member_id: int
    email: str
    nickname: str
    gender: Optional[str] = None
    country: Optional[str] = None
    # create_member: datetime
    # modify_member: datetime

class MemberUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None