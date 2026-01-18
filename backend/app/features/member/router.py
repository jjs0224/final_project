from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from . import schemas, service
from app.common.schemas import responses

router = APIRouter(prefix="/members", tags=["member"])

# 회원가입
@router.post("", status_code=201)
def create_member(payload: schemas.MemberCreate, db: Session = Depends(get_db)):
    print("회원가입 :: ", payload)
    service.create_member(db, payload)
    return {"message": "register ok"}

# MyPage 연동 - 단일 계정 
@router.get("/{member_id}", response_model=schemas.MemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)):
    print("id :: ", member_id)
    return service.get_member(db, member_id)

# MyPage 연동 - 사용자 정보 update
@router.patch("/{member_id}", response_model=schemas.MemberRead)
def update_member(member_id: int, payload: schemas.MemberUpdate, db: Session = Depends(get_db)):
    m = service.update_member(db, member_id, payload)

    # nickname / item_ids / comment만 수정!!!!!!!

    # 응답 구성은 router에서(혹은 service에서 return dict로 넘겨도 됨)
    return {
        "email": m.email,
        "nickname": m.nickname,
        "gender": m.gender,
        "country": m.country,
        "role": m.role,
        "item_ids": payload.item_ids,         # 필요하면 실제 DB에서 다시 조회해서 내려주기
        "dislike_tags": payload.dislike_tags,
    }

# MyPage 회원 탈퇴
@router.delete("/{member_id}", status_code=200)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    service.delete_member(db, member_id)
    return {"message": "member delete ok!"}


# MyPage - NickName 중복체크
@router.get("/nickname/check", response_model=responses.NicknameCheckResponse)
def nickname_check(nickname: str, db: Session = Depends(get_db)):

    # 추가 검증시 필요 로직 현재 사용 x
    # nickname: str = Query(..., min_length=2, max_length=50),

    ok = service.is_nickname_available(db, nickname)
    return {
        "available": ok,
        "message": "available" if ok else "nickname already exists",
    }