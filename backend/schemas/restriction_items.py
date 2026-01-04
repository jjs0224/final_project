from pydantic import BaseModel
from .base import ORMBase
from typing import Optional

class RestrictionItemCreate(BaseModel):
    item_label: str
    item_code: str
    category_id: int

class RestrictionItemRead(ORMBase):
    item_id: int
    item_label: str
    item_code: str
    category_id: int

class RestrictionItemUpdate(BaseModel):
    item_label: Optional[str] = None
    item_code: Optional[str] = None
    category_id: Optional[int] = None