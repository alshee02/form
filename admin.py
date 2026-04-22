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
    get_all_respondents,
    get_individual_team_ranking,
    get_individual_contribution,
    get_team_ranking_raw,
    get_contribution_raw,
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

tab1, tab2, tab3, tab4 = st.tabs(["📊 팀 간 순위", "👥 팀 내 기여도", "💬 질문사항", "👤 개별 응답"])

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

    st.divider()
    st.subheader("📋 개별 응답 원시 데이터")
    raw = get_team_ranking_raw()
    if not raw:
        st.info("아직 응답이 없습니다.")
    else:
        raw_df = pd.DataFrame(raw)
        col_rename = {
            "respondent_team": "응답자 조",
            "respondent_name": "응답자 이름",
            "target_team": "평가 대상 조",
            "total": "합계",
            "question": "질문/코멘트",
        }
        for key, label in TEAM_RANKING_QUESTIONS:
            col_rename[key] = label.split(" — ")[0]
        raw_df = raw_df.rename(columns=col_rename)
        st.dataframe(raw_df, use_container_width=True, hide_index=True)
        csv_raw = raw_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 개별 응답 CSV", csv_raw, "team_ranking_raw.csv", "text/csv")

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
    st.subheader("📋 개별 응답 원시 데이터")
    raw_contrib = get_contribution_raw()
    if not raw_contrib:
        st.info("아직 응답이 없습니다.")
    else:
        raw_cdf = pd.DataFrame(raw_contrib)
        col_rename = {
            "respondent_team": "응답자 조",
            "respondent_name": "응답자 이름",
            "target_team": "평가 대상 조",
            "target_name": "평가 대상 이름",
            "total": "합계",
        }
        for key, label in CONTRIBUTION_QUESTIONS:
            col_rename[key] = label.split(" — ")[0]
        raw_cdf = raw_cdf.rename(columns=col_rename)

        for team in sorted(raw_cdf["평가 대상 조"].unique()):
            st.markdown(f"#### {team}")
            sub = raw_cdf[raw_cdf["평가 대상 조"] == team].drop(columns=["평가 대상 조"]).sort_values(["평가 대상 이름", "응답자 조", "응답자 이름"]).reset_index(drop=True)
            st.dataframe(sub, use_container_width=True, hide_index=True)

        csv_raw = raw_cdf.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 개별 응답 CSV", csv_raw, "contribution_raw.csv", "text/csv")

        st.divider()
        st.subheader("팀원별 맡은 역할")
        roles = get_roles_by_team()
        if roles:
            role_df = pd.DataFrame(roles).rename(
                columns={"respondent_team": "조", "respondent_name": "이름", "respondent_role": "역할"}
            )
            st.dataframe(role_df, use_container_width=True, hide_index=True)

# ---------- 개별 응답 ----------
with tab4:
    st.subheader("👤 개별 응답 조회")
    respondents = get_all_respondents()
    if not respondents:
        st.info("아직 제출된 응답이 없습니다.")
    else:
        # 제출자 목록 (중복 제거)
        submitted_people = sorted(
            {(r["respondent_team"], r["respondent_name"]) for r in respondents},
            key=lambda x: (x[0], x[1]),
        )
        submitted_types = {
            (r["respondent_team"], r["respondent_name"]): [] for r in respondents
        }
        for r in respondents:
            submitted_types[(r["respondent_team"], r["respondent_name"])].append(r["survey_type"])

        options = [f"{team} - {name}" for team, name in submitted_people]
        selected = st.selectbox("응답자 선택", options)

        if selected:
            sel_team, sel_name = selected.split(" - ", 1)
            done_types = submitted_types.get((sel_team, sel_name), [])

            st.markdown(f"### {sel_team} · {sel_name}")
            st.caption(f"제출한 설문: {', '.join(done_types)}")

            # 팀 간 순위 응답
            st.markdown("#### 📊 팀 간 순위 평가")
            ranking_rows = get_individual_team_ranking(sel_team, sel_name)
            if not ranking_rows:
                st.info("팀 간 순위 응답 없음")
            else:
                ranking_df = pd.DataFrame(ranking_rows)
                col_rename = {"target_team": "평가 대상 조", "question": "질문/코멘트"}
                for key, label in TEAM_RANKING_QUESTIONS:
                    col_rename[key] = label.split(" — ")[0]
                ranking_df = ranking_df.rename(columns=col_rename)
                st.dataframe(ranking_df, use_container_width=True, hide_index=True)

            st.divider()

            # 팀 내 기여도 응답
            st.markdown("#### 👥 팀 내 기여도 평가")
            contrib_rows = get_individual_contribution(sel_team, sel_name)
            if not contrib_rows:
                st.info("기여도 평가 응답 없음")
            else:
                contrib_df = pd.DataFrame(contrib_rows)
                col_rename = {
                    "target_team": "평가 대상 조",
                    "target_name": "평가 대상 이름",
                    "respondent_role": "본인 역할",
                }
                for key, label in CONTRIBUTION_QUESTIONS:
                    col_rename[key] = label.split(" — ")[0]
                contrib_df = contrib_df.rename(columns=col_rename)
                st.dataframe(contrib_df, use_container_width=True, hide_index=True)

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
