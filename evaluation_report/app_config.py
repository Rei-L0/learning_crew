# config.py
import os
from dotenv import load_dotenv  # ✨ 신규: 환경변수 로드용

# --- ✨ 환경 변수 로드 ---
# .env 파일을 찾아서 환경 변수로 설정합니다.
load_dotenv()

# --- 경로 설정 ---
# 1. config.py 파일이 있는 현재 디렉터리 (프로젝트 루트로 간주)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 2. prompts 폴더 경로 조합 (PROJECT_ROOT 기준)
SYSTEM_PROMPT_PATH = os.path.join(PROJECT_ROOT, "prompts/evaluation_prompt.txt")

# 다운로드 경로는 그대로 유지
DOWNLOADS_PATH = os.path.join(os.path.expanduser("~"), "Downloads")


# --- Google AI API 설정 (환경 변수 로드) ---
API_KEY = os.getenv("GOOGLE_API_KEY")  # 환경 변수에서 API 키 로드
API_MODEL = os.getenv(
    "GEMINI_MODEL", "gemini-2.5-flash"
)  # 환경 변수에서 모델 로드 (없으면 기본값 사용)

if not API_KEY:
    # 환경 변수 로드 실패 시 예외 발생
    raise ValueError(
        "API_KEY(GOOGLE_API_KEY)가 환경 변수(.env 파일)에 설정되지 않았습니다."
    )

# --- 파일 검색 및 기본값 설정 ---
TARGET_FILE_KEYWORDS = ["9월", "스터디", "이용호"]
DEFAULT_CONTENT = "한국에 대해 알려줘"
