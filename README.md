# 🔬 GMP ALCOA+ Audit Review Assistant

제조 설비(Equipment)에서 추출한 Audit Trail(감사 증적) 데이터를 AI(Gemini)를 통해 자동으로 검토하고, **ALCOA+** 원칙 및 **21 CFR Part 11 / EU GMP Annex 11** 데이터 무결성(Data Integrity) 기준에 따라 위반 사항을 식별하는 B2B SaaS 시스템입니다.

---

## 🏗 프로젝트 특성 및 아키텍처

이 프로젝트는 **Python & Streamlit**을 기반으로 한 빠르고 직관적인 사용자 인터페이스를 가지며, 파일 처리 및 데이터 분석에 **Pandas**를, 대규모 언어 모델 연동에 **Google GenAI (Gemini 2.0)** 를 사용합니다. 데이터 백업 및 리뷰 이력 저장을 위해 **Supabase**(PostgreSQL & Storage)를 연동할 수 있도록 설계되었습니다.

특히 긴 Audit Trail 데이터를 한 번에 처리하기 위한 **Sliding Window Chunking** 기법을 적용하여 AI 토큰 한계(Context Window)를 우회하면서도 레코드 간의 무결성을 잃지 않도록 구성되었습니다.

---

## 📂 파일 및 폴더 구조 설명

### 1. 메인 애플리케이션 (UI Layer)
- **`app.py`**
  - Streamlit 기반의 메인 UI를 담당합니다.
  - 사이드바(로그인/회원가입/장비 선택), 파일 업로드 및 데이터 프리뷰 영역, AI 분석 실행 차트 표출 영역, 리뷰 워크플로우(상태 지정) 기능을 통합 관리하는 컨트롤 타워입니다.

### 2. 핵심 비즈니스 로직 (Core Modules)
- **`ai_utils.py`**
  - Gemini API 연동 모듈입니다.
  - 수천~수만 줄의 Audit Trail 데이터를 설정된 단위(`MAX_CHUNK_ROWS`)로 쪼개고 겹쳐서 분석하는 **청킹(Chunking)** 모직, 여러 청크의 분석 결과(JSON)를 하나로 취합하는 **Merge** 로직, 결과에 대한 Q&A 기능이 포함되어 있습니다.
- **`auth_utils.py`**
  - Supabase를 활용한 로그인(Sign In) 및 회원가입(Sign Up) 로직을 관리합니다.
  - `.env`에 키가 없을 경우를 대비하여 `admin / admin`으로 접속할 수 있는 테스트 환경(Fallback)이 적용되어 있습니다.
- **`cloud_utils.py`**
  - Supabase Database(리뷰 이력 저장) 및 Storage(업로드된 파일 백업 저장) 기능을 담당합니다.
  - 로컬 환경 및 클라우드 배포 환경(`st.secrets`) 모두에서 환경변수를 유연하게 탐색합니다.

### 3. 프롬프트 라이브러리 (Prompt Engineering)
- **`prompts/alcoa_prompt.py`**
  - AI 분석의 핵심이 되는 시스템 프롬프트가 정의되어 있습니다.
  - ALCOA+ 9개 항목(Attributable, Legible, Contemporaneous 등)에 대한 구체적인 **정의**, **평가 규칙**, **Few-Shot (위반 사례 예시)** 이 담겨 있어 Gemini가 일관된 JSON 스키마로 답변을 도출하도록 유도합니다.

### 4. 설정 및 배포 파일 (Config & Deployment)
- **`requirements.txt`**
  - 애플리케이션 구동에 필요한 Python 패키지 의존성 목록입니다. (Pandas, Streamlit, google-genai, supabase 등)
- **`.env.example`**
  - 로컬에서 사용할 환경변수 템플릿 파일입니다.
- **`Dockerfile` / `.dockerignore`**
  - 클라우드나 온프레미스 서버 환경에 독립적으로 배포하기 위한 도커 빌드 설정 파일입니다.
- **`.github/workflows/deploy.yml`**
  - 코드를 GitHub에 푸시(Push)하면 자동으로 도커 이미지를 빌드하여 GitHub Container Registry(GHCR)에 올려주는 CI/CD 배포 파이프라인 자동화 스크립트입니다.

---

## ⚡️ 주요 워크플로우

1. **로그인 / 파일 업로드**: 사용자가 로그인 후 CSV, Excel, TXT, PDF 형태의 Audit Trail 문서를 업로드.
2. **AI 데이터 분석**: `ai_utils.py` 모듈이 작동해 문서를 청킹하여 Gemini에 전송하고, `alcoa_prompt.py`의 기준에 맞춰 ALCOA+ 항목별 평가 점수 및 위반 사항(Findings)을 JSON으로 반환.
3. **리뷰 및 Q&A**: 분석 결과를 Streamlit UI로 확인하며, 특정 로그에 대한 추가 질문(인터랙티브 Q&A) 진행.
4. **결정 및 내보내기**: 위반 사항(Finding)을 Accepted / Rejected 등 상태로 분류하고 리뷰 의견 작성 후 CSV 또는 JSON 형식의 보고서 다운로드 및 DB에 상태 보존.
