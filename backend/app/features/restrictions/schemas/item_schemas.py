from pydantic import BaseModel
from app.common.models.base import ORMBase
from typing import Optional

class ItemCreate(BaseModel):
    item_label_ko: str
    item_label_en: str
    category_id: int

class ItemRead(ORMBase):
    item_id: int
    item_label_ko: str
    item_label_en: str
    category_id: int

class ItemUpdate(BaseModel):
    item_label: Optional[str] = None
    item_code: Optional[str] = None
    category_id: Optional[int] = None