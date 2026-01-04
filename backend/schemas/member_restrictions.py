from pydantic import BaseModel
from .base import ORMBase

class MemberRestrictionCreate(BaseModel):
    member_id: int
    item_id: int

class MemberRestrictionRead(ORMBase):
    member_restrictions_id: int
    member_id: int
    item_id: int
