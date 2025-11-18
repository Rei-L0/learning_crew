import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from google import genai
from google.genai import types
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import json
import sqlite3

# --- 라이브러리 추가 ---
from typing import List, Optional
import asyncio
import os
import re  # ✨ re 임포트 확인
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

# --- FastAPI 앱 및 CORS 설정 (동일) ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB 설정 (동일) ---
DATABASE_URL = "analysis_results.db"


def init_db():
    """DB 테이블을 확인하고, 새 컬럼(campus, class_name, author_name)을 추가합니다."""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    # 1. 기본 테이블 생성
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

    # 2. 새 컬럼 추가 (존재하지 않을 경우)
    cursor.execute("PRAGMA table_info(analysis_results)")
    columns = [row[1] for row in cursor.fetchall()]

    if "campus" not in columns:
        cursor.execute("ALTER TABLE analysis_results ADD COLUMN campus TEXT")
        logger.info("DB 스키마 변경: 'campus' 컬럼 추가")
    if "class_name" not in columns:
        cursor.execute("ALTER TABLE analysis_results ADD COLUMN class_name TEXT")
        logger.info("DB 스키마 변경: 'class_name' 컬럼 추가")
    if "author_name" not in columns:
        cursor.execute("ALTER TABLE analysis_results ADD COLUMN author_name TEXT")
        logger.info("DB 스키마 변경: 'author_name' 컬럼 추가")

    conn.commit()
    conn.close()
    logger.info("데이터베이스 테이블 확인/업데이트 완료. (기존 데이터는 유지됩니다)")


# --- ✨ (수정) 파일명에서 정보 추출 (로직 대폭 수정) ---
def extract_info_from_filename(filename: str) -> dict:
    """
    파일명에서 캠퍼스, 반, 작성자 정보를 추출합니다.

    (!!! 중요 !!!)
    현재 이 함수는 파일명이 "....._[캠퍼스]_[반]_[작성자].xlsx" 형식이라고 가정합니다.
    예: "8월 스터디 활동 결과보고서_서울_1반_홍길동.xlsx"

    만약 파일명 규칙이 다르면, 이 함수의 `parts` 인덱싱 로직을 수정해야 합니다.
    """

    # (!!!) 사용자가 제공한 캠퍼스 목록 (필요시 '대전', '부울경' 등 추가)
    CAMPUS_LIST = ["광주", "구미", "서울", "대전", "부울경"]
    CLASS_REGEX = r"(\d+반)"  # "1반", "2반" ...

    try:
        name_without_ext = os.path.splitext(filename)[0]
        parts = name_without_ext.split("_")

        info = {"campus": None, "class_name": None, "author_name": None}

        # (가정) 파일명의 마지막 3개 요소가 [캠퍼스]_[반]_[작성자] 라고 가정
        if len(parts) >= 4:  # 최소 4개 파트 (e.g., "제목_서울_1반_홍길동")

            campus_candidate = parts[-3]
            class_candidate = parts[-2]
            author_candidate = parts[-1]

            # 캠퍼스 목록에 있고, '반' 형식이 맞는지 확인
            if campus_candidate in CAMPUS_LIST and re.fullmatch(
                CLASS_REGEX, class_candidate
            ):
                info["campus"] = campus_candidate
                info["class_name"] = class_candidate
                info["author_name"] = author_candidate

                logger.info(f"파일명 정보 추출 성공: {info}")
                return info

        # (대안) 위 가정이 실패하면, 파트를 순회하며 탐색 (조금 덜 정확할 수 있음)
        for part in parts:
            if part in CAMPUS_LIST:
                info["campus"] = part
            elif re.fullmatch(CLASS_REGEX, part):
                info["class_name"] = part

        # (대안) 작성자 찾기 (캠퍼스/반이 아닌 마지막 파트 추정)
        for part in reversed(parts):
            if (
                (part not in CAMPUS_LIST)
                and (not re.fullmatch(CLASS_REGEX, part))
                and ("보고서" not in part)
                and ("계획서" not in part)
            ):
                info["author_name"] = part
                break

        if info["campus"] or info["class_name"]:
            logger.warning(f"파일명 부분 추출: {filename} -> {info} (예상 구조와 다름)")
            return info

    except Exception as e:
        logger.error(f"파일명 정보 추출 중 예외 발생: {filename} (오류: {e})")

    logger.warning(
        f"파일명 정보 추출 실패: {filename} (예상 구조: ..._[캠퍼스]_[반]_[이름].xlsx)"
    )
    return {"campus": None, "class_name": None, "author_name": None}


# --- (수정) DB 저장 함수 (동일) ---
def save_result_to_db(
    filename: str,
    total_score: int,
    photo_count: int,
    analysis_json: str,
    campus: Optional[str],
    class_name: Optional[str],
    author_name: Optional[str],
):
    """분석 결과를 DB에 저장 (신규 컬럼 포함)"""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO analysis_results 
            (filename, total_score, photo_count, analysis_json, campus, class_name, author_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                total_score,
                photo_count,
                analysis_json,
                campus,
                class_name,
                author_name,
            ),
        )
        conn.commit()
        conn.close()
        logger.info(
            f"[{filename}] 결과를 DB에 저장했습니다. (정보: {campus}, {class_name}, {author_name})"
        )
    except Exception as e:
        logger.error(f"[{filename}] DB 저장 실패: {e}")


# --- FastAPI 이벤트 핸들러 (동일) ---
@app.on_event("startup")
def startup_event():
    global SYSTEM_PROMPT
    logger.info("서버 시작... 시스템 프롬프트 로드 중...")
    try:
        SYSTEM_PROMPT = file_utils.load_system_prompt(app_config.SYSTEM_PROMPT_PATH)
        logger.info("시스템 프롬프트 로드 완료")
    except Exception as e:
        logger.critical(f"서버 시작 실패: 시스템 프롬프트 로드 중 오류 발생 - {e}")
        SYSTEM_PROMPT = "ERROR: PROMPT NOT LOADED"
    init_db()


# --- read_file_content 헬퍼 함수 (동일) ---
async def read_file_content(file: UploadFile) -> str:
    content_bytes = await file.read()
    if file.filename.endswith(".xlsx"):
        file_stream = io.BytesIO(content_bytes)
        excel_data = pd.read_excel(file_stream, sheet_name=None, engine="openpyxl")
        report_content = ""
        for sheet_name, df in excel_data.items():
            report_content += f"--- 시트: {sheet_name} ---\n"
            report_content += df.to_string(index=False) + "\n\n"
        return report_content
    elif file.filename.endswith(".txt"):
        return content_bytes.decode("utf-8")
    else:
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400, detail=f"파일 디코딩 실패: {file.filename}"
            )


# --- API 호출 함수 (동일) ---
def call_gemini_api(system_prompt: str, content: str) -> str:
    if system_prompt == "ERROR: PROMPT NOT LOADED":
        raise ValueError("시스템 프롬프트가 올바르게 로드되지 않았습니다.")
    logger.info("Google AI API 호출 중 (동기)...")
    try:
        client = genai.Client(api_key=app_config.API_KEY)
        response = client.models.generate_content(
            model=app_config.API_MODEL,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=content,
        )
        return response.text
    except Exception as e:
        logger.error(f"API 호출 실패 (동기): {e}")
        raise


async def call_gemini_api_async(system_prompt: str, content: str) -> str:
    logger.info("Google AI API 비동기 래퍼 호출 중...")
    try:
        return await asyncio.to_thread(call_gemini_api, system_prompt, content)
    except Exception as e:
        logger.error(f"API 비동기 래퍼 호출 실패: {e}")
        raise


# --- get_matching_key 헬퍼 함수 (동일) ---
def get_matching_key(filename: str) -> str | None:
    try:
        name_without_ext = os.path.splitext(filename)[0]
        parts = name_without_ext.split("_")
        if len(parts) >= 3:
            return "_".join(parts[-3:])
        return None
    except Exception as e:
        logger.error(f"키 추출 중 예외 발생: {filename} - {e}")
        return None


# --- (수정) 파일 1쌍 처리 (새로운 extract_info_from_filename 호출) ---
async def process_single_pair(plan_file: UploadFile, report_file: UploadFile, key: str):
    global SYSTEM_PROMPT
    logger.info(f"[{key}] 쌍 처리 시작...")
    api_response_text = ""
    try:
        plan_content = await read_file_content(plan_file)
        report_content = await read_file_content(report_file)
        combined_content = f"[계획서]\n{plan_content}\n\n[결과보고서]\n{report_content}"
        api_response_text = await call_gemini_api_async(SYSTEM_PROMPT, combined_content)

        try:
            start_index = api_response_text.find("{")
            end_index = api_response_text.rfind("}")
            if start_index == -1 or end_index == -1 or end_index < start_index:
                raise ValueError("응답에서 유효한 JSON 객체를 찾을 수 없습니다.")

            cleaned_string = api_response_text[start_index : end_index + 1]
            data = json.loads(cleaned_string)

            total = data.get("total")
            photo_count = data.get("photo_count_detected")

            # --- ✨ (수정됨) 새로운 파서 호출 ---
            info = extract_info_from_filename(report_file.filename)

            await asyncio.to_thread(
                save_result_to_db,
                report_file.filename,
                total,
                photo_count,
                cleaned_string,
                info.get("campus"),
                info.get("class_name"),
                info.get("author_name"),
            )

        except Exception as e:
            logger.error(f"[{key}] API 응답 파싱 또는 DB 저장 실패: {e}")

        return {
            "key": key,
            "filename": report_file.filename,
            "status": "success",
            "analysis_result": api_response_text,
        }
    except Exception as e:
        logger.error(f"[{key}] 쌍 처리 중 오류: {e}")
        return {
            "key": key,
            "filename": report_file.filename,
            "status": "error",
            "error": str(e),
        }


@app.get("/")
def read_root():
    return {"message": "Gemini 분석 API 서버"}


# --- 파일 업로드 API (동일) ---
@app.post("/upload-and-analyze")
async def upload_and_analyze(
    plan_files: List[UploadFile] = File(...), report_files: List[UploadFile] = File(...)
):
    plans_map, reports_map = {}, {}
    for file in plan_files:
        if key := get_matching_key(file.filename):
            plans_map[key] = file
    for file in report_files:
        if key := get_matching_key(file.filename):
            reports_map[key] = file

    matched_keys = set(plans_map.keys()).intersection(set(reports_map.keys()))
    tasks = [
        process_single_pair(plans_map[key], reports_map[key], key)
        for key in matched_keys
    ]
    processing_results = await asyncio.gather(*tasks)

    # (요약 정보 생성 - 간단히 표기)
    summary = {
        "total_plans": len(plan_files),
        "total_reports": len(report_files),
        "matched_count": len(matched_keys),
        "unmatched_plans": [
            f.filename
            for f in plan_files
            if get_matching_key(f.filename) not in matched_keys
        ],
        "unmatched_reports": [
            f.filename
            for f in report_files
            if get_matching_key(f.filename) not in matched_keys
        ],
    }
    return {"summary": summary, "results": processing_results}


# --- 게시판 목록 API (필터링 기능) (동일) ---
@app.get("/results")
async def get_all_results(
    campus: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    """DB에 저장된 분석 결과 목록을 (필터링하여) 반환합니다."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT id, filename, total_score, created_at, campus, class_name, author_name FROM analysis_results"
        conditions = []
        params = []

        if campus:
            conditions.append("campus = ?")
            params.append(campus)
        if class_name:
            conditions.append("class_name = ?")
            params.append(class_name)
        if start_date:
            conditions.append("DATE(created_at) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(created_at) <= ?")
            params.append(end_date)
        if q:
            conditions.append("(author_name LIKE ? OR filename LIKE ?)")
            params.append(f"%{q}%")
            params.append(f"%{q}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        logger.error(f"결과 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- 필터 옵션 API (동일) ---
@app.get("/filter-options")
async def get_filter_options():
    """필터링 드롭다운에 사용할 캠퍼스 및 반 목록을 반환합니다."""
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT DISTINCT campus FROM analysis_results WHERE campus IS NOT NULL ORDER BY campus"
        )
        campuses = [row["campus"] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT class_name FROM analysis_results WHERE class_name IS NOT NULL ORDER BY class_name"
        )
        class_names = [row["class_name"] for row in cursor.fetchall()]

        conn.close()
        return {"campuses": campuses, "class_names": class_names}
    except Exception as e:
        logger.error(f"필터 옵션 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- 세부 내용 API (동일) ---
@app.get("/results/{result_id}")
async def get_result_detail(result_id: int):
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
            try:
                analysis_data = json.loads(row["analysis_json"])
            except json.JSONDecodeError:
                analysis_data = {"error": "저장된 JSON 데이터 파싱 실패"}

            return {"filename": row["filename"], "analysis_data": analysis_data}
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
