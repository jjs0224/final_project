from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/restriction-items", tags=["restriction-items"])

@router.post("", response_model=schemas.RestrictionItemRead)
def create_item(payload: schemas.RestrictionItemCreate, db: Session = Depends(get_db)):
    cat = db.query(models.RestrictionCategory).filter(
        models.RestrictionCategory.category_id == payload.category_id
    ).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Invalid category_id")

    item = models.RestrictionItems(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Item code already exists")

@router.get("", response_model=list[schemas.RestrictionItemRead])
def list_items(category_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.RestrictionItems)
    if category_id is not None:
        q = q.filter(models.RestrictionItems.category_id == category_id)
    return q.order_by(models.RestrictionItems.item_id.asc()).all()

@router.get("/{item_id}", response_model=schemas.RestrictionItemRead)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.RestrictionItems).filter(models.RestrictionItems.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/{item_id}", response_model=schemas.RestrictionItemRead)
def update_item(item_id: int, payload: schemas.RestrictionItemUpdate, db: Session = Depends(get_db)):
    item = db.query(models.RestrictionItems).filter(models.RestrictionItems.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return item

    # category_id 변경 시 존재 확인
    if "category_id" in data and data["category_id"] is not None:
        cat = db.query(models.RestrictionCategory).filter(
            models.RestrictionCategory.category_id == data["category_id"]
        ).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category_id")

    for k, v in data.items():
        setattr(item, k, v)

    try:
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Item code already exists")