from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 1. 사용자 정보 응답 DTO
class UserResponse(BaseModel):
    id: int
    studentId: str
    name: str
    role: str  # 'STUDENT' or 'ADMIN'
    campus: Optional[str] = None
    classNo: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True

# 2. 사용자 생성 요청 (관리자용)
class UserCreateRequest(BaseModel):
    studentId: str = Field(..., max_length=20)
    name: str = Field(..., max_length=50)
    role: str = Field(..., pattern="^(STUDENT|ADMIN)$")
    campus: str = Field(..., max_length=50)
    classNo: Optional[str] = Field(None, max_length=20)
    password: str = Field(..., min_length=1)

# 3. 사용자 업데이트 요청
class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    role: Optional[str] = Field(None, pattern="^(STUDENT|ADMIN)$")
    campus: Optional[str] = Field(None, max_length=50)
    classNo: Optional[str] = Field(None, max_length=20)
    password: Optional[str] = None

# 4. 마이페이지 최종 응답 래퍼
class MyPageResponse(BaseModel):
    success: bool = True
    data: UserResponse