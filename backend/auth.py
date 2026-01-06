# backend/auth.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models


# bcrypt 설정
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정 (.env로 주입 권장)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME__PLEASE_SET_ENV")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(plain_password: str) -> str:
    """평문 비밀번호를 bcrypt 해시로 변환"""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """평문 비밀번호와 저장된 해시를 비교"""
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(
    subject: str,
    expires_minutes: Optional[int] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    JWT Access Token 생성
    - subject: 보통 member_id를 문자열로 넣는 것을 권장
    """
    now = datetime.now(timezone.utc)
    exp_minutes = expires_minutes if expires_minutes is not None else ACCESS_TOKEN_EXPIRE_MINUTES
    expire = now + timedelta(minutes=exp_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """JWT 디코딩 (검증 실패 시 예외)"""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def get_current_member(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Member:
    """Authorization: Bearer <token> 기반 현재 로그인 사용자 로드"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # sub에는 member_id를 문자열로 넣는 것을 권장했으므로 int 변환
    try:
        member_id = int(sub)
    except ValueError:
        raise credentials_exception

    member = (
        db.query(models.Member)
        .filter(models.Member.member_id == member_id)
        .first()
    )
    if not member:
        raise credentials_exception
    return member
