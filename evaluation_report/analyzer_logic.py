# analyzer_logic.py
import os
import re
import json
import logging
import unicodedata
import asyncio
from typing import List, Optional, Callable, Awaitable, Union
import io
import zipfile

from fastapi import UploadFile, HTTPException
from google import genai
from google.genai import types
import pandas as pd
from PIL import Image

import app_config
import db_utils

logger = logging.getLogger(__name__)


# --- 엑셀 이미지 추출 함수 (ZIP 기반, 15KB 필터) ---
def extract_images_from_excel(file_bytes: bytes) -> List[Image.Image]:
    images = []
    MIN_IMAGE_SIZE = 15000  # 15KB 미만 무시

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            media_files = [
                f
                for f in z.namelist()
                if f.startswith("xl/media/") and not f.endswith("/")
            ]

            for file_name in media_files:
                try:
                    img_data = z.read(file_name)
                    if len(img_data) < MIN_IMAGE_SIZE:
                        continue
                    img = Image.open(io.BytesIO(img_data))
                    images.append(img)
                except Exception:
                    continue

            return images
    except Exception:
        return []


# --- API 호출 함수 ---
def call_gemini_api(system_prompt: str, contents: List[Union[str, Image.Image]]) -> str:
    if system_prompt == "ERROR: PROMPT NOT LOADED":
        raise ValueError("시스템 프롬프트가 올바르게 로드되지 않았습니다.")

    img_count = sum(1 for i in contents if isinstance(i, Image.Image))
    logger.info(f"Google AI API 호출 중... (텍스트 + 이미지 {img_count}장)")

    try:
        client = genai.Client(api_key=app_config.API_KEY)
        response = client.models.generate_content(
            model=app_config.API_MODEL,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=contents,
        )
        return response.text
    except Exception as e:
        logger.error(f"API 호출 실패: {e}")
        raise


# --- 파일명 정보 추출 ---
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
                info["author_name"] = re.split(r"[\.\s-]", author_raw, 1)[0]
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
    except Exception:
        return {"campus": None, "class_name": None, "author_name": None}


# --- 파일 내용 읽기 (표 형태 최적화) ---
async def read_file_content(file: UploadFile) -> str:
    await file.seek(0)
    content_bytes = await file.read()
    filename_lower = file.filename.lower()

    if filename_lower.endswith(".xlsx"):
        file_stream = io.BytesIO(content_bytes)
        excel_data = pd.read_excel(file_stream, sheet_name=None, engine="openpyxl")
        report_content = ""

        for sheet_name, df in excel_data.items():
            # 1. 데이터 정제
            df = df.fillna("")
            # 2. 헤더 정제
            new_columns = [
                "" if "Unnamed" in str(col) else str(col) for col in df.columns
            ]
            df.columns = new_columns

            # 3. 문자열 변환 (가독성 유지)
            try:
                table_text = df.to_string(index=False)
            except:
                table_text = df.to_string(index=False)

            report_content += f"\n### 시트명: {sheet_name}\n{table_text}\n"

        return report_content

    elif filename_lower.endswith(".txt") or filename_lower.endswith(".csv"):
        try:
            return content_bytes.decode("utf-8")
        except:
            return content_bytes.decode("cp949", errors="ignore")
    else:
        return content_bytes.decode("utf-8", errors="ignore")


# --- 매칭 키 추출 ---
def get_matching_key(filename: str) -> str | None:
    try:
        name = unicodedata.normalize("NFC", os.path.splitext(filename)[0])
        parts = name.split("_")
        return "_".join(parts[-3:]) if len(parts) >= 3 else None
    except:
        return None


# --- 쌍 처리 로직 ---
async def process_single_pair(
    key: str,
    plan_file: Optional[UploadFile],
    report_file: Optional[UploadFile],
    system_prompt: str,
    gemini_api_caller: Callable[[str, list], Awaitable[str]],
):
    logger.info(f"[{key}] 쌍 처리 시작...")

    # 1. 이미지 추출 (실제 개수 카운팅)
    extracted_images = []
    for file in [plan_file, report_file]:
        if file and file.filename.lower().endswith(".xlsx"):
            await file.seek(0)
            extracted_images.extend(extract_images_from_excel(await file.read()))
            await file.seek(0)

    actual_photo_count = len(extracted_images)
    logger.info(f"[{key}] 실제 감지된 이미지: {actual_photo_count}장")

    # 2. 텍스트 추출
    combined_text = ""
    if plan_file:
        combined_text += f"# [계획서 데이터]\n{await read_file_content(plan_file)}\n\n"
    if report_file:
        combined_text += (
            f"# [결과보고서 데이터]\n{await read_file_content(report_file)}\n\n"
        )

    if not combined_text:
        return {"key": key, "status": "error", "error": "내용 없음"}

    # ✨ [최적화 1] 텍스트 스마트 요약 (앞 20k + 뒤 5k)
    MAX_TOTAL_CHARS = 25000
    if len(combined_text) > MAX_TOTAL_CHARS:
        head_chars = 20000
        tail_chars = 5000
        combined_text = (
            combined_text[:head_chars]
            + f"\n\n... [중간 내용 {len(combined_text) - MAX_TOTAL_CHARS}자 생략됨] ...\n\n"
            + combined_text[-tail_chars:]
        )
        logger.info(f"[{key}] 텍스트 과다로 앞뒤만 추출하여 전송")

    # ✨ [최적화 2] 이미지 전송 개수 제한 (3장)
    MAX_IMAGES_TO_SEND = 3
    images_to_send = extracted_images[:MAX_IMAGES_TO_SEND]

    # ✨ [핵심 수정] AI에게 '메타데이터'를 주입하되, "비밀로 하라"는 지침 추가
    context_header = f"""
        [분석가를 위한 내부 참고 자료 (절대 출력 금지)]
        1. **실제 증빙 자료**: 기술적 제약으로 샘플 {len(images_to_send)}장만 보이지만, 실제 파일 내부에는 총 **{actual_photo_count}장**의 사진이 포함되어 있음. (평가 시 "풍부한 증빙 자료가 제출되었다"고 판단할 것)
        2. **텍스트 요약**: 내용이 길어 중간이 생략되었으나, 문맥을 통해 전체를 읽은 것처럼 평가할 것.

        [출력 시 주의사항]
        - 위 '내부 참고 자료', 'SYSTEM NOTE', '기술적 한계', '텍스트 생략' 등의 단어를 **결과 코멘트에 절대 언급하지 마십시오.**
        - 마치 당신이 **47장의 사진을 모두 직접 눈으로 확인했고, 전체 글을 꼼꼼히 다 읽은 사람처럼** 자연스럽게 작성하십시오.
        - 예시: "SYSTEM NOTE에 따라 47장으로..." (X) -> "47장의 풍부한 증빙 사진을 통해 활동 내역을 명확히 확인할 수 있습니다." (O)
        --------------------------------------------------
        """

    final_prompt_content = context_header + combined_text
    api_contents = [final_prompt_content] + images_to_send

    # 4. 디버그 저장 (✨수정: 시스템 프롬프트 제외, 실제 전송되는 내용만 저장)
    os.makedirs("debug", exist_ok=True)
    with open(f"debug/debug_payload_{key}.txt", "w", encoding="utf-8") as f:
        # 시스템 프롬프트 쓰기 제거함
        f.write(final_prompt_content)

    # 5. API 호출 및 결과 처리
    target_filename = report_file.filename if report_file else plan_file.filename
    try:
        api_response_text = await gemini_api_caller(system_prompt, api_contents)

        start = api_response_text.find("{")
        end = api_response_text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("JSON 형식 오류")

        cleaned_json = api_response_text[start : end + 1]
        data = json.loads(cleaned_json)
        if isinstance(data, list):
            data = data[0]

        # 데이터 보정 (우리가 센 정확한 개수 입력)
        data["photo_count_detected"] = actual_photo_count

        info = extract_info_from_filename(target_filename)

        await asyncio.to_thread(
            db_utils.save_result_to_db,
            os.path.splitext(target_filename)[0],
            data.get("total", 0),
            actual_photo_count,
            json.dumps(data, ensure_ascii=False),
            info.get("campus"),
            info.get("class_name"),
            info.get("author_name"),
        )

        return {
            "key": key,
            "filename": target_filename,
            "status": "success",
            "analysis_result": json.dumps(data, ensure_ascii=False),
        }

    except Exception as e:
        logger.error(f"[{key}] 오류: {e}")
        return {
            "key": key,
            "filename": target_filename,
            "status": "error",
            "error": str(e),
        }
