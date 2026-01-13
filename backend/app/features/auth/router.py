from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security.deps import get_current_member, oauth2_scheme
from app.features.auth import service, schemas

router = APIRouter(prefix="/auth", tags=["auth"])

# LOGIN 
@router.post("/login", response_model=schemas.TokenPairResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print("login form :: ", form)
    access, refresh = service.login_issue_tokens(db, email=form.username, password=form.password)
    return schemas.TokenPairResponse(access_token=access, refresh_token=refresh)

# REFRESH TOKEN 재발급
@router.post("/refresh", response_model=schemas.AccessTokenResponse)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    # access = service.refresh_access_token(payload.refresh_token)
    # return schemas.AccessTokenResponse(access_token=access)

    # refresh token db 저장 로직 추가!
    access, refresh = service.refresh_rotate_tokens(db, payload.refresh_token)
    print("acc :: ", access, "  refresh :: ", refresh)
    return schemas.TokenPairResponse(access_token=access, refresh_token=refresh)

# LOGOUT
@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # service.logout(token)
    
    # logout refresh token 삭제 로직 추가!
    service.logout(db, token)
    return {"ok": True}

# 현재 USER 정보
@router.get("/me")
def me(current=Depends(get_current_member)):
    return {
        "member_id": current.member_id,
        "email": current.email,
        "nickname": current.nickname,
    }

# redis test
from fastapi import APIRouter
from app.core.cache.redis import redis_client

# router = APIRouter(prefix="/debug", tags=["debug"])
#
# @router.get("/redis")
# def redis_health():
#     try:
#         redis_client.set("debug:ping", "pong", ex=30)
#         v = redis_client.get("debug:ping")
#         return {"redis": "ok", "value": v}
#     except Exception as e:
#         return {"redis": "fail", "error": str(e)}