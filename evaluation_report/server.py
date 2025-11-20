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

origins = [
    "http://127.0.0.1",
    "http://127.0.0.1:5500",
    "http://localhost",
    "http://localhost:5500",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
        SYSTEM_PROMPT = file_utils.load_system_prompt(app_config.SYSTEM_PROMPT_PATH)
        logger.info("시스템 프롬프트 로드 완료")
    except Exception as e:
        logger.critical(f"서버 시작 실패: 시스템 프롬프트 로드 중 오류 발생 - {e}")
        SYSTEM_PROMPT = "ERROR: PROMPT NOT LOADED"

    db_utils.init_db()


# --- API 호출 비동기 래퍼 함수 ---
async def call_gemini_api_async(system_prompt: str, content: str) -> str:
    logger.info("Google AI API 비동기 래퍼 호출 중...")
    try:
        return await asyncio.to_thread(
            analyzer_logic.call_gemini_api, system_prompt, content
        )
    except Exception as e:
        logger.error(f"API 비동기 래퍼 호출 실패: {e}")
        raise


# --- ✨ [신규] API 속도 제한(Rate Limit) 처리를 위한 세마포어 및 래퍼 ---
# 동시에 1개의 작업만 수행하도록 제한 (무료 티어 한계 극복용)
api_semaphore = asyncio.Semaphore(1)

SLEEP_TIME = 6


async def process_with_rate_limit(
    key, plan_file, report_file, system_prompt, gemini_caller
):
    """
    세마포어를 사용하여 API 호출 빈도를 제어하는 래퍼 함수입니다.
    작업 완료 후 6초 대기하여 분당 요청 횟수(RPM) 제한을 준수합니다.
    """
    async with api_semaphore:
        try:
            logger.info(f"[{key}] 속도 제한 래퍼 진입. 처리 시작...")
            result = await analyzer_logic.process_single_pair(
                key, plan_file, report_file, system_prompt, gemini_caller
            )

            # ✨ API 호출 후 6초 강제 대기 (Gemini Free Tier: 약 10 RPM)
            logger.info(f"[{key}] API 호출 완료. Rate Limit 준수를 위해 6초 대기...")
            await asyncio.sleep(SLEEP_TIME)

            return result
        except Exception as e:
            logger.error(f"[{key}] 처리 중 예외 발생: {e}")
            return {
                "key": key,
                "filename": (
                    report_file.filename
                    if report_file
                    else (plan_file.filename if plan_file else "unknown")
                ),
                "status": "error",
                "error": str(e),
            }


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
        # ✨ 기존 process_single_pair 대신 process_with_rate_limit 사용
        tasks.append(
            process_with_rate_limit(
                key,
                plans_map.get(key),
                reports_map.get(key),
                SYSTEM_PROMPT,
                call_gemini_api_async,
            )
        )

    # 모든 작업 비동기 실행 (세마포어에 의해 순차적으로 실행됨)
    processing_results = await asyncio.gather(*tasks)

    processed_keys = set(
        item.get("key")
        for item in processing_results
        if item.get("key") and item.get("status") != "error"
    )

    summary = {
        "total_plans": len(plan_files),
        "total_reports": len(report_files),
        "processed_count": len(processing_results),  # 시도한 전체 쌍의 개수
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


# --- 게시판 목록 API ---
@app.get("/results")
async def get_all_results(
    campus: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    try:
        results = db_utils.get_all_results(campus, class_name, start_date, end_date, q)
        return results
    except Exception as e:
        logger.error(f"결과 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- 필터 옵션 API ---
@app.get("/filter-options")
async def get_filter_options():
    try:
        options = db_utils.get_filter_options()
        return options
    except Exception as e:
        logger.error(f"필터 옵션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- 세부 내용 API ---
@app.get("/results/{result_id}")
async def get_result_detail(result_id: int):
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
