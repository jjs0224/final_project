# from pydantic import BaseModel
# from app.models import ORMBase
# from typing import Optional
#
# class CategoryCreate(BaseModel):
#     category_label_ko: str
#     category_label_en: str
#
# class CategoryRead(ORMBase):
#     category_id: int
#     category_label_ko: str
#     category_label_en: str
#
# class CategoryUpdate(BaseModel):
#     category_label: Optional[str] = None
#     category_code: Optional[str] = None
#
# class ItemCreate(BaseModel):
#     item_label_ko: str
#     item_label_en: str
#     category_id: int
#
# class ItemRead(ORMBase):
#     item_id: int
#     item_label_ko: str
#     item_label_en: str
#     category_id: int
#
# class ItemUpdate(BaseModel):
#     item_label: Optional[str] = None
#     item_code: Optional[str] = None
#     category_id: Optional[int] = None
#
# class MemberRestrictionCreate(BaseModel):
#     member_id: int
#     item_id: int
#
# class MemberRestrictionRead(ORMBase):
#     member_restrictions_id: int
#     member_id: int
#     item_id: int
#
