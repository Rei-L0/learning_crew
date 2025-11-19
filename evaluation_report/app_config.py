# config.py
import os
import dotenv

# --- 경로 설정 ---
# 1. config.py 파일이 있는 현재 디렉터리 (예: .../evaluation_report)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 그것의 부모 디렉터리 (예: .../<프로젝트 폴더>)
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)

# 3. 프로젝트 루트를 기준으로 prompts 폴더 경로 조합
# 이 부분이 Traceback에서 오류가 난 부분입니다. 이 변수가 존재해야 합니다.
SYSTEM_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts/evaluation_prompt.txt")

# 다운로드 경로는 그대로 유지
DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads")


# --- Google AI API 설정 ---
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("API_KEY가 설정되지 않았습니다. config.py를 확인하세요.")

# --- 파일 검색 및 기본값 설정 ---
TARGET_FILE_KEYWORDS = ["9월", "스터디", "이용호"]
DEFAULT_CONTENT = "한국에 대해 알려줘"

# --- API 모델 설정 ---
API_MODEL = "gemini-2.5-flash"
