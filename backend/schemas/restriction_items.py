from pydantic import BaseModel
from .base import ORMBase
from typing import Optional

class RestrictionItemCreate(BaseModel):
    item_label_ko: str
    item_label_en: str
    category_id: int

class RestrictionItemRead(ORMBase):
    item_id: int
    item_label_ko: str
    item_label_en: str
    category_id: int

class RestrictionItemUpdate(BaseModel):
    item_label_ko: Optional[str] = None
    item_label_en: Optional[str] = None
    category_id: Optional[int] = None