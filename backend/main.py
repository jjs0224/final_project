from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from .database import engine
from . import models
from .routers import auth

from .routers import (
    members,
    restriction_categories,
    restriction_items,
    member_restrictions,
    reviews,
    communities,
)

app = FastAPI(title="Backend API")


class ForceUTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        # JSON 응답에 charset이 없으면 강제로 붙임
        if ct.startswith("application/json") and "charset=" not in ct:
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response

app.add_middleware(ForceUTF8Middleware)
# 개발 단계에서는 유지 추천 (이미 DB에 테이블 있으면 없어도 됨)
# models.Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(members.router)
app.include_router(restriction_categories.router)
app.include_router(restriction_items.router)
app.include_router(member_restrictions.router)
app.include_router(reviews.router)
app.include_router(communities.router)
app.include_router(auth.router)
