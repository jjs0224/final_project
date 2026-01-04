from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.post("", response_model=schemas.ReviewRead)
def create_review(payload: schemas.ReviewCreate, db: Session = Depends(get_db)):
    m = db.query(models.Member).filter(models.Member.member_id == payload.member_id).first()
    if not m:
        raise HTTPException(status_code=400, detail="Invalid member_id")

    r = models.Review(**payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@router.get("", response_model=list[schemas.ReviewRead])
def list_reviews(member_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Review)
    if member_id is not None:
        q = q.filter(models.Review.member_id == member_id)
    return q.order_by(models.Review.review_id.desc()).all()

@router.get("/{review_id}", response_model=schemas.ReviewRead)
def get_review(review_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Review).filter(models.Review.review_id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    return r

@router.delete("/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Review).filter(models.Review.review_id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(r)
    db.commit()
    return {"deleted": True, "review_id": review_id}


@router.patch("/{review_id}", response_model=schemas.ReviewRead)
def update_review(review_id: int, payload: schemas.ReviewUpdate, db: Session = Depends(get_db)):
    r = db.query(models.Review).filter(models.Review.review_id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return r

    # member_id 변경 시 존재 확인
    if "member_id" in data and data["member_id"] is not None:
        m = db.query(models.Member).filter(models.Member.member_id == data["member_id"]).first()
        if not m:
            raise HTTPException(status_code=400, detail="Invalid member_id")

    for k, v in data.items():
        setattr(r, k, v)

    db.commit()
    db.refresh(r)
    return r
