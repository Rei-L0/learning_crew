from fastapi import APIRouter, Depends
from ..schemas.user import UserResponse, MyPageResponse
from ..security import get_current_user # 👈 (핵심) 인증 의존성 import

router = APIRouter(prefix="/users", tags=["users"])

@router.get(
    "/me", # 👈 (main.py의 prefix와 합쳐져 /api/users/me가 됨)
    response_model=MyPageResponse # 👈 최종 응답 모델 지정
)
async def get_my_page_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    마이페이지 정보를 조회합니다. (인증 필요)
    
    FastAPI가 이 함수를 실행하기 '전에'
    1. 'Depends(get_current_user)'를 먼저 실행합니다.
    2. 'get_current_user'가 토큰을 검증하고 'UserResponse' 객체를 반환합니다.
    3. FastAPI가 그 객체를 'current_user' 매개변수에 넣어줍니다.
    
    (만약 토큰이 없거나 유효하지 않으면 'get_current_user'가
    HTTP 401 에러를 발생시키므로, 이 함수 본문은 아예 실행되지 않습니다.)
    """
    
    # 'current_user'는 이미 'get_current_user'가 반환해 준
    # 인증된 사용자의 정보입니다.
    # 이 정보를 'MyPageResponse' 형식에 맞게 반환합니다.
    return MyPageResponse(data=current_user)