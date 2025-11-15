# 스터디 결과 관련 스키마
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# 스터디 결과 응답
class StudyResultResponse(BaseModel):
    id: int
    studyId: int
    resultGoal: str
    activityDetail: str
    resultText: str
    photoUrls: Optional[List[str]] = None
    status: str  # 'NOT_SUBMITTED', 'SUBMITTED', 'LATE_SUBMITTED'
    submittedAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        from_attributes = True

# 스터디 결과 생성 요청
class StudyResultCreateRequest(BaseModel):
    studyId: int
    resultGoal: str = Field(..., min_length=1)
    activityDetail: str = Field(..., min_length=1)
    resultText: str = Field(..., min_length=1)
    photoUrls: Optional[List[str]] = None
    status: Optional[str] = Field("SUBMITTED", pattern="^(NOT_SUBMITTED|SUBMITTED|LATE_SUBMITTED)$")

# 스터디 결과 업데이트 요청
class StudyResultUpdateRequest(BaseModel):
    resultGoal: Optional[str] = Field(None, min_length=1)
    activityDetail: Optional[str] = Field(None, min_length=1)
    resultText: Optional[str] = Field(None, min_length=1)
    photoUrls: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(NOT_SUBMITTED|SUBMITTED|LATE_SUBMITTED)$")

# 스터디 결과 응답 래퍼
class StudyResultSuccessResponse(BaseModel):
    success: bool = True
    data: StudyResultResponse

