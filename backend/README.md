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

