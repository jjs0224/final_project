from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/members", tags=["members"])

@router.post("", response_model=schemas.MemberRead)
def create_member(payload: schemas.MemberCreate, db: Session = Depends(get_db)):
    m = models.Member(**payload.model_dump())
    db.add(m)
    try:
        db.commit()
        db.refresh(m)
        return m
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")

@router.get("/{member_id}", response_model=schemas.MemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)):
    m = db.query(models.Member).filter(models.Member.member_id == member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m

@router.get("", response_model=list[schemas.MemberRead])
def list_members(db: Session = Depends(get_db)):
    return db.query(models.Member).order_by(models.Member.member_id.asc()).all()

@router.patch("/{member_id}", response_model=schemas.MemberRead)
def update_member(member_id: int, payload: schemas.MemberUpdate, db: Session = Depends(get_db)):
    m = db.query(models.Member).filter(models.Member.member_id == member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return m

    # 이메일 변경 시 unique 충돌 가능
    for k, v in data.items():
        setattr(m, k, v)

    try:
        db.commit()
        db.refresh(m)
        return m
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")