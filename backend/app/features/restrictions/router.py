from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.core.security.deps import require_admin
from backend.app.core.database import get_db

from . import schemas, service
from backend.app.models.restrictions import Category, Item

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin 관리자 Category, Item 초기 등록, 사용중 Update API

# Category, Item list 조회
@router.get("/restrictions", response_model=list[schemas.CategoryItemRead], dependencies=[Depends(require_admin)],)
def admin_restrictions(db: Session = Depends(get_db)):
    print("router db ::", db)
    return service.get_categories_with_items(db)

# Category, Item 전체 등록
@router.post("/restrictions/batch", dependencies=[Depends(require_admin)],)
def create_categories_batch(payload: schemas.CategoriesBatchCreate, db: Session = Depends(get_db)):
    print("payload :: ", payload)
    return service.create_categories_batch(db, payload)

# Category 수정
@router.put("/restrictions/category/{category_id}", response_model=dict, dependencies=[Depends(require_admin)],)
def update_category(category_id: int, payload: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    print("category id :: ", category_id)
    print("payload :: ", payload)
    return service.update_category(db, category_id, payload)

# Item 수정
@router.put("/restrictions/item/{item_id}", response_model=dict, dependencies=[Depends(require_admin)], )
def update_item(item_id: int, payload: schemas.ItemUpdate, db: Session = Depends(get_db)):
    return service.update_item(db, item_id, payload)