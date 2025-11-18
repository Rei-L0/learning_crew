import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from google import genai
from google.genai import types
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import json
import sqlite3

# --- 라이브러리 추가 ---
from typing import List
import asyncio
import os
from datetime import datetime

# 로컬 모듈 임포트
import app_config
import file_utils

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
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "null",
]  # "null" origin 추가 (HTML 파일 로컬 실행시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 편의를 위해 모두 허용 (실제 배포시에는 origins 리스트 사용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ✨ DB 설정 ---
DATABASE_URL = "analysis_results.db"


def init_db():
    """데이터베이스 테이블 초기화"""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        total_score INTEGER,
        photo_count INTEGER,
        analysis_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    )
    conn.commit()
    conn.close()
    logger.info("데이터베이스 테이블 초기화 완료.")


def save_result_to_db(
    filename: str, total_score: int, photo_count: int, analysis_json: str
):
    """분석 결과를 DB에 저장 (동기 함수)"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analysis_results (filename, total_score, photo_count, analysis_json)
            VALUES (?, ?, ?, ?)
            """,
            (filename, total_score, photo_count, analysis_json),
        )
        conn.commit()
        conn.close()
        logger.info(f"[{filename}] 결과를 DB에 저장했습니다.")
    except Exception as e:
        logger.error(f"[{filename}] DB 저장 실패: {e}")


# --- 전역 변수: 시스템 프롬프트 ---
SYSTEM_PROMPT = ""


# --- FastAPI 이벤트 핸들러: 서버 시작 시 ---
@app.on_event("startup")
def startup_event():
    """서버 시작 시 시스템 프롬프트 로드 및 DB 초기화"""
    global SYSTEM_PROMPT
    logger.info("서버 시작... 시스템 프롬프트 로드 중...")
    try:
        SYSTEM_PROMPT = file_utils.load_system_prompt(app_config.SYSTEM_PROMPT_PATH)
        logger.info("시스템 프롬프트 로드 완료")
    except Exception as e:
        logger.critical(f"서버 시작 실패: 시스템 프롬프트 로드 중 오류 발생 - {e}")
        SYSTEM_PROMPT = "ERROR: PROMPT NOT LOADED"

    # --- ✨ DB 초기화 호출 ---
    init_db()


# --- read_file_content 헬퍼 함수 (동일) ---
async def read_file_content(file: UploadFile) -> str:
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


# --- 동기 API 호출 함수 (원본 유지) ---
def call_gemini_api(system_prompt: str, content: str) -> str:
    if system_prompt == "ERROR: PROMPT NOT LOADED":
        logger.error("시스템 프롬프트가 로드되지 않아 API 호출을 중단합니다.")
        raise ValueError("시스템 프롬프트가 올바르게 로드되지 않았습니다.")

    logger.info("Google AI API 호출 중 (동기)...")
    try:
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


# --- 비동기 API 호출 래퍼 함수 ---
async def call_gemini_api_async(system_prompt: str, content: str) -> str:
    logger.info("Google AI API 비동기 래퍼 호출 중...")
    try:
        response_text = await asyncio.to_thread(call_gemini_api, system_prompt, content)
        logger.info("API 비동기 래퍼 호출 성공")
        return response_text
    except Exception as e:
        logger.error(f"API 비동기 래퍼 호출 실패: {e}")
        raise


# --- 파일명에서 매칭 키 추출 헬퍼 함수 (동일) ---
def get_matching_key(filename: str) -> str | None:
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


# --- ✨ (수정) 파일 1쌍 처리 및 DB 저장 ---
async def process_single_pair(plan_file: UploadFile, report_file: UploadFile, key: str):
    """
    계획서/보고서 파일 1쌍을 읽고 API를 호출하여 결과를 dict로 반환하고 DB에 저장합니다.
    """
    global SYSTEM_PROMPT
    logger.info(f"[{key}] 쌍 처리 시작...")
    api_response_text = ""
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

        # 3. 비동기 API 래퍼 호출
        api_response_text = await call_gemini_api_async(SYSTEM_PROMPT, combined_content)

        # 4. ✨ (신규) 서버 사이드에서 JSON 파싱 및 DB 저장
        try:
            start_index = api_response_text.find("{")
            end_index = api_response_text.rfind("}")
            if start_index == -1 or end_index == -1 or end_index < start_index:
                raise ValueError("응답에서 유효한 JSON 객체를 찾을 수 없습니다.")

            cleaned_string = api_response_text[start_index : end_index + 1]
            data = json.loads(cleaned_string)  # JSON 유효성 검사

            total = data.get("total")
            photo_count = data.get("photo_count_detected")

            # DB 저장을 별도 스레드에서 실행
            await asyncio.to_thread(
                save_result_to_db,
                report_file.filename,
                total,
                photo_count,
                cleaned_string,  # 파싱된 원본 JSON 문자열 저장
            )

        except Exception as e:
            # DB 저장이나 파싱에 실패하더라도, 클라이언트에게는 원본 응답을 보내도록 함
            logger.error(f"[{key}] API 응답 파싱 또는 DB 저장 실패: {e}")
            # 이 오류가 치명적이지 않도록, 성공 응답을 그대로 반환

        logger.info(f"[{key}] 쌍 처리 성공")
        # 성공 시 결과 반환 (클라이언트는 기존 로직대로 파싱)
        return {
            "key": key,
            "filename": report_file.filename,
            "status": "success",
            "analysis_result": api_response_text,
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


# --- 파일 업로드 API (로깅 강화됨, 원본 유지) ---
@app.post("/upload-and-analyze")
async def upload_and_analyze(
    plan_files: List[UploadFile] = File(...), report_files: List[UploadFile] = File(...)
):
    logger.info(
        f"다중 파일 수신: [계획서] {len(plan_files)}개, [결과보고서] {len(report_files)}개"
    )
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
            plans_map[key] = file
    for file in report_files:
        key = get_matching_key(file.filename)
        if key:
            reports_map[key] = file

    # 2. 매칭된 쌍 / 매칭 실패한 파일 분류
    plan_keys = set(plans_map.keys())
    report_keys = set(reports_map.keys())
    matched_keys = plan_keys.intersection(report_keys)
    unmatched_plan_keys = plan_keys - report_keys
    unmatched_report_keys = report_keys - plan_keys
    unmatched_plan_filenames = [plans_map[key].filename for key in unmatched_plan_keys]
    unmatched_report_filenames = [
        reports_map[key].filename for key in unmatched_report_keys
    ]

    logger.info("--- 파일 분류(매칭) 결과 ---")
    logger.info(f"  > 매칭 성공 (API 시도 대상): {len(matched_keys)}건")
    if unmatched_plan_filenames:
        logger.warning(
            f"  > 매칭 실패 (계획서) [{len(unmatched_plan_filenames)}건]: {unmatched_plan_filenames}"
        )
    if unmatched_report_filenames:
        logger.warning(
            f"  > 매칭 실패 (보고서) [{len(unmatched_report_filenames)}건]: {unmatched_report_filenames}"
        )

    # 3. 비동기 작업 생성
    tasks = [
        process_single_pair(plans_map[key], reports_map[key], key)
        for key in matched_keys
    ]

    # 4. 모든 작업을 비동기로 동시 실행
    processing_results = await asyncio.gather(*tasks)

    # ... (API 처리 결과 요약 로깅 - 원본 유지) ...

    # 5. 최종 결과 JSON 구성
    summary = {
        "total_plans": len(plan_files),
        "total_reports": len(report_files),
        "matched_count": len(matched_keys),
        "unmatched_plans": unmatched_plan_filenames,
        "unmatched_reports": unmatched_report_filenames,
    }
    return {"summary": summary, "results": processing_results}


# --- ✨ (신규) 게시판 API 엔드포인트 ---


@app.get("/results")
async def get_all_results():
    """DB에 저장된 모든 분석 결과 목록을 반환합니다 (간단한 정보)."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능하도록 설정
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename, total_score, created_at FROM analysis_results ORDER BY created_at DESC"
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        logger.error(f"결과 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.get("/results/{result_id}")
async def get_result_detail(result_id: int):
    """특정 ID의 세부 분석 결과를 반환합니다 (전체 JSON 포함)."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT filename, analysis_json FROM analysis_results WHERE id = ?",
            (result_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            # 클라이언트가 JS에서 JSON.parse()를 두 번 하지 않도록,
            # 서버에서 미리 JSON 문자열을 파싱하여 객체로 반환합니다.
            try:
                analysis_data = json.loads(row["analysis_json"])
            except json.JSONDecodeError:
                analysis_data = {"error": "저장된 JSON 데이터 파싱 실패"}

            return {
                "filename": row["filename"],
                "analysis_data": analysis_data,  # 'analysis_json' 대신 'analysis_data' (객체)
            }
        else:
            raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"결과 세부 조회 실패 (ID: {result_id}): {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app", host="127.0.0.1", port=8000, reload=True, log_level="info"
    )
