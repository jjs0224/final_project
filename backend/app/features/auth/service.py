from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import hashlib

from backend.app.models.member import Member
from backend.app.core.security.password import verify_password
from backend.app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    exp_seconds_left,
)
from backend.app.core.config import REFRESH_TOKEN_EXPIRE_DAYS
from backend.app.features.auth import token_store
# 추가 예정
from backend.app.models.refresh_token import RefreshToken

# token hash 검증 추가 
def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# token exp 검증 추가
def _exp_to_dt(exp) -> datetime:
    if isinstance(exp, int):
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    return exp

# insert / update 있으면 수정 없으면 생성
def _upsert_refresh_db(db: Session, member_id: int, refresh_token: str, refresh_payload: dict) -> None:
    row = db.get(RefreshToken, member_id)
    if not row:
        row = RefreshToken(member_id=member_id)
        db.add(row)

    row.jti = refresh_payload["jti"]
    row.token_hash = _hash(refresh_token)
    row.expires_at = _exp_to_dt(refresh_payload["exp"])
    row.revoked_at = None

# 인증
def authenticate_member(db: Session, email: str, password: str) -> Member:
    member = db.query(Member).filter(Member.email == email).first()
    if not member or not verify_password(password, member.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={" WWW-Authenticate": "Bearer"},
        )
    return member

def login_issue_tokens(db: Session, email: str, password: str) -> tuple[str, str]:
    print("login token issue :: ", email, password)
    member = authenticate_member(db, email, password)

    access = create_access_token(subject=str(member.member_id), role=member.role)
    refresh = create_refresh_token(subject=str(member.member_id))

    refresh_payload = decode_token(refresh)

    # Redis 저장 (refresh:{member_id} = refresh_jti)
    token_store.save_refresh_jti(
        member.member_id,
        refresh_payload["jti"],
        exp_seconds_left(refresh_payload),  # exp 기반 TTL
    )

    # DB 저장 (refresh hash + jti)
    _upsert_refresh_db(db, member.member_id, refresh, refresh_payload)
    db.commit()

    return access, refresh


def refresh_rotate_tokens(db: Session, refresh_token: str) -> tuple[str, str]:
    # 1단계 : refresh token 자체 검증
    print("[REFRESH] incoming token head:", refresh_token[:30])
    try:
        payload = decode_token(refresh_token)
        print("[REFRESH] payload:", payload)
        if payload.get("type") != "refresh":
            print("[REFRESH] type is not refresh:", payload.get("type"))
            raise ValueError("not refresh token")
        member_id = int(payload["sub"])
        refresh_jti = payload["jti"]
    except Exception as e:
        print("[REFRESH] decode/type error:", repr(e))
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # 2단계 : redis에 저장된 refresh_jti와 비교
    saved_jti = token_store.get_refresh_jti(member_id)
    print("[REFRESH] saved_jti:", saved_jti, "req_jti:", refresh_jti)
    if not saved_jti or saved_jti != refresh_jti:

        # 저장된 refresh와 다르면 탈취/이전토큰 가능성
        token_store.delete_refresh(member_id)
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    # 3단계 : db에 저장된 refresh 토큰 비교
    row = db.get(RefreshToken, member_id)
    if (not row) or (row.revoked_at is not None):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    if row.jti != refresh_jti or row.token_hash != _hash(refresh_token):
        # 재사용/불일치 -> 강제 로그아웃 처리
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
        token_store.delete_refresh(member_id)
        raise HTTPException(status_code=401, detail="Refresh token reused")

    # 4) ROTATE: 새 access + 새 refresh 발급
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=401, detail="Member not found")

    new_access = create_access_token(subject=str(member_id), role=member.role)
    new_refresh = create_refresh_token(subject=str(member_id))
    new_refresh_payload = decode_token(new_refresh)

    # 5) 저장소 갱신 (이 시점부터 옛 refresh는 무효)
    token_store.save_refresh_jti(
        member_id,
        new_refresh_payload["jti"],
        exp_seconds_left(new_refresh_payload),
    )

    _upsert_refresh_db(db, member_id, new_refresh, new_refresh_payload)
    db.commit()

    print("refresh_rotate_tokens :: ", new_refresh)

    return new_access, new_refresh

# LOGOUT
def logout(db: Session, access_token: str) -> None:
    # acc :: blacklist, refresh 삭제 + db refresh revoke
    try:
        payload = decode_token(access_token)
        if payload.get("type") != "access":
            raise ValueError("not access token")
        jti = payload["jti"]
        member_id = int(payload["sub"])
        ttl = exp_seconds_left(payload)  # access 남은 시간만큼 blacklist 유지
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")

    # redis: access 블랙리스트
    token_store.add_to_blacklist(jti, ttl)

    # redis: refresh 제거
    token_store.delete_refresh(member_id)

    # db: refresh revoke
    row = db.get(RefreshToken, member_id)
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()