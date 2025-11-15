# 스터디 참여자 관련 스키마
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 스터디 참여자 응답
class StudyParticipantResponse(BaseModel):
    id: int
    studyId: int
    userId: int
    role: str  # 'LEADER' or 'MEMBER'
    classNoSnapshot: Optional[str] = None
    createdAt: datetime

    class Config:
        from_attributes = True

# 스터디 참여자 생성 요청
class StudyParticipantCreateRequest(BaseModel):
    studyId: int
    userId: int
    role: str = Field(..., pattern="^(LEADER|MEMBER)$")
    classNoSnapshot: Optional[str] = Field(None, max_length=20)

# 스터디 참여자 업데이트 요청
class StudyParticipantUpdateRequest(BaseModel):
    role: Optional[str] = Field(None, pattern="^(LEADER|MEMBER)$")
    classNoSnapshot: Optional[str] = Field(None, max_length=20)

