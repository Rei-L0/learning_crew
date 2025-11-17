import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from google import genai
from google.genai import types

# --- ✨ CORS 미들웨어 임포트 ---
from fastapi.middleware.cors import CORSMiddleware

# --- ✨ 라이브러리 추가 ---
import pandas as pd
import io 

# 로컬 모듈 임포트
import app_config
import file_utils

# --- 로깅 설정 (main.py와 동일) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- FastAPI 앱 인스턴스 생성 ---
app = FastAPI()

# --- ✨ CORS 설정 추가 ---
# Live Server의 기본 주소(http://127.0.0.1:5500)를 허용합니다.
origins = [
    "http://127.0.0.1:5500",  # Live Server의 주소
    "http://localhost:5500",   # 만약을 대비한 localhost 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # origins 리스트에 있는 주소에서의 요청을 허용
    allow_credentials=True,    # 쿠키를 포함한 요청 허용
    allow_methods=["*"],       # 모든 HTTP 메서드 허용 (GET, POST 등)
    allow_headers=["*"],       # 모든 HTTP 헤더 허용
)
# --- CORS 설정 끝 ---

# ✨ 엑셀/텍스트 파일을 읽어 문자열로 반환하는 헬퍼 함수
async def read_file_content(file: UploadFile) -> str:
    """UploadFile 객체를 받아 엑셀이나 텍스트를 읽어 문자열로 반환"""
    content_bytes = await file.read()
    
    if file.filename.endswith('.xlsx'):
        logger.info(f"엑셀 파일(.xlsx) 파싱 중: {file.filename}")
        file_stream = io.BytesIO(content_bytes)
        excel_data = pd.read_excel(file_stream, sheet_name=None, engine='openpyxl')
        
        report_content = ""
        for sheet_name, df in excel_data.items():
            report_content += f"--- 시트: {sheet_name} ---\n"
            report_content += df.to_string(index=False) + "\n\n"
        return report_content
    
    elif file.filename.endswith('.txt'):
        logger.info(f"텍스트 파일(.txt) 파싱 중: {file.filename}")
        return content_bytes.decode('utf-8')
    
    else:
        logger.warning(f"지원하지 않는 파일 형식: {file.filename}. utf-8로 시도.")
        try:
            return content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            logger.error(f"파일 디코딩 실패: {file.filename}")
            raise HTTPException(status_code=400, detail=f"파일 디코딩 실패: {file.filename}")


# --- 전역 변수: 시스템 프롬프트 ---
# 서버가 시작될 때 1번만 로드해서 메모리에 저장해 둡니다.
SYSTEM_PROMPT = ""

# --- FastAPI 이벤트 핸들러: 서버 시작 시 실행 ---
@app.on_event("startup")
def startup_event():
    """서버가 시작될 때 시스템 프롬프트를 로드합니다."""
    global SYSTEM_PROMPT
    logger.info("서버 시작... 시스템 프롬프트 로드 중...")
    try:
        SYSTEM_PROMPT = file_utils.load_system_prompt(app_config.SYSTEM_PROMPT_PATH)
        logger.info("시스템 프롬프트 로드 완료")
    except Exception as e:
        logger.critical(f"서버 시작 실패: 시스템 프롬프트 로드 중 오류 발생 - {e}")
        # 실제 운영 시에는 여기서 서버를 중단시킬 수도 있습니다.
        SYSTEM_PROMPT = "ERROR: PROMPT NOT LOADED"

# --- API 호출 함수 (main.py와 동일) ---
def call_gemini_api(system_prompt: str, content: str) -> str:
    """Google AI API를 호출하고 응답 텍스트를 반환합니다."""
    
    if system_prompt == "ERROR: PROMPT NOT LOADED":
        logger.error("시스템 프롬프트가 로드되지 않아 API 호출을 중단합니다.")
        raise ValueError("시스템 프롬프트가 올바르게 로드되지 않았습니다.")

    logger.info("Google AI API 호출 중...")
    try:
        client = genai.Client(api_key=app_config.API_KEY)
        response = client.models.generate_content(
            model=app_config.API_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
            contents=content,
        )
        logger.info("API 호출 성공")
        return response.text
    except Exception as e:
        logger.error(f"API 호출 실패: {e}")
        raise

# --- API 엔드포인트 ---

@app.get("/")
def read_root():
    """서버가 실행 중인지 확인하는 기본 엔드포인트"""
    return {"message": "Gemini 분석 API 서버가 실행 중입니다."}


# --- 방법 1: 파일 업로드 API (프론트엔드 연동용) ---
@app.post("/upload-and-analyze")
async def upload_and_analyze(
    plan_file: UploadFile = File(...), 
    report_file: UploadFile = File(...)
    ):
    """
    파일을 업로드받아 그 내용을 분석하고 결과를 반환합니다.
    .xlsx 파일을 읽도록 수정되었습니다.
    """
    logger.info(f"파일 수신: [계획서] {plan_file.filename}, [결과보고서] {report_file.filename}")
    
    report_content = "" # 추출된 텍스트를 저장할 변수

    try:
        # ✨ 1. 계획서 파일 읽기
        plan_content = await read_file_content(plan_file)
        # ✨ 2. 결과보고서 파일 읽기
        report_content = await read_file_content(report_file)
        
        # ✨ 3. 두 내용을 하나의 프롬프트로 결합
        combined_content = f"""
        [제출된 계획서 내용]
        {plan_content}

        [제출된 결과보고서 내용]
        {report_content}
        """

    except Exception as e:
        logger.error(f"업로드된 파일 읽기 오류: {e}")
        raise HTTPException(status_code=400, detail=f"파일 읽기 오류: {e}")

    # 4. API 호출 (이후 로직은 동일)
    try:
        api_response = call_gemini_api(SYSTEM_PROMPT, combined_content) 
        
        return {
            "filename": report_file.filename,
            "analysis_result": api_response
        }
    except Exception as e:
        logger.error(f"API 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- 방법 2: 기존 로직 실행 API (단순 실행용) ---
@app.post("/run-local-analysis")
def run_local_analysis():
    """
    main.py의 로직을 그대로 실행합니다. 
    서버의 'DOWNLOADS_PATH'에서 파일을 검색합니다.
    """
    logger.info("로컬 파일 분석 API 호출됨...")
    
    # 1. 보고서 파일 검색 (main.py 로직)
    report_file_path = file_utils.find_file_by_keywords(
        app_config.DOWNLOADS_PATH,
        app_config.TARGET_FILE_KEYWORDS
    )

    # 2. 보고서 내용 읽기 (main.py 로직)
    report_content = app_config.DEFAULT_CONTENT
    file_source = "기본값 (DEFAULT_CONTENT)"
    
    if report_file_path:
        try:
            report_content = file_utils.get_file_content(report_file_path)
            file_source = report_file_path
            logger.info(f"파일 읽기 완료: {report_file_path}")
        except Exception as e:
            logger.error(f"파일 읽기 중 오류: {e}. 기본값을 사용합니다.")
    else:
        logger.warning(f"파일을 찾을 수 없어 기본값을 사용합니다. (경로: {app_config.DOWNLOADS_PATH})")

    # 3. API 호출
    try:
        api_response = call_gemini_api(SYSTEM_PROMPT, report_content)
        
        # 4. JSON 형식으로 결과 반환
        return {
            "file_processed": file_source,
            "analysis_result": api_response
        }
    except Exception as e:
        logger.error(f"API 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))