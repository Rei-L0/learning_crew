from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from .schemas.user import UserResponse # 👈 사용자 정보 DTO
# TokenData는 현재 사용되지 않으므로 import 제거
# from .schemas.auth import TokenData

# --- (1) 설정 ---
# 이 SECRET_KEY는 절대 외부에 노출되면 안 됩니다.
# (실제로는 .env 파일에서 읽어옵니다)
SECRET_KEY = "YOUR_VERY_VERY_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1일
REFRESH_TOKEN_EXPIRE_DAYS = 7 # 7일

# 비밀번호 해싱을 위한 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# (1-1) FastAPI가 "/api/auth/login"에서 토큰을 사용함을 알림 (지금은 사용 안함)
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# (1-2) FastAPI가 "Authorization: Bearer <token>" 헤더를 찾도록 함
# 이것이 '의존성'의 핵심입니다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- (2) 비밀번호 검증 ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호를 비교"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호를 해시화"""
    return pwd_context.hash(password)

# --- (3) 토큰 생성 (auth.py에서 사용) ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # 'sub' (subject) 키에 사용자 식별자(studentId)를 넣는 것이 표준입니다.
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- (4) 사용자 조회 (가상 DB) ---
# 미리 계산된 비밀번호 해시 (실제로는 DB에 저장된 값)
# 테스트용: "ssafy123456!" -> 이 해시값
HASHED_PASSWORD_123456 = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqJqZ5q5Xe"  # ssafy123456!
HASHED_PASSWORD_700000 = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqJqZ5q5Xe"  # admin123! (예시)

def get_user_by_student_id(student_id: str):
    """
    학번으로 사용자를 조회합니다.
    실제로는 DB 쿼리를 수행합니다.
    """
    # 가상 사용자 데이터 (실제로는 DB에서 조회)
    # 학번이 7로 시작하면 ADMIN, 아니면 STUDENT
    if student_id == "123456":
        return {
            "id": 1,
            "studentId": "123456",
            "name": "김싸피",
            "role": "STUDENT",
            "campus": "부울경",
            "classNo": "1반",
            "hashed_password": HASHED_PASSWORD_123456  # 실제로는 DB에 저장된 해시
        }
    elif student_id.startswith("7"):
        # ADMIN 사용자 예시
        return {
            "id": 2,
            "studentId": "700000",
            "name": "관리자",
            "role": "ADMIN",
            "campus": None,
            "classNo": None,
            "hashed_password": HASHED_PASSWORD_700000
        }
    return None

# --- (5) 핵심 의존성: 현재 사용자 가져오기 ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """
    이 함수가 /api/users/me 같은 보호된 엔드포인트에서
    'Depends()'에 의해 호출되어 토큰을 검증하고 사용자 정보를 반환합니다.
    """
    
    # (3-1) 토큰 디코딩 시도
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 'sub' (studentId) 값 추출
        student_id: str = payload.get("sub")
        if student_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: User ID not found",
            )
        
        # (토큰 데이터 유효성 검사 - 옵션)
        # token_data = TokenData(studentId=student_id)

    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # (3-2) (가상) DB에서 사용자 조회
    # 실제로는: user = db.query(User).filter(User.studentId == student_id).first()
    if student_id == "123456": # 👈 (로그인 로직과 동일한 가상 사용자)
        user_from_db = {
            "id": 1,
            "studentId": "123456",
            "name": "김싸피",
            "role": "STUDENT",
            "campus": "부울경",
            "classNo": "1반"
        }
        # Pydantic 모델로 변환하여 반환
        return UserResponse(**user_from_db)
    else:
        raise HTTPException(status_code=404, detail="User not found")