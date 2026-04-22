# 중간고사 발표 평가 설문 앱

Streamlit + SQLite 기반의 익명 설문조사 앱입니다.

## 📁 파일 구성

```
survey_app/
├── app.py              # 응답자용 설문 페이지
├── admin.py            # 관리자용 결과 대시보드 (비밀번호 보호)
├── teams.py            # 팀 구성 / 문항 / 척도 설정
├── database.py         # SQLite DB 로직
├── requirements.txt
└── survey.db           # 실행 시 자동 생성
```

## 🚀 실행 방법

### 1. 설치
```bash
pip install -r requirements.txt
```

### 2. 응답자용 앱 실행
```bash
streamlit run app.py
```
→ 기본 주소: `http://localhost:8501`

### 3. 관리자용 결과 대시보드 실행 (다른 포트)
```bash
streamlit run admin.py --server.port 8502
```
→ 기본 비밀번호: `admin1234` (꼭 `admin.py` 상단의 `ADMIN_PASSWORD` 를 변경하세요)

## 📝 설문 구성

### 팀 간 순위 조사 (5점 리커트)
- 주제의 적절성 / 내용의 충실성 / 자료 준비도 / 전달력 / 전반적 완성도
- 주관식 질문사항 (선택)
- 본인 조 제외, 나머지 조 평가

### 팀 내 기여도 평가 (5점 리커트)
- 본인이 맡은 역할 입력 (주관식)
- 참여도 / 책임감 / 기여도 / 협력 태도 / 적극성
- 본인 제외, 나머지 팀원 평가

## 🔒 익명성 / 중복방지 방식
- 응답자의 조·이름은 DB에 저장되지만 **결과 집계/대시보드에서는 노출되지 않습니다.**
- `(조, 이름, 설문유형)` 조합에 UNIQUE 제약이 걸려 있어 **1인 1회 제출**만 허용됩니다.
- 기여도 평가의 '역할' 필드는 누가 무슨 역할을 맡았는지 파악 용도로 관리자 화면에 표시됩니다. (원치 않으면 `admin.py`의 "팀원별 맡은 역할" 섹션을 제거하세요.)

## 📊 집계 방식
- **팀 순위**: 5개 문항의 평균 점수 합 → 내림차순
- **팀 내 기여도**: 5개 문항의 평균 점수 합 → 조별 내림차순

## 🌐 배포 (선택)
- **Streamlit Community Cloud**(무료): GitHub에 코드 푸시 → share.streamlit.io 에서 배포
  - 단, SQLite 파일이 재배포마다 초기화될 수 있으니 수업 중에는 한 서버에서 계속 돌리는 방식 권장
- **로컬 네트워크**: 강의실 Wi-Fi에서 교수자 노트북으로 실행 후 IP 공유
  ```bash
  streamlit run app.py --server.address 0.0.0.0
  ```
  → 학생들이 `http://<교수자IP>:8501` 로 접속

## 🛠 커스터마이징 포인트
- 팀 구성 변경: `teams.py`의 `TEAMS` 딕셔너리 수정
- 문항 수정: `teams.py`의 `TEAM_RANKING_QUESTIONS` / `CONTRIBUTION_QUESTIONS` 수정
- 척도 변경: `teams.py`의 `LIKERT_OPTIONS` 수정 (현재 5점)
