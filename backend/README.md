# backend 설명 및 tree 구조 안내
각 폴더의 역할

app/models/
→ DB 테이블(SQLAlchemy) 정의만 둠 (Entity 역할)

app/features/*/schemas.py
→ 요청/응답 DTO(Pydantic) (Create/Read/Update)

app/features/*/router.py
→ FastAPI 라우팅만 (최대한 얇게)

app/features/*/service.py
→ 비즈니스 로직 (닉네임 유니크 체크, item_ids replace 등)

app/common/schemas/responses.py
→ DeleteResponse 같은 공통 응답 스키마

# restrictions의 category/item/restrictions/dislike 4개
app/models/restrictions/category.py
app/models/restrictions/item.py
app/models/restrictions/dislike.py
app/models/restrictions/member_restriction.py

# 수정 로직 예상
SQLAlchemy 모델은 무조건 app/models 아래
Pydantic 스키마는 feature별 schemas.py + 공통은 common/schemas
라우터는 얇게, 로직은 service로 :: service 추가 작업중

# JWT_SECRET_KEY 생성 
PROMPT : python -c "import secrets; print(secrets.token_urlsafe(64))"

# sub: 누구토큰인지
# type: access / refresh구분
# jti: 토큰고유ID(블랙리스트핵심)
# iat: 언제발급됐는지
# exp: 언제만료되는지

# docker
## 최상위 폴더에서 실행
실행 : docker compose -f docker/redis/docker-compose.yml up -d
중지 : docker compose -f docker/redis/docker-compose.yml down

동작 확인 : docker exec -it app_redis redis-cli ping -> pong
key 확인 : docker exec -it app_redis redis-cli keys "*"

# docker 로그인 테스트
- docker exec -it app_redis redis-cli keys "refresh:*"
- docker exec -it app_redis redis-cli get "refresh:<member_id>"

# role admin/user 구분
- db member/type으로 구분 예정
- rotate 사용으로 refresh 재발급 형태 수정중