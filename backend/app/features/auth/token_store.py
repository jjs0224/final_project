from backend.app.core.cache.redis import redis_client

def refresh_key(member_id: int) -> str:
    return f"refresh:{member_id}"

def blacklist_key(jti: str) -> str:
    return f"bl:{jti}"

def save_refresh_jti(member_id: int, refresh_jti: str, ttl_seconds: int) -> None:
    key = f"refresh:{member_id}"
    print("[REDIS] SET", key, refresh_jti, ttl_seconds)  # ✅ 임시
    redis_client.set(refresh_key(member_id), refresh_jti, ex=ttl_seconds)

def get_refresh_jti(member_id: int) -> str | None:
    return redis_client.get(refresh_key(member_id))

def delete_refresh(member_id: int) -> None:
    redis_client.delete(refresh_key(member_id))

# redis acc token 관리
def add_to_blacklist(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    redis_client.set(blacklist_key(jti), "1", ex=ttl_seconds)

def is_blacklisted(jti: str) -> bool:
    return redis_client.exists(blacklist_key(jti)) == 1