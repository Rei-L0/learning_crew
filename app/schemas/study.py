# 스터디 관련 스키마
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List

# 팀원 모델
class Member(BaseModel):
    studentId: str
    name: str
    classNo: Optional[str] = None  # 반 번호
    role: Optional[str] = None  # 역할: "LEADER" or "MEMBER"

# 스터디 생성 요청 모델
class StudyCreateRequest(BaseModel):
    title: str
    description: str
    periodStart: str
    periodEnd: str
    goal: str
    planDetails: str
    webexRequested: bool
    webexId: Optional[str] = None
    note: Optional[str] = None
    campus: str  # 지역 (필수)
    members: List[Member]
    
    @model_validator(mode='after')
    def validate_webex_id(self):
        """webexRequested가 true일 때 webexId는 필수"""
        if self.webexRequested and not self.webexId:
            raise ValueError("필수 항목 누락")
        return self

# 스터디 생성 성공 응답 데이터
class StudyCreateData(BaseModel):
    studyId: int
    status: str  # "SUBMITTED"
    createdAt: str  # 스터디 생성일 (ISO 8601 형식)

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
    description: str
    periodStart: str
    periodEnd: str
    goal: str
    planDetails: str
    webexRequested: bool
    webexId: Optional[str] = None
    note: Optional[str] = None
    members: List[Member]

# 스터디 단일 조회 응답
class StudyDetailResponse(BaseModel):
    success: bool = True
    data: StudyDetailData

# 스터디 응답 모델 (기존 유지)
class StudyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    maxParticipants: Optional[int] = None
    
    class Config:
        from_attributes = True

