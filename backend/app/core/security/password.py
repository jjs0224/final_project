from passlib.context import CryptContext
import traceback

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 비밀번호  hash :: 변환
def hash_password(plain_password: str) -> str:

    try:
        print("HASH INPUT bytes:", len(str(plain_password).encode("utf-8")))
        return _pwd_context.hash(plain_password)
    except Exception as e:
        print("HASH ERROR:", repr(e))
        traceback.print_exc()
        traceback.print_stack(limit=20)
        raise


    # return _pwd_context.hash(plain_password)

# 비밀번호  verify :: 복원
def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)