from pydantic import BaseModel
from .base import ORMBase
from typing import Optional

class RestrictionCategoryCreate(BaseModel):
    category_label_ko: str
    category_label_en: str

class RestrictionCategoryRead(ORMBase):
    category_id: int
    category_label_ko: str
    category_label_en: str

class RestrictionCategoryUpdate(BaseModel):
    category_label_ko: Optional[str] = None
    category_label_en: Optional[str] = None