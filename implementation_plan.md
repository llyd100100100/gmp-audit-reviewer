# GMP ALCOA+ Audit Review Assistant - 구현 계획서

## 목적
실제 제조 설비(Equipment)에서 추출한 Audit Trail을 업로드하면,
AI(Gemini)가 **ALCOA+** (Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available) 기준과 **21 CFR Part 11** 관점에서 Data Integrity 위반 사항을 자동 분석해주는 **Audit Review Assistant** 시스템.

**기존 `aiauditguide`와의 차이점:**
| 항목 | aiauditguide | gmp-audit-reviewer |
|------|-------------|-------------------|
| PII 마스킹 | ✅ 있음 | ❌ 없음 (실데이터 처리) |
| 목적 | 데모/프로토타입 | 실제 업무 도구 |
| 리뷰 워크플로우 | ❌ 없음 | ✅ 있음 (승인/보류/기각) |
| ALCOA 체크리스트 | 부분 | ✅ 항목별 세분화 |
| 리포트 Export | ❌ 없음 | ✅ CSV/JSON 다운로드 |

---

## 폴더명
`c:\Users\so123\gmp-audit-reviewer`

---

## Proposed Changes

### 프로젝트 초기 설정

#### [DONE] `requirements.txt`
```
streamlit
pandas
google-genai
python-dotenv
tenacity
google-api-core
supabase
openpyxl
pypdf
tabulate
```

#### [DONE] `.env` (템플릿)
```
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
```

---

### 핵심 모듈

#### [NEW] `auth_utils.py`
기존 `aiauditguide/auth_utils.py` 기반 재활용.
- Supabase Auth: 로그인, 회원가입
- 로컬 fallback (Supabase 없을 때)

#### [NEW] `cloud_utils.py`
기존 `aiauditguide/cloud_utils.py` 기반 재활용.
- Supabase Storage: audit trail 파일 백업
- Supabase DB: 리뷰 결과 저장 (`audit_reviews` 테이블)

#### [NEW] `ai_utils.py`
**ALCOA+ 특화 AI 엔진** (기존 대비 크게 개선):
- ALCOA+ 9개 항목 각각에 대한 **개별 평가 점수** 반환
- `A` Attributable, `L` Legible, `C` Contemporaneous, `O` Original, `A` Accurate, `+` Complete/Consistent/Enduring/Available
- JSON 출력 스키마: `alcoa_scores`, `findings`, `executive_summary`, `audit_readiness_score`
- Sliding Window 청킹 유지
- 반환값에 **기록 Gap 자동 탐지** 포함 (Timestamp 간격 이상, 수정 이력 없는 삭제 등)

#### [NEW] `prompts/alcoa_prompt.py`
ALCOA+ 심층 프롬프트:
- ALCOA 항목별 검사 기준 (예: "Contemporaneous - 기록 시점 vs 실제 작업 시점 비교")
- Few-Shot 예시 (위반 사례 포함)
- Equipment 타입별 특화 예시 (HPLC, 저울, 오토클레이브 등)

---

### 메인 UI

#### [NEW] `app.py`
Streamlit 기반, **4개 헤더 섹션**:

**① 로그인/회원가입** (사이드바)
- Supabase 인증
- 사용자/회사명 표시

**② 파일 업로드 & 데이터 프리뷰**
- CSV / Excel / PDF / TXT 지원
- 원본 데이터 그대로 표시 (마스킹 없음)
- 컬럼 자동 인식 및 Timestamp 컬럼 감지

**③ AI ALCOA+ 분석**
```
[Run ALCOA+ Audit] 버튼
  └─ ALCOA 항목별 점수 레이더 차트 (plotly 없이 st.metric으로 대체)
  └─ Findings 테이블 (Severity / ALCOA항목 / 설명 / 근거)
  └─ Executive Summary
  └─ Audit Readiness Score (0-100)
```

**④ 리뷰 워크플로우**
- Finding 별 상태 지정: `✅ Accepted` / `⏳ Pending` / `❌ Rejected`
- 리뷰어 코멘트 입력
- 리뷰 완료 시 `Export Review` 버튼 → JSON/CSV 다운로드

---

## Verification Plan

### 자동 테스트
없음 (신규 프로젝트, Streamlit UI 위주이므로 수동 검증)

### 수동 검증
1. **로컬 실행**: 프로젝트 폴더에서 `streamlit run app.py` 실행
2. **로그인 테스트**: Supabase 없는 환경에서 `admin/admin` fallback으로 접근 확인
3. **파일 업로드**: `aiauditguide/test_data/` 의 기존 CSV 파일을 업로드하여 파싱 확인
4. **AI 분석**: GEMINI_API_KEY 설정 후 "Run ALCOA+ Audit" 실행, JSON 결과 확인
5. **리뷰 워크플로우**: Finding에 상태 지정 후 Export 버튼 → CSV 다운로드 확인
