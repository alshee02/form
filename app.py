import streamlit as st
import sqlite3
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
)

st.set_page_config(page_title="중간고사 발표 평가", page_icon="📝", layout="centered")

# DB 초기화
init_db()

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

# ---------- 설문 유형 선택 ----------
st.divider()
survey_type = st.radio(
    "진행할 설문을 선택하세요",
    options=["team_ranking", "contribution"],
    format_func=lambda x: "📊 팀 간 순위 조사" if x == "team_ranking" else "👥 팀 내 기여도 평가",
    horizontal=True,
)

# 중복 제출 체크
if has_submitted(my_team, my_name, survey_type):
    st.warning(f"✅ {my_team} {my_name}님은 이미 이 설문에 응답하셨습니다. (1인 1회 제출)")
    st.stop()

st.divider()

# ========== 팀 간 순위 조사 ==========
if survey_type == "team_ranking":
    st.subheader("📊 팀 간 순위 조사")
    st.write(f"본인 조(**{my_team}**)를 제외한 모든 조에 대해 평가해 주세요.")

    other_teams = [t for t in TEAMS.keys() if t != my_team]
    responses = {}  # {team: {key: score}}
    questions_text = {}  # {team: str}

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

    if st.button("제출하기", type="primary", use_container_width=True):
        # 유효성 검사: 모든 필수 척도 응답 여부
        missing = []
        for team, scores in responses.items():
            for key, label in TEAM_RANKING_QUESTIONS:
                if scores[key] is None:
                    missing.append(f"{team} - {label.split(' — ')[0]}")

        if missing:
            st.error(f"❌ 다음 항목에 응답해 주세요:\n\n" + "\n".join(f"- {m}" for m in missing[:10]))
        else:
            try:
                submission_id = create_submission(my_team, my_name, "team_ranking")
                for team, scores in responses.items():
                    save_team_ranking(submission_id, team, scores, questions_text.get(team, ""))
                st.success("✅ 응답이 제출되었습니다. 감사합니다!")
                st.balloons()
            except sqlite3.IntegrityError:
                st.error("이미 제출된 응답입니다.")

# ========== 팀 내 기여도 평가 ==========
else:
    st.subheader("👥 팀 내 기여도 평가")
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

    responses = {}  # {name: {key: score}}

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
            st.error(f"❌ 다음 항목에 응답해 주세요:\n\n" + "\n".join(f"- {m}" for m in missing[:10]))
        else:
            try:
                submission_id = create_submission(my_team, my_name, "contribution")
                for name, scores in responses.items():
                    save_contribution(submission_id, my_role.strip(), name, my_team, scores)
                st.success("✅ 응답이 제출되었습니다. 감사합니다!")
                st.balloons()
            except sqlite3.IntegrityError:
                st.error("이미 제출된 응답입니다.")
