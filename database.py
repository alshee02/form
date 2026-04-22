import sqlite3
from contextlib import contextmanager
from teams import DB_PATH, TEAM_RANKING_QUESTIONS, CONTRIBUTION_QUESTIONS


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """DB 테이블 생성. 응답자 1명당 1회만 제출 가능하도록 UNIQUE 제약."""
    ranking_cols = ",\n            ".join(
        [f"{key} INTEGER NOT NULL" for key, _ in TEAM_RANKING_QUESTIONS]
    )
    contrib_cols = ",\n            ".join(
        [f"{key} INTEGER NOT NULL" for key, _ in CONTRIBUTION_QUESTIONS]
    )

    with get_conn() as conn:
        c = conn.cursor()
        # 제출 기록 (중복방지용) - 설문 유형별로 한 사람당 1회
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                respondent_team TEXT NOT NULL,
                respondent_name TEXT NOT NULL,
                survey_type TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(respondent_team, respondent_name, survey_type)
            )
        """)

        # 팀 간 순위 평가 응답
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS team_ranking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                target_team TEXT NOT NULL,
                {ranking_cols},
                question TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES submissions(id)
            )
        """)

        # 팀 내 기여도 평가 응답
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS contribution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                respondent_role TEXT,
                target_name TEXT NOT NULL,
                target_team TEXT NOT NULL,
                {contrib_cols},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES submissions(id)
            )
        """)


def has_submitted(respondent_team, respondent_name, survey_type):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT 1 FROM submissions WHERE respondent_team=? AND respondent_name=? AND survey_type=?",
            (respondent_team, respondent_name, survey_type),
        )
        return c.fetchone() is not None


def create_submission(respondent_team, respondent_name, survey_type):
    """제출 기록 생성. 이미 제출했으면 IntegrityError 발생."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO submissions (respondent_team, respondent_name, survey_type) VALUES (?, ?, ?)",
            (respondent_team, respondent_name, survey_type),
        )
        return c.lastrowid


def save_team_ranking(submission_id, target_team, scores, question_text):
    """scores: {key: int} 형태"""
    keys = [k for k, _ in TEAM_RANKING_QUESTIONS]
    cols = ", ".join(keys)
    placeholders = ", ".join(["?"] * len(keys))
    values = [scores[k] for k in keys]
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            f"INSERT INTO team_ranking (submission_id, target_team, {cols}, question) VALUES (?, ?, {placeholders}, ?)",
            [submission_id, target_team, *values, question_text],
        )


def save_contribution(submission_id, respondent_role, target_name, target_team, scores):
    keys = [k for k, _ in CONTRIBUTION_QUESTIONS]
    cols = ", ".join(keys)
    placeholders = ", ".join(["?"] * len(keys))
    values = [scores[k] for k in keys]
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            f"INSERT INTO contribution (submission_id, respondent_role, target_name, target_team, {cols}) VALUES (?, ?, ?, ?, {placeholders})",
            [submission_id, respondent_role, target_name, target_team, *values],
        )


def get_team_ranking_results():
    """조별 평균 점수 집계"""
    keys = [k for k, _ in TEAM_RANKING_QUESTIONS]
    avg_cols = ", ".join([f"AVG({k}) as {k}_avg" for k in keys])
    total_expr = " + ".join([f"AVG({k})" for k in keys])
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT target_team, COUNT(*) as n_responses, {avg_cols},
                   ({total_expr}) as total_avg
            FROM team_ranking
            GROUP BY target_team
            ORDER BY total_avg DESC
        """)
        return [dict(r) for r in c.fetchall()]


def get_team_questions():
    """각 조에 대한 주관식 질문들"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT target_team, question
            FROM team_ranking
            WHERE question IS NOT NULL AND TRIM(question) != ''
            ORDER BY target_team, created_at
        """)
        return [dict(r) for r in c.fetchall()]


def get_contribution_results():
    """팀원별 평균 기여도"""
    keys = [k for k, _ in CONTRIBUTION_QUESTIONS]
    avg_cols = ", ".join([f"AVG({k}) as {k}_avg" for k in keys])
    total_expr = " + ".join([f"AVG({k})" for k in keys])
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(f"""
            SELECT target_team, target_name, COUNT(*) as n_responses, {avg_cols},
                   ({total_expr}) as total_avg
            FROM contribution
            GROUP BY target_team, target_name
            ORDER BY target_team, total_avg DESC
        """)
        return [dict(r) for r in c.fetchall()]


def get_submission_stats():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT survey_type, COUNT(*) as n
            FROM submissions
            GROUP BY survey_type
        """)
        return {r["survey_type"]: r["n"] for r in c.fetchall()}


def get_roles_by_team():
    """조별 팀원이 적은 역할"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT s.respondent_team, s.respondent_name, c.respondent_role
            FROM submissions s
            JOIN contribution c ON c.submission_id = s.id
            WHERE c.respondent_role IS NOT NULL AND TRIM(c.respondent_role) != ''
            ORDER BY s.respondent_team, s.respondent_name
        """)
        return [dict(r) for r in c.fetchall()]


def reset_db():
    """모든 응답 데이터 초기화"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM team_ranking")
        c.execute("DELETE FROM contribution")
        c.execute("DELETE FROM submissions")
