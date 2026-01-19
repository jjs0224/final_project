from pydantic import BaseModel, Field
from backend.app.common.schemas.base import ORMBase

# category, item 전체 조회 --- start
class RestrictionItemRead(BaseModel):
    item_id: int
    item_label_ko: str
    item_label_en: str
    item_active : bool
    category_id: int

class CategoryItemRead(BaseModel):
    category_id: int
    category_label_ko: str
    category_label_en: str
    category_active : bool
    items: list[RestrictionItemRead] = []
# category, item 전체 조회 --- end

# Category, Item 등록 --- start
class ItemCreate(BaseModel):
    item_label_ko: str
    item_label_en: str

class CategoryCreate(BaseModel):
    category_label_ko: str
    category_label_en: str
    items: list[ItemCreate] = Field(default_factory=list)

class CategoriesBatchCreate(BaseModel):
    categories: list[CategoryCreate]
# Category, Item 등록 --- end

# Category, Item 수정 --- start
class CategoryUpdate(BaseModel):
    category_label_ko: str
    category_label_en: str
    category_active: bool

class ItemUpdate(BaseModel):
    item_label_ko: str
    item_label_en: str
    item_active: bool
# Category, Item 수정 --- end