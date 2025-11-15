from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from app.schemas import (
    StudyScoreResponse,
    StudyScoreCreateRequest,
    StudyScoreUpdateRequest,
    StudyScoreSuccessResponse,
    UserResponse,
)
from app.security import get_current_user

router = APIRouter(prefix="/study-scores", tags=["study-scores"])


@router.get(
    "/{study_id}",
    response_model=StudyScoreSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": StudyScoreSuccessResponse},
        404: {"description": "Study score not found"},
    },
)
async def get_study_score(
    study_id: int,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Get study score by study_id
    
    Requires authentication.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Study score not found",
    )


@router.post(
    "",
    response_model=StudyScoreSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": StudyScoreSuccessResponse},
        400: {"description": "Bad request"},
        409: {"description": "Score already exists"},
    },
)
async def create_study_score(
    score_request: StudyScoreCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Create study score
    
    Requires authentication.
    Only one score per study allowed.
    Total and finalTotal are calculated automatically.
    Admin or AI system only.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.put(
    "/{study_id}",
    response_model=StudyScoreSuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": StudyScoreSuccessResponse},
        404: {"description": "Study score not found"},
    },
)
async def update_study_score(
    study_id: int,
    score_request: StudyScoreUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Update study score by study_id
    
    Requires authentication.
    Total and finalTotal are recalculated automatically.
    Admin only.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.delete(
    "/{study_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Study score deleted"},
        404: {"description": "Study score not found"},
    },
)
async def delete_study_score(
    study_id: int,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Delete study score by study_id
    
    Requires authentication.
    Admin only.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )
