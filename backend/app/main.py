from fastapi import FastAPI, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from .api_router import api_router

# import api_router  # 공통 router 설정
app = FastAPI()

class ForceUTF8Middleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        # JSON 응답에 charset이 없으면 강제로 붙임
        if ct.startswith("application/json") and "charset=" not in ct:
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
# ForceUTF8Middleware,
#     allow_origins=["*"],
    allow_credentials=True,  # 쿠키 전송 허용
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

app.include_router(api_router)
