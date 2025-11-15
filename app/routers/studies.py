from fastapi import APIRouter, HTTPException, status, Query, Depends
from datetime import datetime, timezone
from typing import List, Optional
from app.schemas import (
    StudyCreateRequest,
    StudyCreateSuccessResponse,
    StudyCreateFailureResponse,
    StudyCreateData,
    StudyListItem,
    StudyListResponse,
    StudyDetailData,
    StudyDetailResponse,
    Member,
    UserResponse,
)
from app.security import get_current_user

router = APIRouter(prefix="/studies", tags=["studies"])


@router.get(
    "",
    response_model=StudyListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_studies(
    campus: Optional[str] = Query(None, description="지역 필터 (예: seoul, busan, gwangju)"),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    계획서 일괄 조회 API (인증 필요)
    
    - 모든 스터디 계획서 목록을 조회합니다.
    - 응답에는 작성자, 글 제목, 작성일, Id가 포함됩니다.
    - campus 쿼리 파라미터로 지역별 필터링이 가능합니다.
    - 로그인한 사용자만 접근 가능합니다.
    """
    # 실제로는 DB에서 조회하는 로직을 구현합니다.
    # 예시: studies = db.get_all_studies(campus=campus)
    
    # 가상의 데이터 (실제로는 DB에서 조회)
    # 테스트용 더미 데이터
    dummy_studies = [
        {
            "studyId": 101,
            "title": "CS 스터디",
            "author": "김싸피",
            "createdAt": "2025-01-15T10:30:00+00:00",
            "campus": "seoul",
        },
        {
            "studyId": 102,
            "title": "알고리즘 스터디",
            "author": "이싸피",
            "createdAt": "2025-01-16T14:20:00+00:00",
            "campus": "busan",
        },
        {
            "studyId": 103,
            "title": "웹 개발 스터디",
            "author": "박싸피",
            "createdAt": "2025-01-17T09:15:00+00:00",
            "campus": "seoul",
        },
        {
            "studyId": 104,
            "title": "데이터베이스 스터디",
            "author": "최싸피",
            "createdAt": "2025-01-18T11:00:00+00:00",
            "campus": "gwangju",
        },
    ]
    
    # campus 필터 적용
    if campus:
        filtered_studies = [
            study for study in dummy_studies
            if study.get("campus", "").lower() == campus.lower()
        ]
    else:
        filtered_studies = dummy_studies
    
    # StudyListItem 리스트로 변환
    study_list = [
        StudyListItem(
            studyId=study["studyId"],
            title=study["title"],
            author=study["author"],
            createdAt=study["createdAt"],
        )
        for study in filtered_studies
    ]
    
    return StudyListResponse(
        success=True,
        data=study_list,
    )


@router.get(
    "/{study_id}",
    response_model=StudyDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": StudyDetailResponse},
        404: {"description": "스터디를 찾을 수 없습니다."},
    },
)
async def get_study(
    study_id: int,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    스터디 단일 조회 API (인증 필요)
    
    - studyId로 특정 스터디의 상세 정보를 조회합니다.
    - 스터디의 모든 필드를 반환합니다.
    - 로그인한 사용자만 접근 가능합니다.
    """
    # 실제로는 DB에서 조회하는 로직을 구현합니다.
    # 예시: study = db.get_study_by_id(study_id)
    
    # 가상의 데이터 (실제로는 DB에서 조회)
    # 테스트용 더미 데이터
    dummy_studies_db = {
        101: {
            "studyId": 101,
            "title": "CS 스터디",
            "description": "자료구조와 운영체제를 정리하는 스터디입니다.",
            "periodStart": "2025-03-01",
            "periodEnd": "2025-03-31",
            "goal": "CS 기본기",
            "planDetails": "1주차: 자료구조...",
            "webexRequested": True,
            "webexId": "csstudy_team1@webex.com",
            "note": "",
            "members": [
                {"studentId": "12345678", "name": "김싸피"},
                {"studentId": "23456789", "name": "이싸피"},
            ],
        },
        102: {
            "studyId": 102,
            "title": "알고리즘 스터디",
            "description": "알고리즘 문제 풀이 스터디입니다.",
            "periodStart": "2025-03-01",
            "periodEnd": "2025-03-31",
            "goal": "알고리즘 실력 향상",
            "planDetails": "1주차: 그리디...",
            "webexRequested": False,
            "webexId": None,
            "note": "",
            "members": [
                {"studentId": "34567890", "name": "이싸피"},
            ],
        },
    }
    
    # 스터디 조회
    study_data = dummy_studies_db.get(study_id)
    
    if study_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스터디를 찾을 수 없습니다.",
        )
    
    # Member 리스트 변환
    members = [
        Member(studentId=member["studentId"], name=member["name"])
        for member in study_data["members"]
    ]
    
    # 응답 반환
    return StudyDetailResponse(
        success=True,
        data=StudyDetailData(
            studyId=study_data["studyId"],
            title=study_data["title"],
            description=study_data["description"],
            periodStart=study_data["periodStart"],
            periodEnd=study_data["periodEnd"],
            goal=study_data["goal"],
            planDetails=study_data["planDetails"],
            webexRequested=study_data["webexRequested"],
            webexId=study_data.get("webexId"),
            note=study_data.get("note", ""),
            members=members,
        ),
    )


@router.post(
    "",
    response_model=StudyCreateSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": StudyCreateSuccessResponse},
        400: {"model": StudyCreateFailureResponse},
    },
)
async def create_study(
    study_request: StudyCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    스터디 계획서 생성 API (인증 필요)
    
    - 스터디 정보와 팀원 정보를 받아 계획서를 생성합니다.
    - webexRequested가 true일 때는 webexId가 필수입니다.
    - 성공 시 studyId와 status를 반환합니다.
    - 로그인한 사용자만 접근 가능합니다.
    """
    try:
        # 실제로는 여기서 DB에 저장하는 로직을 구현합니다.
        # 예시: study_id = db.create_study(study_request)
        
        # 가상의 studyId 생성 (실제로는 DB에서 생성된 ID)
        # 간단한 예시로 현재 시간 기반 ID 생성
        import time
        study_id = int(time.time() * 1000) % 10000  # 임시 ID
        
        # 스터디 생성일 (현재 시간을 ISO 8601 형식으로)
        created_at = datetime.now(timezone.utc).isoformat()
        
        # 실제로는 여기서 DB에 저장할 때 createdAt도 함께 저장합니다.
        # 예시: db.create_study(study_request, created_at=created_at)
        
        # 성공 응답 반환
        return StudyCreateSuccessResponse(
            success=True,
            data=StudyCreateData(
                studyId=study_id,
                status="SUBMITTED",
                createdAt=created_at,
            ),
        )
    
    except ValueError as e:
        # Pydantic validation 에러 (조건부 필수 필드 등)
        error_message = str(e)
        # "필수 항목 누락" 메시지인 경우
        if "필수 항목 누락" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=StudyCreateFailureResponse(
                    success=False,
                    message="필수 항목 누락",
                    code="MISSING_FIELDS",
                ).model_dump(),
            )
        # 기타 validation 에러
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=StudyCreateFailureResponse(
                success=False,
                message=error_message,
                code="VALIDATION_ERROR",
            ).model_dump(),
        )
    except Exception as e:
        # 기타 에러
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=StudyCreateFailureResponse(
                success=False,
                message="스터디 생성 중 오류가 발생했습니다.",
                code="INTERNAL_ERROR",
            ).model_dump(),
        )

