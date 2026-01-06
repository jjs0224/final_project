from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/restriction-categories", tags=["restriction-categories"])

@router.post("", response_model=schemas.RestrictionCategoryRead)
def create_category(payload: schemas.RestrictionCategoryCreate, db: Session = Depends(get_db)):
    c = models.RestrictionCategory(**payload.model_dump())
    db.add(c)
    try:
        db.commit()
        db.refresh(c)
        return c
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category label_en already exists")

@router.get("", response_model=list[schemas.RestrictionCategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.RestrictionCategory).order_by(models.RestrictionCategory.category_id.asc()).all()

@router.get("/{category_id}", response_model=schemas.RestrictionCategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)):
    c = db.query(models.RestrictionCategory).filter(models.RestrictionCategory.category_id == category_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")
    return c

@router.patch("/{category_id}", response_model=schemas.RestrictionCategoryRead)
def update_category(category_id: int, payload: schemas.RestrictionCategoryUpdate, db: Session = Depends(get_db)):
    c = db.query(models.RestrictionCategory).filter(models.RestrictionCategory.category_id == category_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Category not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return c

    for k, v in data.items():
        setattr(c, k, v)

    try:
        db.commit()
        db.refresh(c)
        return c
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category label_en already exists")