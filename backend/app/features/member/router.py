from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.common.models.member import Member
from . import schemas

# restrictions_member 생성
from app.features.restrictions.models import MemberRestrictions


router = APIRouter(prefix="/members", tags=["member"])


# 관리자 계정 생성
@router.post("/admin", response_model=schemas.MemberRead)
def create_admin(payload: schemas.MemberCreate, db: Session = Depends(get_db)):
    m = Member(**payload.model_dump())
    db.add(m)
    try:
        db.commit()
        db.refresh(m)
        return m
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")

# 일반 유저 계정 생성
@router.post("", response_model=schemas.MemberRegisterRead)
def create_member(payload: schemas.MemberRegisterCreate, db: Session = Depends(get_db)):
    print(payload)
    print(payload.item_ids)

    member_data = payload.model_dump(exclude={"item_ids"})
    member = Member(**member_data)
    print(member)

    db.add(member)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        print("IntegrityError:", e)
        raise HTTPException(status_code=409, detail="email already exists")

    db.refresh(member)

    # 현재 등록 회원 ID값 추출 및 사용자 추가 ids
    orgMemberId = member.member_id
    items = payload.item_ids

    print(orgMemberId)

    # item 검증 [데이터 여부 확인]
    
    # category 검증 [데이터 여부 확인]
    
    # item, category ok => 실제 member_restrictions 추가
    row = [MemberRestrictions(member_id=orgMemberId, item_id=i) for i in items]

    db.add_all(row)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        print("IntegrityError:", e)
        raise HTTPException(status_code=409, detail="restrictions create err")

    result = schemas.MemberRegisterRead(
        email=member.email,
        nickname=member.nickname,
        gender=member.gender,
        country=member.country,
        item_ids=payload.item_ids,
    )

    print("RETURN RESULT:", result.model_dump())
    return result

@router.get("/{member_id}", response_model=schemas.MemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)):
    print(member_id)
    m = db.query(Member).filter(Member.member_id == member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return m

@router.get("", response_model=list[schemas.MemberRead])
def list_members(db: Session = Depends(get_db)):
    return db.query(Member).order_by(Member.member_id.asc()).all()

@router.patch("/{member_id}", response_model=schemas.MemberRegisterRead)
def update_member(member_id: int, payload: schemas.MemberRegisterCreate, db: Session = Depends(get_db)):

    # 수정시 기존 ibs
    # payload.item_ids

    m = db.query(Member).filter(Member.member_id == member_id).first()
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

@router.delete("/{member_id}", response_model=list[schemas.MemberRead])
def delete_members(member_id: int, db: Session = Depends(get_db)):
    m = db.query(Member).filter(Member.member_id == member_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(m)
    db.commit()
    return {"message": "member delete ok!"}
