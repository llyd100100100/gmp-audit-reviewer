"""
ALCOA+ Prompt Library for GMP Audit Trail Analysis
Covers: Attributable, Legible, Contemporaneous, Original, Accurate,
        Complete, Consistent, Enduring, Available
Reference: 21 CFR Part 11, EU GMP Annex 11, MHRA Data Integrity Guidance
"""

# ─────────────────────────────────────────────
# ALCOA+ 항목 정의 (영/한)
# ─────────────────────────────────────────────
ALCOA_DEFINITIONS = {
    "Attributable": "기록을 생성한 사람(또는 시스템)이 명확히 식별되어야 함. 전자서명, 사용자 ID, 작업자 이니셜 포함.",
    "Legible": "기록이 명확하고 읽을 수 있어야 하며 영구적이어야 함. 수정 시 원본이 읽을 수 있는 상태 유지.",
    "Contemporaneous": "기록은 활동이 발생한 시점과 동시에 작성되어야 함. 사후 기록(backdating) 금지.",
    "Original": "원본 기록 또는 인증된 사본만 유효. 재기록(rewriting) 시 원본 첨부 필요.",
    "Accurate": "기록된 데이터가 실제 측정값, 관찰값과 일치해야 함. 계산 오류, 단위 불일치 주의.",
    "Complete": "모든 필수 항목이 기록되어야 함. 빈 칸(blank), 생략, 누락된 서명 주의.",
    "Consistent": "동일한 데이터가 여러 기록에서 일관되어야 함. 상호 참조 불일치 주의.",
    "Enduring": "기록이 보존 기간 동안 유지되어야 함. 열화, 삭제, 덮어쓰기 위험 점검.",
    "Available": "권한 있는 사람에게 기록이 접근 가능해야 함. 백업, 재해 복구 계획 포함.",
}

# ─────────────────────────────────────────────
# Few-Shot 위반 사례 예시
# ─────────────────────────────────────────────
FEW_SHOT_EXAMPLES = """
=== 위반 사례 예시 (Few-Shot) ===

[사례 1] Attributable 위반
- 레코드: Action=Parameter Change, User=SYSTEM, Timestamp=2024-01-15 03:22:10
- 문제: 심야 시간대 시스템 계정으로 파라미터 변경. 실제 작업자 불명확.
- Finding: 심야 3시 시스템 계정 파라미터 변경 — 작업자 신원 추적 불가. Attributable 위반.
- Severity: Critical

[사례 2] Contemporaneous 위반
- 레코드: Action=Analysis Result Entered, Timestamp=2024-01-20 17:45, Analysis Time=2024-01-20 09:30
- 문제: 분석 완료 후 8시간 이상 지나서 결과 입력. 동시 기록 원칙 위반.
- Finding: 분석 완료 8시간 후 결과 입력 — 사후 기록(Backdating) 의심. Contemporaneous 위반.
- Severity: Major

[사례 3] Complete 위반
- 레코드: Action=Batch Release, Reviewer=, Timestamp=2024-02-01 14:00
- 문제: 배치 릴리즈 기록에 검토자(Reviewer) 서명란 공백.
- Finding: 배치 릴리즈 기록에 검토자 서명 누락 — Complete 위반.
- Severity: Major

[사례 4] Original 위반
- 레코드: Action=Result Rewritten, Old Value=98.2, New Value=99.1, Reason=, User=admin01
- 문제: 결과값 재기록 시 변경 사유 미기재. 원본 데이터 탈락 여부 불명확.
- Finding: 결과값 재기록 사유 미입력 — Original 및 Accurate 위반 가능성.
- Severity: Major

[사례 5] Consistent 위반
- 레코드 A: Weight=5.023g (Balance Log), 레코드 B: Weight=5.031g (Batch Record)
- 문제: 동일 측정에 대한 두 기록 값 불일치 (차이: 0.008g).
- Finding: 저울 로그와 배치 기록 중량 불일치 — Consistent 위반.
- Severity: Critical
"""

# ─────────────────────────────────────────────
# 메인 분석 프롬프트 빌더
# ─────────────────────────────────────────────

def build_audit_prompt(chunk_text: str, equipment_type: str = "General") -> str:
    """
    Returns the full ALCOA+ audit analysis prompt for a given chunk of audit trail data.
    """
    alcoa_criteria = "\n".join(
        f"- **{k}**: {v}" for k, v in ALCOA_DEFINITIONS.items()
    )

    prompt = f"""
You are a senior GMP Data Integrity auditor with expertise in 21 CFR Part 11, EU GMP Annex 11, and MHRA Data Integrity Guidance.

## Equipment Type
{equipment_type}

## ALCOA+ Evaluation Criteria
{alcoa_criteria}

## Reference Violation Examples
{FEW_SHOT_EXAMPLES}

## Audit Trail Data to Analyze
```
{chunk_text}
```

## Task
Perform a thorough ALCOA+ Data Integrity audit on the above audit trail records.

### Output Format (STRICT JSON — no markdown outside the JSON block)
Return ONLY a valid JSON object with the following schema:

{{
  "alcoa_scores": {{
    "Attributable": <0-10>,
    "Legible": <0-10>,
    "Contemporaneous": <0-10>,
    "Original": <0-10>,
    "Accurate": <0-10>,
    "Complete": <0-10>,
    "Consistent": <0-10>,
    "Enduring": <0-10>,
    "Available": <0-10>
  }},
  "findings": [
    {{
      "id": <integer, 1-based>,
      "alcoa_item": "<ALCOA+ category>",
      "severity": "<Critical | Major | Minor | Observation>",
      "description": "<clear description of the finding in Korean>",
      "evidence": "<ALL specific record(s), timestamps, or field(s) from the data that serve as evidence. If there are multiple related records, cite ALL of them.>",
      "recommendation": "<corrective action recommendation in Korean>"
    }}
  ],
  "gap_summary": "<brief list of key gap patterns found, in Korean>",
  "executive_summary": "<overall narrative summary in Korean, 3-5 sentences>",
  "audit_readiness_score": <0-100>,
  "audit_readiness_comment": "<brief Korean comment on overall audit readiness>"
}}

### Scoring Rules
- ALCOA scores: 10 = fully compliant, 0 = critical systemic failure
- Audit readiness score: weighted average considering severity distribution
  - Each Critical finding: -15 pts from 100
  - Each Major finding: -8 pts
  - Each Minor finding: -3 pts
  - (Minimum score: 0)
- If data is insufficient to evaluate an ALCOA item, score it 7 and note it in findings as Observation.

### Important
- Be precise and COMPREHENSIVE. Reference actual field values, timestamps, and user IDs.
- **CRITICAL**: If a finding is based on multiple log entries (e.g., a trend of missing signatures, or multiple conflicting timestamps), you MUST list ALL related lines / records in the "evidence" field. Do not just cite the first one.
- Do NOT hallucinate findings that are not supported by the data.
- If the data looks clean for a given ALCOA category, score it 9-10 and skip that category in findings.
- Output ONLY the raw JSON. No extra text, no markdown code fences.
"""
    return prompt.strip()


def build_qa_prompt(question: str, audit_data_summary: str, previous_findings: str) -> str:
    """
    Returns a prompt for interactive Q&A about the audit findings.
    """
    prompt = f"""
You are a GMP Data Integrity expert. The user has already run an ALCOA+ audit and wants to ask a follow-up question.

## Audit Data Summary
{audit_data_summary}

## Previous Audit Findings
{previous_findings}

## User Question
{question}

Answer in Korean. Be specific, cite relevant data or findings where possible.
If the question is outside the scope of the provided data, say so clearly.
"""
    return prompt.strip()
