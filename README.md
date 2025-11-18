# 가상환경 실행

(Window)
1. python -m venv venv
2. .\venv\Scripts\activate

(Mac)
1. python3 -m venv venv
2. source venv/bin/activate

# 의존성 설치

pip install -r requirements.txt

# API 서버 실행

uvicorn app.main:app --reload

# 엑셀 서버 실행

1. cd evaluation_report/
2. uvicorn server:app --reload
