# 스터디 관련 스키마
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime, date

# 팀원 모델 (API 요청/응답용)
class Member(BaseModel):
    studentId: str
    name: str
    classNo: Optional[str] = None  # 반 번호
    role: Optional[str] = None  # 역할: "LEADER" or "MEMBER"

# 스터디 생성 요청 모델
class StudyCreateRequest(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    periodStart: date
    periodEnd: date
    goal: str = Field(..., min_length=1)
    planDetails: str = Field(..., min_length=1)
    campus: str = Field(..., max_length=50)
    webexRequested: bool = False
    webexId: Optional[str] = Field(None, max_length=100)
    note: Optional[str] = None
    members: List[Member]
    status: Optional[str] = Field("SUBMITTED", pattern="^(DRAFT|SUBMITTED|CLOSED)$")
    
    @model_validator(mode='after')
    def validate_webex_id(self):
        """webexRequested가 true일 때 webexId는 필수"""
        if self.webexRequested and not self.webexId:
            raise ValueError("필수 항목 누락")
        return self
    
    @model_validator(mode='after')
    def validate_period(self):
        """periodEnd는 periodStart 이후여야 함"""
        if self.periodEnd < self.periodStart:
            raise ValueError("종료일은 시작일 이후여야 합니다")
        return self

# 스터디 생성 성공 응답 데이터
class StudyCreateData(BaseModel):
    studyId: int
    status: str  # "DRAFT", "SUBMITTED", "CLOSED"
    createdAt: datetime  # 스터디 생성일

# 스터디 생성 성공 응답
class StudyCreateSuccessResponse(BaseModel):
    success: bool = True
    data: StudyCreateData

# 스터디 생성 실패 응답
class StudyCreateFailureResponse(BaseModel):
    success: bool = False
    message: str
    code: str

# 계획서 일괄 조회용 응답 모델
class StudyListItem(BaseModel):
    studyId: int  # Id
    title: str  # 글 제목
    author: str  # 작성자
    createdAt: str  # 작성일

# 계획서 일괄 조회 응답
class StudyListResponse(BaseModel):
    success: bool = True
    data: List[StudyListItem]

# 스터디 단일 조회 응답 데이터
class StudyDetailData(BaseModel):
    studyId: int
    title: str
    description: Optional[str] = None
    periodStart: date
    periodEnd: date
    goal: str
    planDetails: str
    campus: str
    webexRequested: bool
    webexId: Optional[str] = None
    note: Optional[str] = None
    leaderUserId: int
    status: str  # "DRAFT", "SUBMITTED", "CLOSED"
    createdAt: datetime
    updatedAt: datetime
    members: List[Member]

# 스터디 단일 조회 응답
class StudyDetailResponse(BaseModel):
    success: bool = True
    data: StudyDetailData

# 스터디 업데이트 요청
class StudyUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    periodStart: Optional[date] = None
    periodEnd: Optional[date] = None
    goal: Optional[str] = Field(None, min_length=1)
    planDetails: Optional[str] = Field(None, min_length=1)
    campus: Optional[str] = Field(None, max_length=50)
    webexRequested: Optional[bool] = None
    webexId: Optional[str] = Field(None, max_length=100)
    note: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(DRAFT|SUBMITTED|CLOSED)$")

# 스터디 응답 모델 (DB 모델 매핑용)
class StudyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    periodStart: date
    periodEnd: date
    goal: str
    planDetails: str
    campus: str
    webexRequested: bool
    webexId: Optional[str] = None
    note: Optional[str] = None
    leaderUserId: int
    status: str
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True

