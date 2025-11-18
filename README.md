# 가상환경 활성화
python -m venv venv

# 가상환경 실행

(Window)
python -m venv venv
.\venv\Scripts\activate

(Mac)
python3 -m venv venv
source venv/bin/activate

# 의존성 설치

pip install -r requirements.txt

# API 서버 실행

uvicorn app.main:app --reload

# 엑셀 서버 실행

cd evaluation_report/
uvicorn server:app --reload
