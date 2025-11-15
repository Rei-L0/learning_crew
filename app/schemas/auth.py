# 인증 관련 스키마
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse

# --- 1. 로그인 요청 모델 (RequestBody) ---
class LoginRequest(BaseModel):
    studentId: str = Field(..., max_length=6, pattern=r"^\d{6}$")
    password: str

# --- 2. 응답 모델 (ResponseBody) ---

# 2-1. 성공 응답의 data 객체 모델
class LoginSuccessData(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserResponse  # 위에서 정의한 UserResponse 모델 사용

# 2-2. 최종 성공 응답 (Top-level)
class LoginSuccessResponse(BaseModel):
    success: bool = True
    data: LoginSuccessData

# 2-3. 최종 실패 응답 (Top-level)
class LoginFailureResponse(BaseModel):
    success: bool = False
    message: str
    code: str  # 예: "USER_NOT_FOUND"

