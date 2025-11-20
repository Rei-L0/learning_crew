# analyzer_logic.py
import os
import re
import json
import logging
import unicodedata
import asyncio
from typing import List, Optional, Callable, Awaitable
import io
import zipfile

from fastapi import UploadFile, HTTPException
from google import genai
from google.genai import types
import pandas as pd
from openpyxl import load_workbook

# 로컬 모듈 임포트
import app_config
import db_utils

logger = logging.getLogger(__name__)


# --- ZIP 구조 기반 이미지 카운팅 함수 ---
def count_images_in_excel(file_bytes: bytes) -> int:
    """
    엑셀 파일(.xlsx)을 ZIP으로 열어 'xl/media/' 폴더 내의 이미지 파일 개수를 직접 셉니다.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            media_files = [
                f
                for f in z.namelist()
                if f.startswith("xl/media/") and not f.endswith("/")
            ]
            count = len(media_files)
            logger.info(f"ZIP 구조 분석 결과 이미지 발견: {count}개 ({media_files})")
            return count
    except zipfile.BadZipFile:
        logger.warning("파일이 올바른 ZIP(XLSX) 형식이 아닙니다.")
        return 0
    except Exception as e:
        logger.warning(f"이미지 카운팅 중 오류 발생: {e}")
        return 0


# --- API 호출 함수 (동기) ---
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


# --- 파일명에서 정보 추출 ---
def extract_info_from_filename(filename: str) -> dict:
    CAMPUS_LIST_RAW = ["광주", "구미", "서울", "대전", "부울경"]
    CAMPUS_LIST = [unicodedata.normalize("NFC", s) for s in CAMPUS_LIST_RAW]
    CLASS_REGEX = r"(\d+반)"

    try:
        name_without_ext = os.path.splitext(filename)[0]
        name_without_ext = unicodedata.normalize("NFC", name_without_ext)
        parts = name_without_ext.split("_")

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

        return info

    except Exception as e:
        logger.error(f"파일명 정보 추출 중 예외: {e}")
        return {"campus": None, "class_name": None, "author_name": None}


# --- 파일 내용 읽기 ---
async def read_file_content(file: UploadFile) -> str:
    await file.seek(0)
    content_bytes = await file.read()
    filename_lower = file.filename.lower()

    if filename_lower.endswith(".xlsx"):
        file_stream = io.BytesIO(content_bytes)
        # 텍스트 읽기는 기존대로 pandas/openpyxl 사용
        excel_data = pd.read_excel(file_stream, sheet_name=None, engine="openpyxl")
        report_content = ""

        for sheet_name, df in excel_data.items():
            report_content += f"--- 시트: {sheet_name} ---\n"

            # ✨ [수정] 데이터 정제 로직 추가
            # 1. 모든 NaN(빈 값)을 빈 문자열("")로 변경
            df = df.fillna("")

            # 2. 컬럼 이름에 'Unnamed'가 포함되어 있으면 빈 문자열로 변경
            # (헤더가 없는 경우 보기 흉한 'Unnamed: 1' 등을 제거)
            new_columns = []
            for col in df.columns:
                if "Unnamed" in str(col):
                    new_columns.append("")
                else:
                    new_columns.append(str(col))
            df.columns = new_columns

            # 3. 문자열로 변환 (index=False로 행 번호 제거)
            report_content += df.to_string(index=False) + "\n\n"

        return report_content

    elif filename_lower.endswith(".txt") or filename_lower.endswith(".csv"):
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return content_bytes.decode("cp949")
            except:
                raise HTTPException(
                    status_code=400, detail=f"파일 디코딩 실패: {file.filename}"
                )
    else:
        try:
            return content_bytes.decode("utf-8")
        except:
            raise HTTPException(
                status_code=400, detail=f"지원하지 않는 파일: {file.filename}"
            )


# --- 매칭 키 추출 ---
def get_matching_key(filename: str) -> str | None:
    try:
        name_without_ext = os.path.splitext(filename)[0]
        name_without_ext = unicodedata.normalize("NFC", name_without_ext)
        parts = name_without_ext.split("_")
        if len(parts) >= 3:
            return "_".join(parts[-3:])
        return None
    except:
        return None


# --- 파일 쌍/단일 파일 처리 로직 ---
async def process_single_pair(
    key: str,
    plan_file: Optional[UploadFile],
    report_file: Optional[UploadFile],
    system_prompt: str,
    gemini_api_caller: Callable[[str, str], Awaitable[str]],
):
    logger.info(f"[{key}] 쌍 처리 시작...")

    target_filename = (
        report_file.filename
        if report_file
        else (plan_file.filename if plan_file else None)
    )
    if not target_filename:
        return {"key": key, "status": "error", "error": "파일 없음"}

    try:
        # 1. 이미지 카운팅 (ZIP 방식)
        actual_photo_count = 0

        if plan_file and plan_file.filename.lower().endswith(".xlsx"):
            await plan_file.seek(0)
            p_bytes = await plan_file.read()
            p_count = count_images_in_excel(p_bytes)
            actual_photo_count += p_count
            logger.info(f"[{key}] 계획서 이미지: {p_count}장")
            await plan_file.seek(0)

        if report_file and report_file.filename.lower().endswith(".xlsx"):
            await report_file.seek(0)
            r_bytes = await report_file.read()
            r_count = count_images_in_excel(r_bytes)
            actual_photo_count += r_count
            logger.info(f"[{key}] 결과보고서 이미지: {r_count}장")
            await report_file.seek(0)

        logger.info(f"[{key}] 총 합산 이미지 개수: {actual_photo_count}장")

        # 2. 파일 내용 로드 (텍스트 추출)
        plan_content = ""
        if plan_file:
            plan_content = await read_file_content(plan_file)

        report_content = ""
        if report_file:
            report_content = await read_file_content(report_file)

        # 3. API 입력 내용 준비
        combined_content = ""
        if plan_content:
            combined_content += f"[계획서]\n{plan_content}\n\n"
        if report_content:
            combined_content += f"[결과보고서]\n{report_content}\n\n"

        if not combined_content:
            raise ValueError("파일 내용이 비어있습니다.")

        # ------------------------------------------------------------------
        # ✨ [디버깅용] Gemini에게 전송되는 내용을 텍스트 파일로 저장
        # ------------------------------------------------------------------
        debug_filename = f"debug/debug_payload_{key}.txt"
        try:
            with open(debug_filename, "w", encoding="utf-8") as f:
                f.write("--- SYSTEM PROMPT ---\n")
                f.write(
                    system_prompt[:500] + "\n... (생략) ...\n\n"
                )  # 시스템 프롬프트 앞부분만
                f.write("--- USER CONTENT (Combined) ---\n")
                f.write(combined_content)
            logger.info(
                f"[{key}] Gemini 전송 내용이 '{debug_filename}'에 저장되었습니다."
            )
        except Exception as e:
            logger.warning(f"[{key}] 디버그 파일 저장 실패: {e}")
        # ------------------------------------------------------------------

        # 4. API 호출
        api_response_text = await gemini_api_caller(system_prompt, combined_content)

        try:
            # 5. JSON 파싱
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
                raise ValueError("JSON 객체를 찾을 수 없습니다.")

            data = json.loads(cleaned_string)
            data_to_save = data[0] if isinstance(data, list) and data else data

            # 6. 데이터 보정 (실제 이미지 개수로 덮어쓰기)
            data_to_save["photo_count_detected"] = actual_photo_count

            total = data_to_save.get("total")
            final_json_string = json.dumps(data_to_save, ensure_ascii=False)

            # 7. DB 저장
            info = extract_info_from_filename(target_filename)

            await asyncio.to_thread(
                db_utils.save_result_to_db,
                os.path.splitext(target_filename)[0],
                total,
                actual_photo_count,
                final_json_string,
                info.get("campus"),
                info.get("class_name"),
                info.get("author_name"),
            )

        except Exception as e:
            logger.error(f"[{key}] 파싱/DB저장 실패: {e}")
            return {
                "key": key,
                "filename": target_filename,
                "status": "error",
                "error": f"파싱/저장 오류: {e}",
            }

        return {
            "key": key,
            "filename": target_filename,
            "status": "success",
            "analysis_result": final_json_string,
        }

    except Exception as e:
        logger.error(f"[{key}] 처리 중 오류: {e}")
        return {
            "key": key,
            "filename": target_filename,
            "status": "error",
            "error": str(e),
        }
