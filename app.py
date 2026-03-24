"""
GMP ALCOA+ Audit Review Assistant
Streamlit UI — Main Application
"""

import streamlit as st
import pandas as pd
import json
import io
import datetime

from auth_utils import AuthManager
from cloud_utils import CloudManager
from ai_utils import run_alcoa_audit, run_qa

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="GMP ALCOA+ Audit Reviewer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "logged_in": False,
        "user": None,
        "uploaded_df": None,
        "audit_text": "",
        "audit_result": None,
        "review_states": {},   # {finding_id: {"status": str, "comment": str}}
        "qa_history": [],
        "equipment_type": "General",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

auth = AuthManager()
cloud = CloudManager()

# ─────────────────────────────────────────────
# Custom CSS — Light & Refined Theme
# ─────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    /* ── Base ── */
    html, body, .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f0f4f8;
        color: #1e293b;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(160deg, #1e3a5f 0%, #2563eb 100%);
        color: #fff;
    }
    [data-testid="stSidebar"] * { color: #fff !important; }
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background: rgba(255,255,255,0.15) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        color: #fff !important;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input::placeholder { color: rgba(255,255,255,0.55) !important; }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(255,255,255,0.15) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] [data-baseweb="tab"] {
        background: rgba(255,255,255,0.12) !important;
        border-radius: 8px 8px 0 0;
    }
    [data-testid="stSidebar"] [aria-selected="true"] {
        background: rgba(255,255,255,0.25) !important;
        font-weight: 600;
    }

    /* ── Main Area ── */
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }

    /* Top gradient banner */
    .app-banner {
        background: linear-gradient(120deg, #1e3a5f 0%, #2563eb 60%, #60a5fa 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 28px;
        box-shadow: 0 4px 20px rgba(37,99,235,0.25);
    }
    .app-banner h1 { font-size: 1.6rem; font-weight: 700; margin: 0 0 4px 0; }
    .app-banner p  { margin: 0; opacity: 0.85; font-size: 0.95rem; }

    /* Section card wrapper */
    .section-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 20px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.05);
    }

    /* Section header */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1e3a5f;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 8px;
        margin-bottom: 16px;
        letter-spacing: 0.01em;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #f8faff;
        border: 1px solid #dbeafe;
        border-radius: 10px;
        padding: 10px 12px;
        text-align: center;
    }
    [data-testid="metric-container"] label { color: #64748b !important; font-size: 0.75rem !important; }
    [data-testid="stMetricValue"] { color: #1e3a5f !important; font-weight: 700 !important; }

    /* Score gauge */
    .score-ring {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        padding: 20px 0 10px;
    }
    .score-num { font-size: 4rem; font-weight: 800; line-height: 1; }
    .score-label { font-size: 0.9rem; color: #64748b; margin-top: 4px; }

    /* Finding cards */
    .finding-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #93c5fd;
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    .finding-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
    .finding-critical { border-left-color: #ef4444; background: #fff5f5; }
    .finding-major    { border-left-color: #f97316; background: #fff8f5; }
    .finding-minor    { border-left-color: #eab308; background: #fefce8; }
    .finding-obs      { border-left-color: #94a3b8; background: #f8fafc; }

    .finding-title { font-weight: 700; font-size: 0.95rem; color: #1e293b; margin-bottom: 6px; }
    .finding-desc  { font-size: 0.9rem; color: #334155; margin-bottom: 6px; }
    .finding-meta  { font-size: 0.8rem; color: #64748b; }
    .finding-rec   { font-size: 0.82rem; color: #2563eb; margin-top: 4px; }

    /* Severity chips */
    .chip {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .chip-critical { background: #fee2e2; color: #b91c1c; }
    .chip-major    { background: #ffedd5; color: #c2410c; }
    .chip-minor    { background: #fef9c3; color: #92400e; }
    .chip-obs      { background: #f1f5f9; color: #475569; }

    /* Severity summary cards */
    .sev-card {
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        font-weight: 700;
    }
    .sev-critical { background: #fee2e2; color: #b91c1c; }
    .sev-major    { background: #ffedd5; color: #c2410c; }
    .sev-minor    { background: #fef9c3; color: #92400e; }
    .sev-obs      { background: #f1f5f9; color: #475569; }
    .sev-num { font-size: 2rem; line-height: 1; }
    .sev-lbl { font-size: 0.8rem; margin-top: 4px; }

    /* Dividers */
    hr { border-color: #e2e8f0 !important; }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1e40af) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.4rem !important;
        box-shadow: 0 2px 8px rgba(37,99,235,0.35) !important;
        transition: all 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.45) !important;
    }

    /* Upload zone */
    [data-testid="stFileUploader"] { background: #f8faff; border-radius: 12px; }

    /* Expander */
    [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
    }

    /* Chat */
    [data-testid="stChatMessage"] { background: #f8faff; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ① 사이드바 — 로그인 / 회원가입
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 GMP Audit Reviewer")
    st.markdown("---")

    if not st.session_state.logged_in:
        tab_login, tab_register = st.tabs(["로그인", "회원가입"])

        with tab_login:
            st.markdown("##### 계정 로그인")
            email = st.text_input("이메일 / ID", key="login_email", placeholder="admin")
            password = st.text_input("비밀번호", type="password", key="login_pw", placeholder="admin")
            if st.button("🔑 로그인", use_container_width=True):
                ok, result = auth.login_user(email, password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user = result
                    st.rerun()
                else:
                    st.error(str(result))

        with tab_register:
            st.markdown("##### 신규 계정")
            reg_name  = st.text_input("이름", key="reg_name")
            reg_email = st.text_input("이메일", key="reg_email")
            reg_pw    = st.text_input("비밀번호", type="password", key="reg_pw")
            if st.button("📝 회원가입", use_container_width=True):
                ok, msg = auth.register_user(reg_email, reg_pw, reg_name)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    else:
        user = st.session_state.user
        if isinstance(user, dict):
            display_name = user.get("user_metadata", {}).get("full_name", user.get("email", "User"))
            display_email = user.get("email", "")
        else:
            display_name = getattr(getattr(user, "user_metadata", None), "full_name", None) or getattr(user, "email", "User")
            display_email = getattr(user, "email", "")

        st.success(f"✅ {display_name}")
        st.caption(display_email)

        st.markdown("---")
        st.markdown("##### Equipment Type")
        eq_types = ["General", "HPLC", "Balance / Weighing", "Autoclave / Sterilizer",
                    "Bioreactor", "Dissolution Tester", "GC / LC-MS", "Cleanroom / HVAC", "Other"]
        st.session_state.equipment_type = st.selectbox("설비 종류", eq_types, label_visibility="collapsed")

        st.markdown("---")
        if st.button("🚪 로그아웃", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ─────────────────────────────────────────────
# Not logged in → show landing
# ─────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("""
    <div class="app-banner">
      <h1>🔬 GMP ALCOA+ Audit Review Assistant</h1>
      <p>실제 제조 Audit Trail의 Data Integrity를 AI로 자동 검토합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    ### 주요 기능
    | 기능 | 설명 |
    |------|------|
    | 📂 파일 업로드 | CSV / Excel / TXT / PDF 지원 |
    | 🤖 ALCOA+ AI 분석 | Gemini 기반 9개 항목 자동 평가 |
    | 🔍 Finding 분류 | Critical / Major / Minor / Observation |
    | ✅ 리뷰 워크플로우 | 승인 / 보류 / 기각 상태 관리 |
    | 📤 Export | JSON / CSV 다운로드 |

    👈 **사이드바에서 로그인 후 시작하세요.** 테스트: `admin` / `admin`
    """)
    st.stop()

# ─────────────────────────────────────────────
# ② 파일 업로드 & 데이터 프리뷰
# ─────────────────────────────────────────────
st.markdown("""
<div class="app-banner" style="padding:18px 28px; margin-bottom:20px;">
  <h1 style="font-size:1.2rem;">🔬 GMP ALCOA+ Audit Review Assistant</h1>
  <p>ALCOA+ Data Integrity 자동 분석 · 21 CFR Part 11 / EU GMP Annex 11</p>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="section-header">📂 Audit Trail 업로드</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "CSV, Excel, TXT, PDF 파일을 드래그하거나 선택하세요",
    type=["csv", "xlsx", "xls", "txt", "pdf"],
    label_visibility="collapsed"
)

if uploaded_file:
    fname = uploaded_file.name
    ext = fname.rsplit(".", 1)[-1].lower()

    try:
        if ext == "csv":
            df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            raw_text = df.to_csv(index=False)

        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(uploaded_file)
            raw_text = df.to_csv(index=False)

        elif ext == "txt":
            content = uploaded_file.read().decode("utf-8-sig", errors="replace")
            df = pd.DataFrame({"Raw Text": content.splitlines()})
            raw_text = content

        elif ext == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(uploaded_file)
                content = "\n".join(p.extract_text() or "" for p in reader.pages)
                df = pd.DataFrame({"Extracted Text": content.splitlines()})
                raw_text = content
            except Exception as e:
                st.error(f"PDF 파싱 오류: {e}")
                st.stop()
        else:
            st.error("지원하지 않는 파일 형식입니다.")
            st.stop()

        st.session_state.uploaded_df = df
        st.session_state.audit_text = raw_text

    except Exception as e:
        st.error(f"파일 파싱 오류: {e}")
        st.stop()

if st.session_state.uploaded_df is not None:
    df = st.session_state.uploaded_df
    total_rows = len(df)

    with st.expander(f"📋 데이터 프리뷰 ({total_rows:,} rows)", expanded=True):
        st.dataframe(df.head(100), use_container_width=True, height=280)
        if total_rows > 100:
            st.caption(f"상위 100행 표시 중 (전체 {total_rows:,}행)")

    # Timestamp column detection
    ts_cols = [c for c in df.columns if any(k in c.lower() for k in ["time", "date", "ts", "timestamp"])]
    if ts_cols:
        st.info(f"⏱ Timestamp 컬럼 감지: **{', '.join(ts_cols)}**")

# ─────────────────────────────────────────────
# ③ AI ALCOA+ 분석
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header" style="font-size:1.2rem;">🤖 ALCOA+ AI 분석</div>', unsafe_allow_html=True)

if st.session_state.uploaded_df is None:
    st.warning("먼저 Audit Trail 파일을 업로드하세요.")
else:
    col_run, col_eq = st.columns([3, 2])
    with col_eq:
        st.markdown(f"**설비 타입:** `{st.session_state.equipment_type}`  \n(사이드바에서 변경)")

    with col_run:
        run_btn = st.button("▶ Run ALCOA+ Audit", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("🔍 Gemini AI가 ALCOA+ 분석 중... (데이터 크기에 따라 수십 초 소요)"):
            ok, result = run_alcoa_audit(
                st.session_state.audit_text,
                equipment_type=st.session_state.equipment_type
            )

        if ok:
            st.session_state.audit_result = result
            st.session_state.review_states = {}
            st.success("✅ 분석 완료!")
        else:
            st.error(f"❌ 분석 실패: {result}")

    # ── Display Results ──────────────────────
    if st.session_state.audit_result:
        res = st.session_state.audit_result

        # Audit Readiness Score
        score = res.get("audit_readiness_score", 0)
        score_color = "#16a34a" if score >= 80 else "#d97706" if score >= 60 else "#dc2626"
        score_bg    = "#f0fdf4" if score >= 80 else "#fffbeb" if score >= 60 else "#fef2f2"
        st.markdown(
            f"""<div style="background:{score_bg}; border:1px solid {score_color}33;
                border-radius:16px; text-align:center; padding:28px 0; margin:16px 0;">
              <div style="font-size:4rem; font-weight:800; color:{score_color}; line-height:1;">{score}</div>
              <div style="font-size:1rem; color:#64748b; margin-top:4px;">/ 100 &nbsp;·&nbsp; Audit Readiness Score</div>
              <div style="font-size:0.9rem; color:#475569; margin-top:8px;">{res.get("audit_readiness_comment", "")}</div>
            </div>""",
            unsafe_allow_html=True
        )

        # ALCOA Scores
        st.markdown('<div class="section-header">📊 ALCOA+ 항목별 점수</div>', unsafe_allow_html=True)
        alcoa_scores = res.get("alcoa_scores", {})
        alcoa_order = ["Attributable", "Legible", "Contemporaneous", "Original", "Accurate",
                       "Complete", "Consistent", "Enduring", "Available"]
        cols = st.columns(len(alcoa_order))
        for col, key in zip(cols, alcoa_order):
            val = alcoa_scores.get(key, "-")
            delta = None
            if isinstance(val, (int, float)):
                delta = "▲" if val >= 8 else ("▼" if val < 6 else "–")
            col.metric(label=key[:4], value=val, delta=delta)

        # Severity Summary
        sev = res.get("severity_distribution", {})
        st.markdown('<div class="section-header" style="margin-top:20px;">🚨 Severity 요약</div>', unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.markdown(f'<div class="sev-card sev-critical"><div class="sev-num">{sev.get("Critical", 0)}</div><div class="sev-lbl">🔴 Critical</div></div>', unsafe_allow_html=True)
        sc2.markdown(f'<div class="sev-card sev-major"><div class="sev-num">{sev.get("Major", 0)}</div><div class="sev-lbl">🟠 Major</div></div>', unsafe_allow_html=True)
        sc3.markdown(f'<div class="sev-card sev-minor"><div class="sev-num">{sev.get("Minor", 0)}</div><div class="sev-lbl">🟡 Minor</div></div>', unsafe_allow_html=True)
        sc4.markdown(f'<div class="sev-card sev-obs"><div class="sev-num">{sev.get("Observation", 0)}</div><div class="sev-lbl">⚪ Observation</div></div>', unsafe_allow_html=True)

        # Executive Summary
        with st.expander("📝 Executive Summary", expanded=True):
            st.markdown(res.get("executive_summary", ""))
            if res.get("gap_summary"):
                st.markdown("**Gap 패턴:** " + res.get("gap_summary", ""))

        # Findings
        findings = res.get("findings", [])
        if findings:
            st.markdown(f'<div class="section-header" style="margin-top:16px;">🔎 Findings ({len(findings)}건)</div>', unsafe_allow_html=True)

            severity_colors = {"Critical": "finding-critical", "Major": "finding-major",
                               "Minor": "finding-minor", "Observation": "finding-obs"}
            chip_classes    = {"Critical": "chip-critical", "Major": "chip-major",
                               "Minor": "chip-minor", "Observation": "chip-obs"}

            for f in findings:
                fid       = f.get("id", "?")
                sev_label = f.get("severity", "Observation")
                card_cls  = severity_colors.get(sev_label, "finding-obs")
                chip_cls  = chip_classes.get(sev_label, "chip-obs")

                st.markdown(
                    f"""<div class="finding-card {card_cls}">
                      <div class="finding-title">
                        <span class="chip {chip_cls}">{sev_label}</span>
                        Finding #{fid} &nbsp;·&nbsp; {f.get("alcoa_item", "")}
                      </div>
                      <div class="finding-desc">{f.get("description", "")}</div>
                      <div class="finding-meta">📌 근거: {f.get("evidence", "")}</div>
                      <div class="finding-rec">💡 권고: {f.get("recommendation", "")}</div>
                    </div>""",
                    unsafe_allow_html=True
                )

        # Q&A
        st.markdown("---")
        st.markdown("## 💬 AI Q&A (인터랙티브)")
        user_q = st.text_input("분석 결과에 대해 추가 질문을 입력하세요", key="qa_input",
                               placeholder="예: 심야 시간대 시스템 계정 변경이 왜 문제인가요?")
        if st.button("질문하기", key="qa_btn") and user_q.strip():
            findings_text = json.dumps(findings, ensure_ascii=False, indent=2)
            summary_text = res.get("executive_summary", "")
            with st.spinner("AI 답변 생성 중..."):
                ok_qa, answer = run_qa(user_q, summary_text, findings_text)
            if ok_qa:
                st.session_state.qa_history.append({"q": user_q, "a": answer})
            else:
                st.error(answer)

        for item in reversed(st.session_state.qa_history):
            st.chat_message("user").write(item["q"])
            st.chat_message("assistant").write(item["a"])

# ─────────────────────────────────────────────
# ④ 리뷰 워크플로우
# ─────────────────────────────────────────────
if st.session_state.audit_result and st.session_state.audit_result.get("findings"):
    findings = st.session_state.audit_result["findings"]

    st.markdown("---")
    st.markdown('<div class="section-header" style="font-size:1.2rem;">✅ 리뷰 워크플로우</div>', unsafe_allow_html=True)
    st.caption("각 Finding에 대해 상태를 지정하고 코멘트를 입력하세요.")

    STATUS_OPTIONS = ["⏳ Pending", "✅ Accepted", "❌ Rejected"]
    severity_icons  = {"Critical": "🔴", "Major": "🟠", "Minor": "🟡", "Observation": "⚪"}

    for f in findings:
        fid = str(f.get("id", "?"))
        sev = f.get("severity", "Observation")
        icon = severity_icons.get(sev, "⚪")

        with st.container():
            col_info, col_status, col_comment = st.columns([4, 2, 4])
            with col_info:
                st.markdown(f"**{icon} #{fid} [{sev}]** — {f.get('alcoa_item', '')}  \n{f.get('description', '')[:80]}…")
            with col_status:
                current = st.session_state.review_states.get(fid, {}).get("status", "⏳ Pending")
                status = st.selectbox("상태", STATUS_OPTIONS,
                                      index=STATUS_OPTIONS.index(current),
                                      key=f"status_{fid}",
                                      label_visibility="collapsed")
            with col_comment:
                comment = st.text_input("코멘트", key=f"comment_{fid}", label_visibility="collapsed",
                                        placeholder="리뷰어 코멘트 (선택)")

            st.session_state.review_states[fid] = {"status": status, "comment": comment}
            st.markdown("<hr style='border-color:#e2e8f0; margin:6px 0'>", unsafe_allow_html=True)

    # Export
    st.markdown("---")
    st.markdown("### 📤 리뷰 결과 Export")

    export_data = []
    for f in findings:
        fid = str(f.get("id", "?"))
        rv = st.session_state.review_states.get(fid, {})
        export_data.append({
            "Finding #": fid,
            "ALCOA Item": f.get("alcoa_item", ""),
            "Severity": f.get("severity", ""),
            "Description": f.get("description", ""),
            "Evidence": f.get("evidence", ""),
            "Recommendation": f.get("recommendation", ""),
            "Review Status": rv.get("status", "⏳ Pending"),
            "Reviewer Comment": rv.get("comment", ""),
            "Reviewed At": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

    export_df = pd.DataFrame(export_data)
    col_csv, col_json = st.columns(2)

    with col_csv:
        csv_bytes = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="⬇ CSV 다운로드",
            data=csv_bytes,
            file_name=f"audit_review_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_json:
        json_bytes = json.dumps({
            "audit_readiness_score": st.session_state.audit_result.get("audit_readiness_score"),
            "executive_summary": st.session_state.audit_result.get("executive_summary"),
            "findings_review": export_data,
            "exported_at": datetime.datetime.now().isoformat()
        }, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            label="⬇ JSON 다운로드",
            data=json_bytes,
            file_name=f"audit_review_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )

    # Cloud save
    if cloud.is_connected:
        if st.button("☁ Supabase에 리뷰 저장", use_container_width=True):
            user = st.session_state.user
            reviewer_email = user.get("email", "local") if isinstance(user, dict) else getattr(user, "email", "local")
            ok_save, msg_save = cloud.save_review(
                reviewer=reviewer_email,
                filename="uploaded_audit",
                findings=export_data,
                summary=st.session_state.audit_result.get("executive_summary", ""),
                score=st.session_state.audit_result.get("audit_readiness_score", 0)
            )
            if ok_save:
                st.success(msg_save)
            else:
                st.error(msg_save)
    else:
        st.caption("☁ Supabase 미연결 — CSV/JSON으로 로컬 저장하세요.")
