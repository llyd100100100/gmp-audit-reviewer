# GMP ALCOA+ Audit Review Assistant - Task Checklist

## Phase 0: Planning
- [x] Define project scope and architecture
- [x] Create implementation plan

## Phase 1: Project Setup
- [x] Create new project folder `c:\Users\so123\gmp-audit-reviewer`
- [x] Create `requirements.txt`
- [x] Create `.env` template
- [x] Create `.gitignore`

## Phase 2: Core Modules
- [x] `auth_utils.py` - Supabase 로그인/회원가입
- [x] `cloud_utils.py` - Supabase Storage/DB 연동 (audit_reviews 테이블)
- [x] `ai_utils.py` - Gemini AI 엔진 (ALCOA+ 특화, 청킹, 멀티청크 머지)
- [x] `prompts/alcoa_prompt.py` - ALCOA+ 심층 프롬프트 + Few-Shot 예시

## Phase 3: UI (app.py)
- [x] 로그인/회원가입 페이지 (Supabase + local fallback)
- [x] 파일 업로드 섹션 (CSV/Excel/TXT/PDF)
- [x] 데이터 프리뷰 (원본 그대로, 마스킹 없음)
- [x] AI 분석 섹션 (Full Audit + Q&A)
- [x] ALCOA+ 항목별 점수 뷰 (9개 항목 metric)
- [x] 리뷰 워크플로우 (Finding 승인/보류/기각)
- [x] 리뷰 결과 Export (CSV/JSON 다운로드)

## Phase 4: Verification
- [/] 로컬 실행 테스트
- [ ] 샘플 audit trail 데이터로 AI 분석 검증
- [ ] Supabase 연동 확인
