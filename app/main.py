# 1. FastAPI 클래스를 import합니다.
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.schemas.study import StudyCreateFailureResponse

# 라우터들을 import합니다.
from app.routers import auth, users, studies, study_results, study_scores

# 2. FastAPI 앱 인스턴스(객체)를 생성합니다.
# 이 'app' 변수가 uvicorn이 실행할 대상입니다.
app = FastAPI()

# Pydantic validation 에러를 커스텀 형식으로 변환
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic validation 에러를 커스텀 형식으로 변환"""
    errors = exc.errors()
    for error in errors:
        # "필수 항목 누락" 메시지가 있는 경우
        if "필수 항목 누락" in str(error.get("msg", "")):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=StudyCreateFailureResponse(
                    success=False,
                    message="필수 항목 누락",
                    code="MISSING_FIELDS",
                ).model_dump(),
            )
    # 기타 validation 에러는 기본 형식 유지
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )

# 라우터들을 앱에 포함시킵니다. (모든 라우터에 /api prefix 적용)
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(studies.router, prefix="/api")
app.include_router(study_results.router, prefix="/api")
app.include_router(study_scores.router, prefix="/api")

# 3. 경로(path) 연산(operation) 데코레이터를 사용합니다.
# @app.get("/")는 HTTP "GET" 메소드로
# "/" 경로에 대한 요청을 처리한다는 의미입니다.
@app.get("/")
def read_root():
    # 4. 이 함수는 요청이 오면 호출되며,
    # 반환하는 딕셔너리가 JSON 응답으로 자동 변환됩니다.
    return {"Hello": "World"}

