# db_utils.py
import sqlite3
import logging
import json
from typing import Optional

# 로컬 모듈 임포트
# app_config에서 DB 경로를 관리하는 경우 여기에 포함시키거나, server.py에서와 같이 직접 정의합니다.
# 여기서는 server.py에서 정의한 DATABASE_URL을 재정의합니다.
DATABASE_URL = "analysis_results.db"

logger = logging.getLogger(__name__)


# --- DB 설정 및 초기화 (server.py에서 이동) ---
def init_db():
    """DB 테이블을 확인하고, 새 컬럼(campus, class_name, author_name)을 추가합니다."""
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

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
    logger.info("데이터베이스 테이블 확인/업데이트 완료.")


# --- DB 저장 함수 (server.py에서 이동) ---
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


# --- 결과 목록 조회 함수 (server.py에서 이동) ---
def get_all_results(
    campus: Optional[str],
    class_name: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    q: Optional[str],
) -> list[dict]:
    """DB에 저장된 분석 결과 목록을 (필터링하여) 반환합니다."""
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


# --- 필터 옵션 조회 함수 (server.py에서 이동) ---
def get_filter_options() -> dict:
    """필터링 드롭다운에 사용할 캠퍼스 및 반 목록을 반환합니다."""
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


# --- 세부 내용 조회 함수 (server.py에서 이동) ---
def get_result_detail(result_id: int) -> dict:
    """특정 분석 결과의 상세 내용(JSON 데이터)을 반환합니다."""
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
        # 이 함수를 server.py에서 호출할 때 HTTPException으로 래핑됩니다.
        raise FileNotFoundError(f"결과 ID {result_id}를 찾을 수 없습니다.")
