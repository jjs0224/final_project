import uuid
from fastapi import APIRouter
from backend.app.core.cache.redis import redis_client

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/redis")
def redis_health():
    conn = redis_client.connection_pool.connection_kwargs
    info = redis_client.info()

    key = f"debug:ping:{uuid.uuid4().hex[:6]}"
    redis_client.set(key, "pong", ex=120)
    val = redis_client.get(key)

    return {
        "ok": True,
        "value": val,
        "key": key,
        "host": conn.get("host"),
        "port": conn.get("port"),
        "db": conn.get("db"),
        "run_id": info.get("run_id"),
        "dbsize": redis_client.dbsize(),
    }