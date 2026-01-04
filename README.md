# Local MySQL (Docker Compose) + Schema/Seed 자동 초기화

이 저장소는 `docker-compose.yml`로 **MySQL 컨테이너를 띄우고**, `db/schema.sql` 및 `db/seed.sql`을 **최초 1회 자동 실행**하도록 구성되어 있습니다.

## 1) 요구사항
- Docker Desktop 설치 (Windows/Mac) 또는 Docker Engine (Linux)
- `docker compose` 명령 사용 가능

## 2) 원클릭 실행
프로젝트 루트(= `docker-compose.yml`이 있는 위치)에서 아래 한 줄만 실행하세요.

```bash
docker compose up -d
```

컨테이너 상태 확인:
```bash
docker ps
```

로그 확인:
```bash
docker logs -f app_mysql
```

> 처음 실행 시 `mysql_data` 볼륨이 비어 있으므로,
> `./db`의 `schema.sql`, `seed.sql`이 자동으로 실행됩니다.

## 3) 접속 정보
- Host: `127.0.0.1`
- Port: `3306`
- Database: `app_db`
- Root:
  - user: `root`
  - password: `rootpassword`
- App user:
  - user: `app_user`
  - password: `app_password`

예) MySQL CLI로 접속:
```bash
mysql -h 127.0.0.1 -P 3306 -u app_user -papp_password app_db
```

## 4) 초기화(주의)
`schema.sql/seed.sql`은 **MySQL 데이터 디렉토리가 비어 있을 때만(= 최초 1회)** 실행됩니다.

스키마/시드를 다시 적용하려면 아래처럼 볼륨을 삭제하고 재시작하세요.

```bash
docker compose down -v
docker compose up -d
```

## 5) 파일 설명
- `db/schema.sql` : 테이블/제약조건(FK/INDEX/UNIQUE) 포함 스키마
- `db/seed.sql`   : 초기 데이터(예시). 필요에 따라 수정/확장

## 6) 자주 겪는 이슈
### A) 포트 충돌(3306)
이미 로컬에 MySQL이 3306을 사용 중이면 충돌이 납니다. 이 경우 `docker-compose.yml`에서 포트를 변경하세요.

예:
```yaml
ports:
  - "3307:3306"
```
그럼 접속도 3307로 합니다.

### B) seed 수정했는데 반영이 안 됨
볼륨에 데이터가 남아 있으면 init 스크립트가 다시 실행되지 않습니다.
`docker compose down -v`로 볼륨 삭제 후 재실행하세요.

---

## 7) FastAPI(로컬)에서 Compose MySQL에 연결하기

### 7.1 Python 패키지 설치
FastAPI + SQLAlchemy + MySQL 드라이버 + dotenv 로더를 설치합니다.

```bash
pip install fastapi uvicorn sqlalchemy pymysql python-dotenv
```

> 이미 설치되어 있다면 생략 가능합니다.

### 7.2 .env 생성
프로젝트 루트에 `.env.example`이 있으니, 이를 복사해 `.env`를 만듭니다.

- mac/linux
```bash
cp .env.example .env
```

- windows(cmd)
```bat
copy .env.example .env
```

`.env`의 값은 docker-compose.yml의 설정과 일치하도록 기본으로 채워져 있습니다:
- DB_USER=app_user
- DB_PASSWORD=app_password
- DB_NAME=app_db

### 7.3 backend/database.py 수정(환경변수 기반 DATABASE_URL)
아래처럼 `DATABASE_URL`을 하드코딩하지 말고 `.env`를 읽어 구성하세요.

```python
# backend/database.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 프로젝트 루트의 .env 로드 (backend/ 아래에서 실행해도 동작)
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "app_password")

# 단일 문자열을 쓰고 싶으면 .env에 DATABASE_URL을 직접 설정해도 됩니다.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 7.4 실행 순서(완전 재현)
1) MySQL 컨테이너 실행(스키마/시드 최초 1회 자동 적용)
```bash
docker compose up -d
```

2) FastAPI 실행
```bash
uvicorn backend.main:app --reload
```

3) 확인
- Swagger: http://127.0.0.1:8000/docs
- DB 연결 확인: MySQL에 member/restriction_category 등 테이블이 생성되어 있어야 합니다.

### 7.5 흔한 실수
- **.env를 커밋하지 마세요**: 비밀번호가 들어갈 수 있으므로 `.gitignore`에 포함했습니다.
- **포트 충돌**: 로컬 MySQL이 3306을 사용 중이면 compose 포트를 바꾸고 `.env`의 DB_PORT도 맞춰야 합니다.
