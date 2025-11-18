import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from google import genai
from google.genai import types
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

# --- ✨ 라이브러리 추가 ---
from typing import List
import asyncio  # ✨ asyncio 임포트 확인 (to_thread 사용)
import os

# 로컬 모듈 임포트
import app_config
import file_utils

# --- ✨ (수정) 로깅 설정 추가 ---
# Uvicorn이 실행하더라도, 파이썬의 기본 로거를 설정합니다.
# 이것이 main.py에만 있고 server.py에는 없었기 때문에 INFO 로그가 무시되었습니다.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# --- 수정 끝 ---

# --- 로깅 설정 (동일) ---
logger = logging.getLogger(__name__)

# --- FastAPI 앱 및 CORS 설정 (동일) ---
app = FastAPI()
origins = ["http://127.0.0.1:5500", "http://localhost:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- read_file_content 헬퍼 함수 (동일) ---
async def read_file_content(file: UploadFile) -> str:
    # ... (기존 코드와 동일) ...
    content_bytes = await file.read()
    if file.filename.endswith(".xlsx"):
        logger.info(f"엑셀 파일(.xlsx) 파싱 중: {file.filename}")
        file_stream = io.BytesIO(content_bytes)
        excel_data = pd.read_excel(file_stream, sheet_name=None, engine="openpyxl")
        report_content = ""
        for sheet_name, df in excel_data.items():
            report_content += f"--- 시트: {sheet_name} ---\n"
            report_content += df.to_string(index=False) + "\n\n"
        return report_content
    elif file.filename.endswith(".txt"):
        logger.info(f"텍스트 파일(.txt) 파싱 중: {file.filename}")
        return content_bytes.decode("utf-8")
    else:
        logger.warning(f"지원하지 않는 파일 형식: {file.filename}. utf-8로 시도.")
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.error(f"파일 디코딩 실패: {file.filename}")
            raise HTTPException(
                status_code=400, detail=f"파일 디코딩 실패: {file.filename}"
            )


# --- ✨ 전역 변수: 시스템 프롬프트 ---
SYSTEM_PROMPT = ""
# API_MODEL 변수는 제거


# --- ✨ FastAPI 이벤트 핸들러: 서버 시작 시 (수정) ---
@app.on_event("startup")
def startup_event():
    """서버 시작 시 시스템 프롬프트 로드"""
    global SYSTEM_PROMPT
    logger.info("서버 시작... 시스템 프롬프트 로드 중...")
    try:
        SYSTEM_PROMPT = file_utils.load_system_prompt(app_config.SYSTEM_PROMPT_PATH)
        logger.info("시스템 프롬프트 로드 완료")

        # --- ❌ 오류가 발생한 API 모델 초기화 코드 제거 ---
        # genai.configure(api_key=app_config.API_KEY)  <-- 제거
        # API_MODEL = genai.GenerativeModel(...)       <-- 제거
        # -----------------------------------------------

    except Exception as e:
        # ✨ 오류 메시지 수정
        logger.critical(f"서버 시작 실패: 시스템 프롬프트 로드 중 오류 발생 - {e}")
        SYSTEM_PROMPT = "ERROR: PROMPT NOT LOADED"


# --- 기존 동기 API 호출 함수 (원본 유지) ---
def call_gemini_api(system_prompt: str, content: str) -> str:
    """(동기) Google AI API를 호출하고 응답 텍스트를 반환합니다."""

    if system_prompt == "ERROR: PROMPT NOT LOADED":
        logger.error("시스템 프롬프트가 로드되지 않아 API 호출을 중단합니다.")
        raise ValueError("시스템 프롬프트가 올바르게 로드되지 않았습니다.")

    logger.info("Google AI API 호출 중 (동기)...")
    try:
        # app_config에서 API_KEY를 가져옵니다.
        client = genai.Client(api_key=app_config.API_KEY)
        response = client.models.generate_content(
            model=app_config.API_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
            contents=content,
        )
        logger.info("API 호출 성공 (동기)")
        return response.text
    except Exception as e:
        logger.error(f"API 호출 실패 (동기): {e}")
        raise


# --- ✨ (수정) 비동기 API 호출 래퍼 함수 ---
async def call_gemini_api_async(system_prompt: str, content: str) -> str:
    """
    (비동기 래퍼) 동기 API 호출 함수를 별도 스레드에서 실행합니다.
    (FastAPI 이벤트 루프 차단 방지)
    """
    logger.info("Google AI API 비동기 래퍼 호출 중...")
    try:
        # ✨ asyncio.to_thread를 사용해 동기 함수를 비동기로 실행
        response_text = await asyncio.to_thread(call_gemini_api, system_prompt, content)
        logger.info("API 비동기 래퍼 호출 성공")
        return response_text
    except Exception as e:
        logger.error(f"API 비동기 래퍼 호출 실패: {e}")
        raise


# --- 파일명에서 매칭 키 추출 헬퍼 함수 (동일) ---
def get_matching_key(filename: str) -> str | None:
    # ... (기존 코드와 동일) ...
    try:
        name_without_ext = os.path.splitext(filename)[0]
        parts = name_without_ext.split("_")
        if len(parts) >= 3:
            key = "_".join(parts[-3:])
            return key
        else:
            logger.warning(f"키 추출 실패: {filename} (파일명에 '_'가 2개 미만)")
            return None
    except Exception as e:
        logger.error(f"키 추출 중 예외 발생: {filename} - {e}")
        return None


# --- ✨ (수정) 파일 1쌍을 비동기로 처리하는 헬퍼 함수 ---
async def process_single_pair(plan_file: UploadFile, report_file: UploadFile, key: str):
    """
    계획서/보고서 파일 1쌍을 읽고 API를 호출하여 결과를 dict로 반환합니다.
    """
    global SYSTEM_PROMPT  # ✨ 전역 시스템 프롬프트를 사용
    logger.info(f"[{key}] 쌍 처리 시작...")
    try:
        # 1. 파일 내용 비동기로 읽기
        plan_content = await read_file_content(plan_file)
        report_content = await read_file_content(report_file)

        # 2. 프롬프트 조합
        combined_content = f"""
        [제출된 계획서 내용]
        {plan_content}

        [제출된 결과보고서 내용]
        {report_content}
        """

        # 3. ✨ 수정된 비동기 API 래퍼 호출 (SYSTEM_PROMPT 전달)
        api_response = await call_gemini_api_async(SYSTEM_PROMPT, combined_content)

        logger.info(f"[{key}] 쌍 처리 성공")
        # 성공 시 결과 반환
        return {
            "key": key,
            "filename": report_file.filename,
            "status": "success",
            "analysis_result": api_response,
        }
    except Exception as e:
        logger.error(f"[{key}] 쌍 처리 중 오류: {e}")
        # 실패 시 에러 정보 반환
        return {
            "key": key,
            "filename": report_file.filename,
            "status": "error",
            "error": str(e),
        }


@app.get("/")
def read_root():
    return {"message": "Gemini 분석 API 서버가 실행 중입니다."}


# --- 파일 업로드 API (✨ 로깅 강화) ---
@app.post("/upload-and-analyze")
async def upload_and_analyze(
    plan_files: List[UploadFile] = File(...), report_files: List[UploadFile] = File(...)
):
    logger.info(
        f"다중 파일 수신: [계획서] {len(plan_files)}개, [결과보고서] {len(report_files)}개"
    )

    # --- (로그) 수신된 파일명 전체 로깅 ---
    plan_filenames = [file.filename for file in plan_files]
    report_filenames = [file.filename for file in report_files]
    logger.info(f"  > 수신된 계획서 목록: {plan_filenames}")
    logger.info(f"  > 수신된 보고서 목록: {report_filenames}")

    # 1. 파일 매칭
    plans_map = {}
    reports_map = {}
    for file in plan_files:
        key = get_matching_key(file.filename)
        if key:
            if key in plans_map:
                logger.warning(f"  > 중복 키 (계획서): {key} (파일: {file.filename})")
            plans_map[key] = file
    for file in report_files:
        key = get_matching_key(file.filename)
        if key:
            if key in reports_map:
                logger.warning(f"  > 중복 키 (보고서): {key} (파일: {file.filename})")
            reports_map[key] = file

    # 2. 매칭된 쌍 / 매칭 실패한 파일 분류
    plan_keys = set(plans_map.keys())
    report_keys = set(reports_map.keys())
    matched_keys = plan_keys.intersection(report_keys)
    unmatched_plan_keys = plan_keys - report_keys
    unmatched_report_keys = report_keys - plan_keys

    # (summary 딕셔너리에서 사용할 리스트를 미리 생성)
    unmatched_plan_filenames = [plans_map[key].filename for key in unmatched_plan_keys]
    unmatched_report_filenames = [
        reports_map[key].filename for key in unmatched_report_keys
    ]

    # --- (로그) 분류 결과 상세 로깅 ---
    logger.info("--- 파일 분류(매칭) 결과 ---")
    logger.info(f"  > 매칭 성공 (API 시도 대상): {len(matched_keys)}건")
    if matched_keys:
        logger.info(f"    > 성공 키: {list(matched_keys)}")

    if unmatched_plan_filenames:
        logger.warning(
            f"  > 매칭 실패 (계획서) [{len(unmatched_plan_filenames)}건]: {unmatched_plan_filenames}"
        )
    else:
        logger.info("  > 매칭 실패 (계획서): 0건")

    if unmatched_report_filenames:
        logger.warning(
            f"  > 매칭 실패 (보고서) [{len(unmatched_report_filenames)}건]: {unmatched_report_filenames}"
        )
    else:
        logger.info("  > 매칭 실패 (보고서): 0건")
    logger.info("-----------------------------")

    # 3. 비동기 작업 생성 (process_single_pair 호출)
    tasks = []
    for key in matched_keys:
        tasks.append(process_single_pair(plans_map[key], reports_map[key], key))

    # 4. 모든 작업을 비동기로 동시 실행
    processing_results = await asyncio.gather(*tasks)

    # --- ✨ (로그 추가) API 처리 결과 요약 로깅 ---
    success_count = 0
    failed_count = 0
    failed_keys = []

    # 'processing_results' 리스트를 순회하며 결과 집계
    for result in processing_results:
        if result["status"] == "success":
            success_count += 1
        else:
            failed_count += 1
            # .get()을 사용하여 'key'가 없는 예외 상황에도 안전하게 처리
            failed_keys.append(result.get("key", "Unknown"))

    logger.info("--- API 처리(쌍) 결과 요약 ---")
    logger.info(f"  > 총 시도: {len(matched_keys)}건")
    logger.info(f"  > 처리 성공: {success_count}건")

    if failed_count > 0:
        # 실패 건수는 ERROR 레벨로 로깅하여 눈에 띄게 함
        logger.error(f"  > 처리 실패: {failed_count}건")
        logger.error(f"    > 실패 키: {failed_keys}")
    else:
        logger.info(f"  > 처리 실패: 0건")
    logger.info("-----------------------------")
    # --- ✨ 로그 추가 끝 ---

    # 5. 최종 결과 JSON 구성
    summary = {
        "total_plans": len(plan_files),
        "total_reports": len(report_files),
        "matched_count": len(matched_keys),
        "unmatched_plans": unmatched_plan_filenames,
        "unmatched_reports": unmatched_report_filenames,
    }
    return {"summary": summary, "results": processing_results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app", host="127.0.0.1", port=8000, reload=True, log_level="info"
    )
