from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid

from jose import jwt
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

def _now() -> datetime:
    return datetime.now(timezone.utc)

# ACC TOKEN
def create_access_token(subject: str, role: str, additional_claims: Optional[dict[str, Any]] = None) -> str:
    now = _now()
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

# REFRESH TOKEN
def create_refresh_token(subject: str) -> str:
    now = _now()
    exp = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

# 사용/만료 검증
def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

# blacklist TTL 계산 사용
def exp_seconds_left(payload: dict[str, Any]) -> int:
    # jose는 exp를 timestamp(int) 또는 datetime으로 줄 수 있음. 여기선 decode 결과 exp가 보통 int로 옴.
    exp = payload.get("exp")
    now_ts = int(_now().timestamp())
    if isinstance(exp, int):
        return max(0, exp - now_ts)
    # 혹시 datetime이면
    try:
        return max(0, int(exp.timestamp()) - now_ts)
    except Exception:
        return 0