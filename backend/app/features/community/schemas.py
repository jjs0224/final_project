from typing import Optional
from pydantic import BaseModel

from app.common.models.base import ORMBase

class CommunityCreate(BaseModel):
    field: Optional[str] = None
    member_id: int

class CommunityRead(ORMBase):
    community_id: int
    field: Optional[str] = None
    member_id: int
