"""
AI Engine for GMP ALCOA+ Audit Review
Uses Google Gemini via google-genai SDK
"""

import os
import json
import math
import re
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from prompts.alcoa_prompt import build_audit_prompt, build_qa_prompt

load_dotenv()

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
MODEL_NAME = "gemini-2.0-flash"
MAX_CHUNK_ROWS = 200       # rows per chunk for audit trail
CHUNK_OVERLAP_ROWS = 20    # sliding window overlap


# ─────────────────────────────────────────────
# Gemini Client
# ─────────────────────────────────────────────
def _get_api_key() -> str | None:
    # Try streamlit secrets first (best for deployment)
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # Fallback to .env (best for local)
    return os.getenv("GEMINI_API_KEY")

def _get_client():
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env or st.secrets")
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai package not installed")
    return genai.Client(api_key=api_key)


# ─────────────────────────────────────────────
# Chunking Helpers
# ─────────────────────────────────────────────
def _chunk_text_by_rows(lines: list[str], chunk_size: int, overlap: int) -> list[str]:
    """Splits a list of text lines into overlapping chunks."""
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(lines), step):
        chunk = lines[i: i + chunk_size]
        chunks.append("\n".join(chunk))
        if i + chunk_size >= len(lines):
            break
    return chunks


def _text_to_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


# ─────────────────────────────────────────────
# JSON Parsing
# ─────────────────────────────────────────────
def _extract_json(raw: str) -> dict:
    """Extracts and parses JSON from model response, tolerating markdown fences."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find first { ... } block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Cannot parse JSON from model response:\n{raw[:500]}")


# ─────────────────────────────────────────────
# Single-Chunk Audit
# ─────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _audit_chunk(client, chunk_text: str, equipment_type: str) -> dict:
    prompt = build_audit_prompt(chunk_text, equipment_type)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=4096,
        )
    )
    return _extract_json(response.text)


# ─────────────────────────────────────────────
# Merge Results from Multiple Chunks
# ─────────────────────────────────────────────
def _merge_results(results: list[dict]) -> dict:
    """Aggregates ALCOA scores and findings from multiple chunk results."""
    if not results:
        return {}

    # Average ALCOA scores
    alcoa_keys = ["Attributable", "Legible", "Contemporaneous", "Original", "Accurate",
                  "Complete", "Consistent", "Enduring", "Available"]
    avg_scores = {}
    for k in alcoa_keys:
        scores = [r.get("alcoa_scores", {}).get(k, 7) for r in results if r.get("alcoa_scores")]
        avg_scores[k] = round(sum(scores) / len(scores), 1) if scores else 7

    # Merge findings with re-indexed IDs
    all_findings = []
    idx = 1
    seen = set()  # deduplicate near-identical findings
    for r in results:
        for f in r.get("findings", []):
            key = (f.get("alcoa_item"), f.get("severity"), f.get("description", "")[:60])
            if key not in seen:
                seen.add(key)
                f["id"] = idx
                all_findings.append(f)
                idx += 1

    # Severity distribution for score
    severity_count = {"Critical": 0, "Major": 0, "Minor": 0, "Observation": 0}
    for f in all_findings:
        sev = f.get("severity", "Observation")
        if sev in severity_count:
            severity_count[sev] += 1

    score = 100
    score -= severity_count["Critical"] * 15
    score -= severity_count["Major"] * 8
    score -= severity_count["Minor"] * 3
    score = max(0, score)

    # Combine executive summaries
    summaries = [r.get("executive_summary", "") for r in results if r.get("executive_summary")]
    combined_summary = " ".join(summaries) if len(summaries) == 1 else f"[{len(results)}개 구간 분석 종합] " + summaries[0]

    gap_summaries = [r.get("gap_summary", "") for r in results if r.get("gap_summary")]
    combined_gap = " | ".join(gap_summaries)

    return {
        "alcoa_scores": avg_scores,
        "findings": all_findings,
        "gap_summary": combined_gap,
        "executive_summary": combined_summary,
        "audit_readiness_score": score,
        "audit_readiness_comment": results[-1].get("audit_readiness_comment", ""),
        "severity_distribution": severity_count,
        "chunks_analyzed": len(results),
    }


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
def run_alcoa_audit(audit_text: str, equipment_type: str = "General") -> tuple[bool, dict | str]:
    """
    Main entry point. Accepts raw audit trail text (CSV rows as string).
    Returns (success: bool, result: dict | error_message: str)
    """
    try:
        client = _get_client()
    except (ValueError, ImportError) as e:
        return False, str(e)

    lines = _text_to_lines(audit_text)
    if not lines:
        return False, "업로드된 파일에 분석 가능한 텍스트가 없습니다."

    # If small enough, analyze as single chunk
    if len(lines) <= MAX_CHUNK_ROWS:
        chunks = ["\n".join(lines)]
    else:
        chunks = _chunk_text_by_rows(lines, MAX_CHUNK_ROWS, CHUNK_OVERLAP_ROWS)

    results = []
    errors = []
    for i, chunk in enumerate(chunks):
        try:
            res = _audit_chunk(client, chunk, equipment_type)
            results.append(res)
        except Exception as e:
            errors.append(f"Chunk {i+1}: {str(e)}")

    if not results:
        return False, f"AI 분석 실패: {'; '.join(errors)}"

    merged = _merge_results(results)
    if errors:
        merged["warnings"] = errors

    return True, merged


def run_qa(question: str, audit_data_summary: str, findings_text: str) -> tuple[bool, str]:
    """
    Interactive Q&A about the audit findings.
    Returns (success: bool, answer: str)
    """
    try:
        client = _get_client()
    except (ValueError, ImportError) as e:
        return False, str(e)

    try:
        prompt = build_qa_prompt(question, audit_data_summary, findings_text)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
            )
        )
        return True, response.text
    except Exception as e:
        return False, f"AI Q&A 오류: {str(e)}"
