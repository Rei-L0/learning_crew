from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.schemas import (
    StudyResultResponse,
    StudyResultCreateRequest,
    StudyResultUpdateRequest,
    StudyResultSuccessResponse,
    UserResponse,
)
from app.security import get_current_user

router = APIRouter(prefix="/study-results", tags=["study-results"])


@router.get(
    "/{study_id}",
    response_model=StudyResultSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": StudyResultSuccessResponse},
        404: {"description": "Study result not found"},
    },
)
async def get_study_result(
    study_id: int,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get study result by study_id
    
    Requires authentication.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Study result not found",
    )


@router.post(
    "",
    response_model=StudyResultSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": StudyResultSuccessResponse},
        400: {"description": "Bad request"},
        409: {"description": "Result already exists"},
    },
)
async def create_study_result(
    result_request: StudyResultCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Create study result
    
    Requires authentication.
    Only one result per study allowed.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.put(
    "/{study_id}",
    response_model=StudyResultSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": StudyResultSuccessResponse},
        404: {"description": "Study result not found"},
    },
)
async def update_study_result(
    study_id: int,
    result_request: StudyResultUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Update study result by study_id
    
    Requires authentication.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.delete(
    "/{study_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Study result deleted"},
        404: {"description": "Study result not found"},
    },
)
async def delete_study_result(
    study_id: int,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Delete study result by study_id
    
    Requires authentication.
    Admin only.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )
