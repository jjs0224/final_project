# backend/routers/members.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from .. import models, schemas
from ..auth import hash_password, get_current_member


router = APIRouter(prefix="/members", tags=["members"])


@router.post("", response_model=schemas.MemberRead)
def create_member(payload: schemas.MemberCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()

    # 비밀번호 해시 저장
    if "password" in data and data["password"]:
        data["password"] = hash_password(data["password"])

    m = models.Member(**data)
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
def update_member(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),  # ✅ 인증(로그인) 필수
):
    # ✅ 본인만 수정 가능
    if current.member_id != member_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own account",
        )

    m = db.query(models.Member).filter(models.Member.member_id == member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return m

    # 비밀번호 변경이면 해시 저장
    if "password" in data and data["password"]:
        data["password"] = hash_password(data["password"])

    for k, v in data.items():
        setattr(m, k, v)

    try:
        db.commit()
        db.refresh(m)
        return m
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
