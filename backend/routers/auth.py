# backend/routers/auth.py
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models
from ..auth import verify_password, create_access_token

from ..auth import get_current_member
from .. import schemas

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.email == payload.email).first()

    # 계정 유추 방지: email 없음/비번 틀림을 동일 메시지로 처리
    if not member or not verify_password(payload.password, member.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(member.member_id))
    return TokenResponse(access_token=token)

@router.get("/me", response_model=schemas.MemberRead)
def me(current=Depends(get_current_member)):
    return current