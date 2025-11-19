# analyzer_logic.py
import os
import re
import json
import logging
import unicodedata
import asyncio
from typing import List, Optional, Callable, Awaitable

from fastapi import UploadFile, HTTPException
from google import genai
from google.genai import types
import pandas as pd
import io

# 로컬 모듈 임포트
import app_config
import db_utils  # DB 저장 함수 호출을 위해 임포트

logger = logging.getLogger(__name__)


# --- API 호출 함수 (동기 버전, to_thread로 호출될 예정) ---
def call_gemini_api(system_prompt: str, content: str) -> str:
    """Google AI API를 호출하고 응답 텍스트를 반환합니다. (동기)"""
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


# --- 파일명에서 정보 추출 (server.py에서 이동) ---
def extract_info_from_filename(filename: str) -> dict:
    """
    파일명에서 캠퍼스, 반, 작성자 정보를 추출합니다. (기존 로직 유지)
    """
    CAMPUS_LIST_RAW = ["광주", "구미", "서울", "대전", "부울경"]
    CAMPUS_LIST = [unicodedata.normalize("NFC", s) for s in CAMPUS_LIST_RAW]
    CLASS_REGEX = r"(\d+반)"

    # --- (중략) 기존 server.py의 extract_info_from_filename 함수 전체 내용 ---
    try:
        # 1. 확장자 제거
        name_without_ext = os.path.splitext(filename)[0]
        # 2. 파일명을 NFC로 정규화 (macOS NFD 호환)
        name_without_ext = unicodedata.normalize("NFC", name_without_ext)

        # 3. `_` 기준으로 분리
        parts = name_without_ext.split("_")
        logger.info(f"파일명 분리 결과: {parts}")

        info = {"campus": None, "class_name": None, "author_name": None}

        if len(parts) >= 4:
            campus_candidate = parts[-3].strip()
            class_candidate = parts[-2].strip()
            author_raw = parts[-1].strip()

            if campus_candidate in CAMPUS_LIST and re.fullmatch(
                CLASS_REGEX, class_candidate
            ):
                info["campus"] = campus_candidate
                info["class_name"] = class_candidate
                author_clean = re.split(r"[\.\s-]", author_raw, 1)[0]
                info["author_name"] = author_clean
                logger.info(f"파일명 정보 추출 성공: {info}")
                return info

        for part in parts:
            if part in CAMPUS_LIST:
                info["campus"] = part
            elif re.fullmatch(CLASS_REGEX, part):
                info["class_name"] = part

        for part in reversed(parts):
            if (
                (part not in CAMPUS_LIST)
                and (not re.fullmatch(CLASS_REGEX, part))
                and ("보고서" not in part)
                and ("계획서" not in part)
                and (".xlsx" not in part)
            ):
                info["author_name"] = part
                break

        if info["campus"] or info["class_name"]:
            logger.warning(f"파일명 부분 추출: {filename} -> {info} (예상 구조와 다름)")
            return info

    except Exception as e:
        logger.error(f"파일명 정보 추출 중 예외 발생: {filename} (오류: {e})")

    logger.warning(
        f"파일명 정보 추출 실패: {filename} (예상 구조: ..._[캠퍼스]_[반]_[이름]...)"
    )
    return {"campus": None, "class_name": None, "author_name": None}


# --- 파일 내용 읽기 (server.py에서 이동) ---
async def read_file_content(file: UploadFile) -> str:
    """UploadFile을 읽어 내용(str)을 반환 (엑셀/CSV/텍스트 지원)"""
    content_bytes = await file.read()
    filename_lower = file.filename.lower()

    if filename_lower.endswith(".xlsx"):
        logger.info(f"엑셀 파일(.xlsx) 파싱 중: {file.filename}")
        file_stream = io.BytesIO(content_bytes)
        excel_data = pd.read_excel(file_stream, sheet_name=None, engine="openpyxl")
        report_content = ""
        for sheet_name, df in excel_data.items():
            report_content += f"--- 시트: {sheet_name} ---\n"
            report_content += df.to_string(index=False) + "\n\n"
        return report_content

    elif filename_lower.endswith(".txt") or filename_lower.endswith(".csv"):
        logger.info(f"텍스트/CSV 파일(.txt/.csv) 파싱 중: {file.filename}")
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return content_bytes.decode("cp949")
            except Exception as e:
                logger.error(f"파일 디코딩 실패 (UTF-8, CP949): {file.filename} - {e}")
                raise HTTPException(
                    status_code=400, detail=f"파일 디코딩 실패: {file.filename}"
                )

    else:
        logger.warning(f"지원하지 않는 파일 형식: {file.filename}. utf-8로 시도.")
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.error(f"파일 디코딩 실패: {file.filename}")
            raise HTTPException(
                status_code=400, detail=f"파일 디코딩 실패: {file.filename}"
            )


# --- 매칭 키 추출 (server.py에서 이동) ---
def get_matching_key(filename: str) -> str | None:
    """파일명에서 매칭을 위한 키를 추출합니다. (캠퍼스_반_이름)"""
    try:
        name_without_ext = os.path.splitext(filename)[0]
        name_without_ext = unicodedata.normalize("NFC", name_without_ext)
        parts = name_without_ext.split("_")
        if len(parts) >= 3:
            return "_".join(parts[-3:])
        return None
    except Exception as e:
        logger.error(f"키 추출 중 예외 발생: {filename} - {e}")
        return None


# --- 파일 쌍/단일 파일 처리 로직 (수정됨) ---
async def process_single_pair(
    key: str,
    plan_file: Optional[UploadFile],
    report_file: Optional[UploadFile],
    system_prompt: str,
    gemini_api_caller: Callable[
        [str, str], Awaitable[str]
    ],  # 비동기 호출 함수 타입 힌트
):
    logger.info(f"[{key}] 쌍 처리 시작...")
    api_response_text = ""

    target_filename = (
        report_file.filename
        if report_file
        else (plan_file.filename if plan_file else None)
    )

    if not target_filename:
        logger.error(f"[{key}] 처리할 파일이 없습니다.")
        return {
            "key": key,
            "filename": "N/A",
            "status": "error",
            "error": "처리할 파일(계획서 또는 보고서)이 없습니다.",
        }

    try:
        # 1. 파일 내용 로드
        plan_content = ""
        if plan_file:
            plan_content = await read_file_content(plan_file)

        report_content = ""
        if report_file:
            report_content = await read_file_content(report_file)

        # 2. API 입력 내용 준비
        combined_content = ""
        if plan_content:
            combined_content += f"[계획서]\n{plan_content}\n\n"
        if report_content:
            combined_content += f"[결과보고서]\n{report_content}\n\n"

        if not combined_content:
            raise ValueError("계획서/결과보고서 파일 내용이 비어있습니다.")

        # 3. API 호출
        api_response_text = await gemini_api_caller(system_prompt, combined_content)

        try:
            # 4. JSON 파싱 및 오류 해결 (가장 바깥쪽 JSON 객체/배열 추출)
            start_index_arr = api_response_text.find("[")
            end_index_arr = api_response_text.rfind("]")

            start_index_obj = api_response_text.find("{")
            end_index_obj = api_response_text.rfind("}")

            cleaned_string = ""

            if (
                start_index_arr != -1
                and end_index_arr != -1
                and (end_index_arr - start_index_arr)
                > (end_index_obj - start_index_obj)
            ):
                cleaned_string = api_response_text[start_index_arr : end_index_arr + 1]
            elif start_index_obj != -1 and end_index_obj != -1:
                cleaned_string = api_response_text[start_index_obj : end_index_obj + 1]
            else:
                raise ValueError(
                    "응답에서 유효한 JSON 객체 또는 배열을 찾을 수 없습니다."
                )

            data = json.loads(cleaned_string)

            # ✨ 1. 단일 평가 결과 추출: 배열이면 첫 번째 객체만 추출
            data_to_save = data[0] if isinstance(data, list) and data else data

            total = data_to_save.get("total")
            photo_count = data_to_save.get("photo_count_detected")

            if total is None or photo_count is None:
                raise ValueError(
                    "JSON 응답에 'total' 또는 'photo_count_detected' 키가 누락되었습니다."
                )

            # ✨ 2. 추출한 단일 객체를 JSON 문자열로 다시 변환 (DB 저장을 위해)
            final_json_string = json.dumps(data_to_save, ensure_ascii=False)

            # 5. DB 저장
            info = extract_info_from_filename(target_filename)

            await asyncio.to_thread(
                db_utils.save_result_to_db,
                os.path.splitext(target_filename)[0],
                total,
                photo_count,
                final_json_string,  # <--- 단일 객체 JSON 문자열 저장
                info.get("campus"),
                info.get("class_name"),
                info.get("author_name"),
            )

        except Exception as e:
            logger.error(
                f"[{key}] API 응답 파싱 또는 DB 저장 실패: {e} (원본 응답 길이: {len(api_response_text)})"
            )
            return {
                "key": key,
                "filename": target_filename,
                "status": "partial_success_db_fail",
                "analysis_result": api_response_text,
                "error": f"API 응답 파싱 또는 DB 저장 실패: {e}",
            }

        return {
            "key": key,
            "filename": target_filename,
            "status": "success",
            "analysis_result": final_json_string,  # 단일 객체 JSON 문자열 반환
        }
    except Exception as e:
        logger.error(f"[{key}] 쌍 처리 중 오류: {e}")
        return {
            "key": key,
            "filename": target_filename,
            "status": "error",
            "error": str(e),
        }
