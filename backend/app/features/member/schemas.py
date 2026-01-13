from typing import Optional, List
from pydantic import BaseModel

from app.common.schemas.base import ORMBase

# request [요청]
# 등록
class MemberCreate(BaseModel):
    email: str
    password: str
    nickname: str
    # role: str
    gender: Optional[str] = None
    country: Optional[str] = None
    item_ids: Optional[List[int]] = None
    dislike_tags: Optional[List[str]] = None

# 수정
class MemberUpdate(BaseModel):
    nickname: str
    item_ids: Optional[List[int]] = None
    dislike_tags: Optional[List[str]] = None

# response [응답]
class MemberRead(BaseModel):
    email: str
    nickname: str
    gender: str
    country: str
    role: str
    item_ids: Optional[List[int]] = None
    dislike_tags: Optional[List[str]] = None

