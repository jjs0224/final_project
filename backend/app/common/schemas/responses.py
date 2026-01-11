from pydantic import BaseModel

# 공통 schema

# 삭제시 msg response
class DeleteResponse(BaseModel):
    message: str