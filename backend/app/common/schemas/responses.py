from pydantic import BaseModel

# 공통 schema

# api 성공시 msg response
class ApiResponse(BaseModel):
    message: str

# 삭제시 msg response
class DeleteResponse(BaseModel):
    message: str
    
# 비밀번호 수정
# PasswordChangeRequest { current_password, new_password }

# nickname 조회 / 체크
class NicknameCheckResponse(BaseModel):
    available: bool
    message: str