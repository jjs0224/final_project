# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError
#
# from app.core.database import get_db
#
# from .schemas import category_schemas, item_schemas
# from .models import category_model, item_model
#
# # common member
#
# router = APIRouter(prefix="/restriction", tags=["restriction"])
#

# admin category, item 생성, 수정 부분
# @router.get("/admin/xxx")
# def admin_xxx(current=Depends(require_roles("ADMIN"))):

# # Category // [/restriction/category]
# @router.post("/category/", response_model=category_schemas.CategoryRead)
# def create_category(payload: category_schemas.CategoryCreate, db: Session = Depends(get_db)):
#     c = category_model.Category(**payload.model_dump())
#     db.add(c)
#     try:
#         db.commit()
#         db.refresh(c)
#         return c
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Category code already exists")
#
# @router.get("/category/{category_id}", response_model=list[category_schemas.CategoryRead])
# def list_categories(db: Session = Depends(get_db)):
#     return db.query(category_model.Category).order_by(category_model.Category.category_id.asc()).all()
#
# @router.patch("/category/{category_id}", response_model=category_schemas.CategoryUpdate)
# def update_category(category_id: int, payload: category_schemas.CategoryUpdate, db: Session = Depends(get_db)):
#     c = db.query(category_model.Category).filter(category_model.Category.category_id == category_id).first()
#     if not c:
#         raise HTTPException(status_code=404, detail="Category not found")
#
#     data = payload.model_dump(exclude_unset=True)
#     if not data:
#         return c
#
#     for k, v in data.items():
#         setattr(c, k, v)
#
#     try:
#         db.commit()
#         db.refresh(c)
#         return c
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Category code already exists")
#
#
#
# # Item // [/restriction/item]
# @router.post("/item", response_model=item_schemas.ItemRead)
# def create_item(payload: item_schemas.ItemCreate, db: Session = Depends(get_db)):
#
#     print(payload)
#     # item_label_ko='테스트1_아이템1' item_label_en='test1_i1' category_id=1
#
#     # 해당 값의 category 여부 확인
#     cat = db.query(category_model.Category).filter(
#         category_model.Category.category_id == payload.category_id).first()
#     if not cat:
#         raise HTTPException(status_code=400, detail="Invalid category_id")
#
#     item = item_model.Items(**payload.model_dump())
#     db.add(item)
#     try:
#         db.commit()
#         db.refresh(item)
#         return item
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Item code already exists")
#
# @router.get("/item", response_model=list[item_schemas.ItemRead])
# def list_items(category_id: int | None = None, db: Session = Depends(get_db)):
#     q = db.query(item_model.Items)
#     if category_id is not None:
#         q = q.filter(item_model.Items.category_id == category_id)
#     return q.order_by(item_model.Items.item_id.asc()).all()
#
# @router.patch("/item/{item_id}", response_model=item_schemas.ItemRead)
# def update_item(item_id: int, payload: item_schemas.ItemUpdate, db: Session = Depends(get_db)):
#     item = db.query(item_model.Items).filter(item_model.Items.item_id == item_id).first()
#     if not item:
#         raise HTTPException(status_code=404, detail="Item not found")
#
#     data = payload.model_dump(exclude_unset=True)
#     if not data:
#         return item
#
#     # category_id 변경 시 존재 확인
#     if "category_id" in data and data["category_id"] is not None:
#         cat = db.query(category_model.Category).filter(
#             item_model.Items.category_id == data["category_id"]
#         ).first()
#         if not cat:
#             raise HTTPException(status_code=400, detail="Invalid category_id")
#
#     for k, v in data.items():
#         setattr(item, k, v)
#
#     try:
#         db.commit()
#         db.refresh(item)
#         return item
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Item code already exists")
#
# """
# # Member // [/restriction/member]
# @router.post("/member/", response_model=member_schemas.MemberRestrictionRead)
# def add_member_restriction(payload: member_schemas.MemberRestrictionCreate, db: Session = Depends(get_db)):
#
#     # 회원가입 선 진행 후 restriction 생성 진행
#     #
#
#
#     m = db.query(member_model.MemberRestrictions).filter(member_model.MemberRestrictions.member_id == payload.member_id).first()
#     if not m:
#         raise HTTPException(status_code=400, detail="Invalid member_id")
#
#     it = db.query(member_model.RestrictionItems).filter(member_model.RestrictionItems.item_id == payload.item_id).first()
#     if not it:
#         raise HTTPException(status_code=400, detail="Invalid item_id")
#
#     mr = member_model.MemberRestrictions(**payload.model_dump())
#     db.add(mr)
#     try:
#         db.commit()
#         db.refresh(mr)
#         return mr
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Already assigned (member_id, item_id)")
#
# @router.get("/member/", response_model=list[schemas.MemberRestrictionRead])
# def list_member_restrictions(member_id: int | None = None, db: Session = Depends(get_db)):
#     q = db.query(models.MemberRestrictions)
#     if member_id is not None:
#         q = q.filter(models.MemberRestrictions.member_id == member_id)
#     return q.order_by(models.MemberRestrictions.member_restrictions_id.asc()).all()
#
# @router.delete("/member/{member_restrictions_id}")
# def delete_member_restriction(member_restrictions_id: int, db: Session = Depends(get_db)):
#     mr = db.query(models.MemberRestrictions).filter(
#         models.MemberRestrictions.member_restrictions_id == member_restrictions_id
#     ).first()
#     if not mr:
#         raise HTTPException(status_code=404, detail="Member restriction not found")
#
#     db.delete(mr)
#     db.commit()
#     return {"deleted": True, "member_restrictions_id": member_restrictions_id}
# """
#
