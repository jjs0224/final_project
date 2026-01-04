from pydantic import BaseModel
from .base import ORMBase
from typing import Optional

class RestrictionCategoryCreate(BaseModel):
    category_label: str
    category_code: str

class RestrictionCategoryRead(ORMBase):
    category_id: int
    category_label: str
    category_code: str

class RestrictionCategoryUpdate(BaseModel):
    category_label: Optional[str] = None
    category_code: Optional[str] = None