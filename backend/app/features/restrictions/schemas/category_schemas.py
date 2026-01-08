from pydantic import BaseModel
from app.common.models.base import ORMBase
from typing import Optional

class CategoryCreate(BaseModel):
    category_label_ko: str
    category_label_en: str

class CategoryRead(ORMBase):
    category_id: int
    category_label_ko: str
    category_label_en: str

class CategoryUpdate(BaseModel):
    category_label: Optional[str] = None
    category_code: Optional[str] = None