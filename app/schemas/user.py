from pydantic import BaseModel
from typing import Optional

# 1. 사용자 정보 응답 DTO (이전과 동일, 재사용)
class UserResponse(BaseModel):
    id: int
    studentId: str
    name: str
    role: str
    campus: Optional[str] = None
    classNo: Optional[str] = None

    class Config:
        from_attributes = True

# 2. 마이페이지 최종 응답 래퍼 (새로 추가)
class MyPageResponse(BaseModel):
    success: bool = True
    data: UserResponse # 👈 UserResponse DTO를 'data' 키에 중첩