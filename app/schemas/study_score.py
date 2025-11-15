# 스터디 점수 관련 스키마
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# 스터디 점수 응답
class StudyScoreResponse(BaseModel):
    id: int
    studyId: int
    planSpecificity: int = Field(..., ge=0, le=10)
    planFeasibility: int = Field(..., ge=0, le=10)
    planMeasurability: int = Field(..., ge=0, le=10)
    resultSpecificityGoal: int = Field(..., ge=0, le=10)
    teamParticipationDiversity: int = Field(..., ge=0, le=10)
    evidenceStrength: int = Field(..., ge=0, le=10)
    total: int = Field(..., ge=0, le=60)
    latePenalty: int = Field(0, ge=0, le=10)
    finalTotal: int = Field(..., ge=0, le=60)
    photoCountDetected: int = Field(0, ge=0)
    rationaleJson: Optional[Dict[str, Any]] = None
    uncertaintiesJson: Optional[Dict[str, Any]] = None
    finalComment: Optional[str] = None
    status: str  # 'NOT_SCORED', 'SCORED', 'SCORED_LATE', 'MANUALLY_ADJUSTED'
    scoredBy: Optional[str] = Field(None, pattern="^(AI|ADMIN)$")
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

# 스터디 점수 생성 요청
class StudyScoreCreateRequest(BaseModel):
    studyId: int
    planSpecificity: int = Field(..., ge=0, le=10)
    planFeasibility: int = Field(..., ge=0, le=10)
    planMeasurability: int = Field(..., ge=0, le=10)
    resultSpecificityGoal: int = Field(..., ge=0, le=10)
    teamParticipationDiversity: int = Field(..., ge=0, le=10)
    evidenceStrength: int = Field(..., ge=0, le=10)
    latePenalty: int = Field(0, ge=0, le=10)
    photoCountDetected: int = Field(0, ge=0)
    rationaleJson: Optional[Dict[str, Any]] = None
    uncertaintiesJson: Optional[Dict[str, Any]] = None
    finalComment: Optional[str] = None
    status: Optional[str] = Field("SCORED", pattern="^(NOT_SCORED|SCORED|SCORED_LATE|MANUALLY_ADJUSTED)$")
    scoredBy: Optional[str] = Field("AI", pattern="^(AI|ADMIN)$")

# 스터디 점수 업데이트 요청
class StudyScoreUpdateRequest(BaseModel):
    planSpecificity: Optional[int] = Field(None, ge=0, le=10)
    planFeasibility: Optional[int] = Field(None, ge=0, le=10)
    planMeasurability: Optional[int] = Field(None, ge=0, le=10)
    resultSpecificityGoal: Optional[int] = Field(None, ge=0, le=10)
    teamParticipationDiversity: Optional[int] = Field(None, ge=0, le=10)
    evidenceStrength: Optional[int] = Field(None, ge=0, le=10)
    latePenalty: Optional[int] = Field(None, ge=0, le=10)
    photoCountDetected: Optional[int] = Field(None, ge=0)
    rationaleJson: Optional[Dict[str, Any]] = None
    uncertaintiesJson: Optional[Dict[str, Any]] = None
    finalComment: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(NOT_SCORED|SCORED|SCORED_LATE|MANUALLY_ADJUSTED)$")
    scoredBy: Optional[str] = Field(None, pattern="^(AI|ADMIN)$")

# 스터디 점수 응답 래퍼
class StudyScoreSuccessResponse(BaseModel):
    success: bool = True
    data: StudyScoreResponse

