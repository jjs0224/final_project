# backend/routers/auth.py
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from ..database import get_db
from .. import models, schemas
from ..auth import verify_password, create_access_token, get_current_member

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _authenticate_member(db: Session, email: str, password: str) -> models.Member:
    member = db.query(models.Member).filter(models.Member.email == email).first()

    # 계정 유추 방지: email 없음/비번 틀림을 동일 메시지로 처리
    if not member or not verify_password(password, member.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return member


@router.post("/login", response_model=TokenResponse, summary="OAuth2 Password login (Swagger Authorize용)")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Swagger UI의 OAuth2 Password Flow(Authorize 버튼)가 호출하는 엔드포인트.
    - Content-Type: application/x-www-form-urlencoded
    - Field: username, password

    여기서는 username 값을 'email'로 사용합니다.
    """
    email = form_data.username  # Swagger는 username 필드로 보냄
    password = form_data.password

    member = _authenticate_member(db, email=email, password=password)
    token = create_access_token(subject=str(member.member_id))
    return TokenResponse(access_token=token)


@router.post("/login-json", response_model=TokenResponse, summary="JSON login (기존 클라이언트/프론트용)")
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    기존에 JSON 바디로 로그인하던 클라이언트/프론트 호환용.
    - Content-Type: application/json
    - Body: { "email": "...", "password": "..." }
    """
    member = _authenticate_member(db, email=payload.email, password=payload.password)
    token = create_access_token(subject=str(member.member_id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=schemas.MemberRead)
def me(current=Depends(get_current_member)):
    return current
