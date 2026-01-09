from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.common.models.member import Member
from . import schemas

# common schema
from app.common.schemas.common import DeleteResponse

# restrictions_member 생성
from app.features.restrictions.models import MemberRestrictions, Items


router = APIRouter(prefix="/members", tags=["member"])


# 관리자 계정 생성 // 26/01/08 - 추후 개발 예정
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
    try:
        with db.begin():  # 트랜잭션 시작 (성공=commit / 실패=rollback)

            # 1) member 생성
            member_data = payload.model_dump(exclude={"item_ids"})
            member = Member(**member_data)
            db.add(member)

            # 2) commit 전에 PK 뽑기
            db.flush()  # 회원가입 계정 member_id 추출

            orgMemberId = member.member_id

            # 3) item 검증 (IN 한방 + 차집합)
            req_ids = set(payload.item_ids or []) # item_ids 값이 없으면 []
            if req_ids:
                found_ids = set(
                    db.execute(
                        select(Items.item_id).where(Items.item_id.in_(req_ids))
                    ).scalars().all()
                )
                # item_ids 값이 item에 없는 경우
                missing = sorted(req_ids - found_ids)
                if missing:
                    raise HTTPException(
                        status_code=400,
                        detail={"message": "invalid item_ids", "missing_item_ids": missing},
                    )

            # 4) restrictions 저장 (중복 제거 추천)
            rows = [
                MemberRestrictions(member_id=orgMemberId, item_id=i)
                for i in sorted(req_ids)
            ]
            db.add_all(rows)

        # 여기까지 예외 없이 끝나면 자동 commit 완료

    except IntegrityError as e:
        # with db.begin() 안에서 IntegrityError가 나면 자동 rollback 됨
        raise HTTPException(status_code=409, detail="email already exists")

    result = schemas.MemberRegisterRead(
        email=member.email,
        nickname=member.nickname,
        gender=member.gender,
        country=member.country,
        item_ids=payload.item_ids,
    )

    print("RETURN RESULT:", result.model_dump())
    return result

# MyPage 연동 - 단일 계정 
@router.get("/{member_id}", response_model=schemas.MemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)):
    print(member_id)

    stmt = select(Member).where(Member.member_id == member_id)
    m = db.execute(stmt).scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return m

# 회원 전체 조회 사용 여부 체크 // 현재 미필요
# @router.get("", response_model=list[schemas.MemberRead])
# def list_members(db: Session = Depends(get_db)):
#     return db.query(Member).order_by(Member.member_id.asc()).all()

# MyPage 연동 - 사용자 정보 update
@router.patch("/{member_id}", response_model=schemas.MemberRegisterRead)
def update_member(member_id: int, payload: schemas.MemberRegisterCreate, db: Session = Depends(get_db)):

    print("넘어온 data == > ", payload)
    print("넘어온 memberId == > ", member_id)



    # 수정시 기존 ibs
    # payload.item_ids

    # stmt = select(Member).where(Member.member_id == member_id)
    # # m = db.
    # print(m.mem)
    # # m = db.query(Member).filter(Member.member_id == member_id).first()
    # if not m:
    #     raise HTTPException(status_code=404, detail="Member not found")
    #
    # data = payload.model_dump(exclude_unset=True)
    # if not data:
    #     return m
    #
    # # 이메일 변경 시 unique 충돌 가능
    # for k, v in data.items():
    #     setattr(m, k, v)
    #
    # try:
    #     db.commit()
    #     db.refresh(m)
    #     return m
    # except IntegrityError:
    #     db.rollback()
    #     raise HTTPException(status_code=409, detail="Email already exists")

# MyPage 회원 탈퇴
@router.delete("/{member_id}", response_model=DeleteResponse)
def delete_members(member_id: int, db: Session = Depends(get_db)):

    print("넘어온 memebrId ==> ", member_id)

    # 계정 정보 체크
    m = db.get(Member, member_id)

    db.delete(m)
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    # member_id로 item_ids 조회 및 삭제 처리
    # 2) member_id로 item_ids 전체 조회
    item_ids = db.execute(
        select(MemberRestrictions.item_id)
        .where(MemberRestrictions.member_id == member_id)
    ).scalars().all()

    print("item_ids 값 :: ", item_ids)

    # 3) restrictions 전체 삭제 (한 방)
    db.execute(
        delete(MemberRestrictions)
        .where(MemberRestrictions.member_id == member_id)
    )

    # 4) member 삭제
    db.delete(m)
    db.commit()

    # 계정 삭제 및 회원 탈퇴 정보 table 이동 1년 보관 로직
    # 추후 어떻게 구현할지 회의 필요

    return {"message": "member delete ok!"}