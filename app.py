import streamlit as st
import sqlite3
import pandas as pd
from teams import (
    TEAMS,
    TEAM_RANKING_QUESTIONS,
    CONTRIBUTION_QUESTIONS,
    LIKERT_OPTIONS,
)
from database import (
    init_db,
    has_submitted,
    create_submission,
    save_team_ranking,
    save_contribution,
    get_team_ranking_results,
    get_team_questions,
    get_contribution_results,
    get_submission_stats,
    get_roles_by_team,
    reset_db,
)

st.set_page_config(page_title="중간고사 발표 평가", page_icon="📝", layout="centered")

init_db()

ADMIN_PASSWORD = "admin1234"

# ---------- 사이드바: 관리자 모드 ----------
with st.sidebar:
    st.caption("관리자")
    if not st.session_state.get("auth"):
        pw = st.text_input("관리자 비밀번호", type="password", key="pw_input")
        if st.button("로그인"):
            if pw == ADMIN_PASSWORD:
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    else:
        st.success("관리자 모드")
        if st.button("로그아웃"):
            st.session_state["auth"] = False
            st.rerun()

# ========== 관리자 대시보드 ==========
if st.session_state.get("auth"):
    st.title("📈 설문 결과 대시보드")

    stats = get_submission_stats()
    c1, c2 = st.columns(2)
    c1.metric("팀 간 순위 응답자 수", stats.get("team_ranking", 0))
    c2.metric("기여도 평가 응답자 수", stats.get("contribution", 0))

    tab1, tab2, tab3 = st.tabs(["📊 팀 간 순위", "👥 팀 내 기여도", "💬 질문사항"])

    with tab1:
        st.subheader("팀 간 순위 (총점 기준 내림차순)")
        results = get_team_ranking_results()
        if not results:
            st.info("아직 응답이 없습니다.")
        else:
            df = pd.DataFrame(results)
            rename_map = {"target_team": "조", "n_responses": "응답수", "total_avg": "총점(평균합)"}
            for key, label in TEAM_RANKING_QUESTIONS:
                rename_map[f"{key}_avg"] = label.split(" — ")[0]
            df = df.rename(columns=rename_map)
            df.insert(0, "순위", range(1, len(df) + 1))
            num_cols = df.select_dtypes(include="number").columns.drop("순위").drop("응답수", errors="ignore")
            df[num_cols] = df[num_cols].round(2)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.subheader("문항별 평균 (조별 비교)")
            chart_cols = [label.split(" — ")[0] for _, label in TEAM_RANKING_QUESTIONS]
            st.bar_chart(df.set_index("조")[chart_cols])

            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 CSV 다운로드", csv, "team_ranking_results.csv", "text/csv")

    with tab2:
        st.subheader("팀 내 기여도 (조별)")
        results = get_contribution_results()
        if not results:
            st.info("아직 응답이 없습니다.")
        else:
            df = pd.DataFrame(results)
            rename_map = {"target_team": "조", "target_name": "이름", "n_responses": "평가수", "total_avg": "총점(평균합)"}
            for key, label in CONTRIBUTION_QUESTIONS:
                rename_map[f"{key}_avg"] = label.split(" — ")[0]
            df = df.rename(columns=rename_map)
            num_cols = df.select_dtypes(include="number").columns.drop("평가수", errors="ignore")
            df[num_cols] = df[num_cols].round(2)

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

    # ---------- 초기화 ----------
    st.divider()
    with st.expander("⚠️ 데이터 초기화 (위험)"):
        st.warning("모든 응답 데이터가 삭제되며 복구할 수 없습니다.")
        confirm = st.checkbox("초기화할 것을 확인합니다")
        if st.button("전체 초기화", type="primary", disabled=not confirm):
            reset_db()
            st.success("초기화 완료! 모든 응답이 삭제되었습니다.")
            st.rerun()

    with tab3:
        st.subheader("💬 각 조에 대한 질문 (익명)")
        questions = get_team_questions()
        if not questions:
            st.info("아직 작성된 질문이 없습니다.")
        else:
            q_df = pd.DataFrame(questions)
            for team in sorted(q_df["target_team"].unique()):
                st.markdown(f"#### {team}")
                for i, q in enumerate(q_df[q_df["target_team"] == team]["question"].tolist(), 1):
                    st.markdown(f"{i}. {q}")

    st.stop()

# ========== 응답자 설문 ==========
st.title("📝 중간고사 발표 평가")
st.caption("응답 내용은 익명으로 집계되며, 개별 응답자는 결과에 노출되지 않습니다.")

# ---------- 응답자 식별 ----------
st.subheader("본인 정보")
col1, col2 = st.columns(2)
with col1:
    my_team = st.selectbox("본인의 조", options=list(TEAMS.keys()), index=None, placeholder="조를 선택하세요")
with col2:
    my_name = None
    if my_team:
        my_name = st.selectbox("본인의 이름", options=TEAMS[my_team], index=None, placeholder="이름을 선택하세요")

if not (my_team and my_name):
    st.info("먼저 본인의 조와 이름을 선택해 주세요.")
    st.stop()

# ---------- 단계 결정 ----------
tr_done = has_submitted(my_team, my_name, "team_ranking")
ct_done = has_submitted(my_team, my_name, "contribution")

identity_key = f"{my_team}__{my_name}"
if st.session_state.get("identity_key") != identity_key:
    st.session_state["identity_key"] = identity_key
    st.session_state["step"] = "contribution" if tr_done else "team_ranking"

step = st.session_state.get("step", "team_ranking")

st.divider()
col_a, col_b = st.columns(2)
with col_a:
    if tr_done or step == "contribution":
        st.success("✅ 1단계: 팀 간 순위 조사 완료")
    else:
        st.info("▶ 1단계: 팀 간 순위 조사")
with col_b:
    if ct_done:
        st.success("✅ 2단계: 팀 내 기여도 평가 완료")
    elif step == "contribution":
        st.info("▶ 2단계: 팀 내 기여도 평가")
    else:
        st.caption("2단계: 팀 내 기여도 평가")

st.divider()

if tr_done and ct_done:
    st.success(f"🎉 {my_team} {my_name}님, 모든 설문에 응답하셨습니다. 감사합니다!")
    st.stop()

# ========== 1단계: 팀 간 순위 조사 ==========
if step == "team_ranking":
    st.subheader("📊 1단계: 팀 간 순위 조사")
    st.write(f"본인 조(**{my_team}**)를 제외한 모든 조에 대해 평가해 주세요.")

    other_teams = [t for t in TEAMS.keys() if t != my_team]
    responses = {}
    questions_text = {}

    for team in other_teams:
        with st.expander(f"**{team}** 평가", expanded=True):
            team_scores = {}
            for key, label in TEAM_RANKING_QUESTIONS:
                score = st.radio(
                    label,
                    options=list(LIKERT_OPTIONS.keys()),
                    format_func=lambda x: LIKERT_OPTIONS[x],
                    index=None,
                    key=f"tr_{team}_{key}",
                    horizontal=True,
                )
                team_scores[key] = score
            question = st.text_area(
                f"{team}에 궁금한 점이 있다면 자유롭게 작성해 주세요 (선택)",
                key=f"tr_{team}_q",
                placeholder="발표를 듣고 궁금했던 내용, 피드백 등",
            )
            responses[team] = team_scores
            questions_text[team] = question.strip()

    if st.button("다음 단계로 →", type="primary", use_container_width=True):
        missing = []
        for team, scores in responses.items():
            for key, label in TEAM_RANKING_QUESTIONS:
                if scores[key] is None:
                    missing.append(f"{team} - {label.split(' — ')[0]}")

        if missing:
            st.error("❌ 다음 항목에 응답해 주세요:\n\n" + "\n".join(f"- {m}" for m in missing[:10]))
        else:
            try:
                submission_id = create_submission(my_team, my_name, "team_ranking")
                for team, scores in responses.items():
                    save_team_ranking(submission_id, team, scores, questions_text.get(team, ""))
                st.session_state["step"] = "contribution"
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("이미 제출된 응답입니다.")

# ========== 2단계: 팀 내 기여도 평가 ==========
else:
    st.subheader("👥 2단계: 팀 내 기여도 평가")
    st.write(f"같은 조(**{my_team}**) 팀원들의 기여도를 평가해 주세요. (본인 제외)")

    my_role = st.text_input(
        "**본인이 맡은 역할**",
        placeholder="예: 자료조사, PPT 제작, 발표, 팀장 등",
    )

    st.divider()

    teammates = [n for n in TEAMS[my_team] if n != my_name]
    if not teammates:
        st.info("평가할 팀원이 없습니다.")
        st.stop()

    responses = {}

    for name in teammates:
        with st.expander(f"**{name}** 평가", expanded=True):
            scores = {}
            for key, label in CONTRIBUTION_QUESTIONS:
                score = st.radio(
                    label,
                    options=list(LIKERT_OPTIONS.keys()),
                    format_func=lambda x: LIKERT_OPTIONS[x],
                    index=None,
                    key=f"ct_{name}_{key}",
                    horizontal=True,
                )
                scores[key] = score
            responses[name] = scores

    if st.button("제출하기", type="primary", use_container_width=True):
        missing = []
        if not my_role.strip():
            missing.append("본인이 맡은 역할")
        for name, scores in responses.items():
            for key, label in CONTRIBUTION_QUESTIONS:
                if scores[key] is None:
                    missing.append(f"{name} - {label.split(' — ')[0]}")

        if missing:
            st.error("❌ 다음 항목에 응답해 주세요:\n\n" + "\n".join(f"- {m}" for m in missing[:10]))
        else:
            try:
                submission_id = create_submission(my_team, my_name, "contribution")
                for name, scores in responses.items():
                    save_contribution(submission_id, my_role.strip(), name, my_team, scores)
                st.success("✅ 모든 설문이 완료되었습니다. 감사합니다!")
                st.balloons()
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("이미 제출된 응답입니다.")
