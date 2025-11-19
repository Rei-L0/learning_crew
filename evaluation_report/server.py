import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
import asyncio
from typing import List, Optional

# 로컬 모듈 임포트
import app_config
import file_utils

# ✨ 신규 임포트
import db_utils
import analyzer_logic


# --- 로깅 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- FastAPI 앱 및 CORS 설정 ---
app = FastAPI()
# ✨ 프론트엔드 출처 (Origin)를 명시적으로 추가합니다.
origins = [
    "http://127.0.0.1",
    "http://127.0.0.1:5500",  # 프론트엔드 개발 서버 포트
    "http://localhost",
    "http://localhost:5500",
    "*",  # 와일드카드는 다른 모든 경우를 위해 유지
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 수정된 origins 리스트 사용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- FastAPI 이벤트 핸들러 (DB 초기화) ---
@app.on_event("startup")
def startup_event():
    global SYSTEM_PROMPT
    logger.info("서버 시작... 시스템 프롬프트 로드 및 DB 초기화 중...")
    try:
        # file_utils.load_system_prompt는 file_utils.py에 그대로 둡니다.
        SYSTEM_PROMPT = file_utils.load_system_prompt(app_config.SYSTEM_PROMPT_PATH)
        logger.info("시스템 프롬프트 로드 완료")
    except Exception as e:
        logger.critical(f"서버 시작 실패: 시스템 프롬프트 로드 중 오류 발생 - {e}")
        SYSTEM_PROMPT = "ERROR: PROMPT NOT LOADED"

    # ✨ db_utils의 init_db 호출
    db_utils.init_db()


# --- API 호출 비동기 래퍼 함수 (Gemini API 호출 함수는 analyzer_logic.py로 이동) ---
async def call_gemini_api_async(system_prompt: str, content: str) -> str:
    logger.info("Google AI API 비동기 래퍼 호출 중...")
    try:
        # ✨ analyzer_logic의 동기 함수를 스레드에서 실행
        return await asyncio.to_thread(
            analyzer_logic.call_gemini_api, system_prompt, content
        )
    except Exception as e:
        logger.error(f"API 비동기 래퍼 호출 실패: {e}")
        raise


@app.get("/")
def read_root():
    return {"message": "Gemini 분석 API 서버"}


# --- (수정) 파일 업로드 API ---
@app.post("/upload-and-analyze")
async def upload_and_analyze(
    plan_files: List[UploadFile] = File(...), report_files: List[UploadFile] = File(...)
):
    plans_map, reports_map = {}, {}
    all_keys = set()

    # ✨ analyzer_logic.get_matching_key 사용
    for file in plan_files:
        if key := analyzer_logic.get_matching_key(file.filename):
            plans_map[key] = file
            all_keys.add(key)

    for file in report_files:
        if key := analyzer_logic.get_matching_key(file.filename):
            reports_map[key] = file
            all_keys.add(key)

    tasks = []
    for key in all_keys:
        # ✨ analyzer_logic.process_single_pair 호출 (SYSTEM_PROMPT 및 call_gemini_api_async 전달)
        tasks.append(
            analyzer_logic.process_single_pair(
                key,
                plans_map.get(key),
                reports_map.get(key),
                SYSTEM_PROMPT,
                call_gemini_api_async,
            )
        )

    processing_results = await asyncio.gather(*tasks)

    processed_keys = set(
        item.get("key") for item in processing_results if item.get("key")
    )

    summary = {
        "total_plans": len(plan_files),
        "total_reports": len(report_files),
        "processed_count": len(processed_keys),
        "unmatchable_plans": [
            f.filename
            for f in plan_files
            if analyzer_logic.get_matching_key(f.filename) not in all_keys
        ],
        "unmatchable_reports": [
            f.filename
            for f in report_files
            if analyzer_logic.get_matching_key(f.filename) not in all_keys
        ],
    }
    return {"summary": summary, "results": processing_results}


# --- 게시판 목록 API (필터링 기능) ---
@app.get("/results")
async def get_all_results(
    campus: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    # ✨ db_utils의 get_all_results 호출
    try:
        results = db_utils.get_all_results(campus, class_name, start_date, end_date, q)
        return results
    except Exception as e:
        logger.error(f"결과 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- 필터 옵션 API ---
@app.get("/filter-options")
async def get_filter_options():
    # ✨ db_utils의 get_filter_options 호출
    try:
        options = db_utils.get_filter_options()
        return options
    except Exception as e:
        logger.error(f"필터 옵션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- 세부 내용 API ---
@app.get("/results/{result_id}")
async def get_result_detail(result_id: int):
    # ✨ db_utils의 get_result_detail 호출
    try:
        return db_utils.get_result_detail(result_id)
    except Exception as e:
        logger.error(f"결과 세부 조회 실패 (ID: {result_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app", host="127.0.0.1", port=8000, reload=True, log_level="info"
    )
