import streamlit as st
import pandas as pd
from teams import TEAMS, TEAM_RANKING_QUESTIONS, CONTRIBUTION_QUESTIONS
from database import (
    init_db,
    get_team_ranking_results,
    get_team_questions,
    get_contribution_results,
    get_submission_stats,
    get_roles_by_team,
)

st.set_page_config(page_title="설문 결과 (관리자)", page_icon="🔐", layout="wide")
init_db()

# ---------- 비밀번호 보호 ----------
ADMIN_PASSWORD = "admin1234"  # ⚠️ 실제 배포 시 꼭 변경하세요

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 관리자 로그인")
    pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pw == ADMIN_PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

st.title("📈 설문 결과 대시보드")

stats = get_submission_stats()
c1, c2 = st.columns(2)
c1.metric("팀 간 순위 응답자 수", stats.get("team_ranking", 0))
c2.metric("기여도 평가 응답자 수", stats.get("contribution", 0))

tab1, tab2, tab3 = st.tabs(["📊 팀 간 순위", "👥 팀 내 기여도", "💬 질문사항"])

# ---------- 팀 간 순위 ----------
with tab1:
    st.subheader("팀 간 순위 (총점 기준 내림차순)")
    results = get_team_ranking_results()
    if not results:
        st.info("아직 응답이 없습니다.")
    else:
        df = pd.DataFrame(results)
        # 컬럼 이름 한글화
        rename_map = {"target_team": "조", "n_responses": "응답수", "total_avg": "총점(평균합)"}
        for key, label in TEAM_RANKING_QUESTIONS:
            short_label = label.split(" — ")[0]
            rename_map[f"{key}_avg"] = short_label
        df = df.rename(columns=rename_map)

        # 순위 컬럼 추가
        df.insert(0, "순위", range(1, len(df) + 1))

        # 숫자 반올림
        num_cols = df.select_dtypes(include="number").columns.drop("순위").drop("응답수", errors="ignore")
        df[num_cols] = df[num_cols].round(2)

        st.dataframe(df, use_container_width=True, hide_index=True)

        # 문항별 평균 차트
        st.subheader("문항별 평균 (조별 비교)")
        chart_cols = [label.split(" — ")[0] for _, label in TEAM_RANKING_QUESTIONS]
        chart_df = df.set_index("조")[chart_cols]
        st.bar_chart(chart_df)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 CSV 다운로드", csv, "team_ranking_results.csv", "text/csv")

# ---------- 팀 내 기여도 ----------
with tab2:
    st.subheader("팀 내 기여도 (조별)")
    results = get_contribution_results()
    if not results:
        st.info("아직 응답이 없습니다.")
    else:
        df = pd.DataFrame(results)
        rename_map = {
            "target_team": "조",
            "target_name": "이름",
            "n_responses": "평가수",
            "total_avg": "총점(평균합)",
        }
        for key, label in CONTRIBUTION_QUESTIONS:
            short_label = label.split(" — ")[0]
            rename_map[f"{key}_avg"] = short_label
        df = df.rename(columns=rename_map)

        num_cols = df.select_dtypes(include="number").columns.drop("평가수", errors="ignore")
        df[num_cols] = df[num_cols].round(2)

        # 조별로 그룹핑해서 보여주기
        for team in sorted(df["조"].unique()):
            st.markdown(f"#### {team}")
            sub = df[df["조"] == team].drop(columns=["조"]).sort_values("총점(평균합)", ascending=False).reset_index(drop=True)
            sub.insert(0, "조내순위", range(1, len(sub) + 1))
            st.dataframe(sub, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 CSV 다운로드", csv, "contribution_results.csv", "text/csv")

        st.divider()
        st.subheader("팀원별 맡은 역할")
        roles = get_roles_by_team()
        if roles:
            role_df = pd.DataFrame(roles).rename(
                columns={"respondent_team": "조", "respondent_name": "이름", "respondent_role": "역할"}
            )
            st.dataframe(role_df, use_container_width=True, hide_index=True)

# ---------- 질문사항 ----------
with tab3:
    st.subheader("💬 각 조에 대한 질문 (익명)")
    questions = get_team_questions()
    if not questions:
        st.info("아직 작성된 질문이 없습니다.")
    else:
        q_df = pd.DataFrame(questions)
        for team in sorted(q_df["target_team"].unique()):
            st.markdown(f"#### {team}")
            sub = q_df[q_df["target_team"] == team]["question"].tolist()
            for i, q in enumerate(sub, 1):
                st.markdown(f"{i}. {q}")
            st.markdown("")
