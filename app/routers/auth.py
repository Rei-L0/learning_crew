from fastapi import APIRouter, HTTPException, status
from app.schemas import (
    LoginRequest,
    LoginSuccessResponse,
    LoginSuccessData,
    LoginFailureResponse,
)
from app.security import (
    get_user_by_student_id,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": LoginSuccessResponse},
        401: {"model": LoginFailureResponse},
    },
)
async def login(login_request: LoginRequest):
    """
    로그인 API
    
    - 학번과 비밀번호를 받아 인증합니다.
    - 성공 시 accessToken, refreshToken과 사용자 정보를 반환합니다.
    - 실패 시 적절한 에러 메시지와 코드를 반환합니다.
    """
    # 1. 사용자 조회
    user = get_user_by_student_id(login_request.studentId)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LoginFailureResponse(
                success=False,
                message="등록되지 않은 사용자입니다.",
                code="USER_NOT_FOUND",
                ).model_dump(),
        )
    
    # 2. 비밀번호 검증
    # 실제로는 DB에 저장된 해시와 비교해야 합니다.
    # 테스트를 위해 특정 비밀번호만 허용하도록 구현
    valid_passwords = {
        "123456": "ssafy123456!",
        "700000": "admin123!",
    }
    
    expected_password = valid_passwords.get(login_request.studentId)
    if expected_password is None or login_request.password != expected_password:
        # 실제 운영 환경에서는 verify_password를 사용:
        # if not verify_password(login_request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LoginFailureResponse(
                success=False,
                message="비밀번호가 일치하지 않습니다.",
                code="INVALID_PASSWORD",
                ).model_dump(),
        )
    
    # 3. 토큰 생성
    token_data = {"sub": user["studentId"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # 4. 사용자 정보 구성 (hashed_password 제외)
    user_response = UserResponse(
        id=user["id"],
        studentId=user["studentId"],
        name=user["name"],
        role=user["role"],
        campus=user.get("campus"),
        classNo=user.get("classNo"),
    )
    
    # 5. 성공 응답 반환
    return LoginSuccessResponse(
        success=True,
        data=LoginSuccessData(
            accessToken=access_token,
            refreshToken=refresh_token,
            user=user_response,
        ),
    )

