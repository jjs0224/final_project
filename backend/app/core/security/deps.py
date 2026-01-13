from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security.jwt import decode_token
from app.features.auth.token_store import is_blacklisted
from app.models.member import Member

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# 현재 user 인증 관련 로직
def get_current_member(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Member:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise cred_exc

        jti = payload.get("jti")
        if not jti or is_blacklisted(jti):
            raise cred_exc

        sub = payload.get("sub")
        if not sub:
            raise cred_exc
        member_id = int(sub)
    except (JWTError, ValueError, TypeError):
        raise cred_exc

    member = db.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        raise cred_exc
    return member

def require_roles(*allowed: str):
    def _checker(current=Depends(get_current_member)):
        if current.role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current
    return _checker

