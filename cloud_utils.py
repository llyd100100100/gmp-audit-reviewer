import os
import datetime
import json
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class CloudManager:
    def __init__(self):
        self.supabase: "Client | None" = None
        self.is_connected = False

        # Try streamlit secrets first (deployment), fallback to .env (local)
        try:
            import streamlit as st
            sb_url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
            sb_key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
        except Exception:
            sb_url = os.getenv("SUPABASE_URL")
            sb_key = os.getenv("SUPABASE_KEY")

        if SUPABASE_AVAILABLE and sb_url and sb_key:
            try:
                self.supabase = create_client(sb_url, sb_key)
                self.is_connected = True
            except Exception as e:
                print(f"Supabase Init Error: {e}")

    # ─────────────────── Storage ───────────────────

    def upload_file(self, file_content: bytes, filename: str) -> tuple[bool, str]:
        """Uploads an audit trail file to Supabase Storage bucket 'audit-vault'."""
        if not self.is_connected:
            return False, "Supabase not connected. File not uploaded."

        try:
            bucket_name = "audit-vault"
            self.supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=file_content,
                file_options={"content-type": "application/octet-stream", "upsert": "true"}
            )
            return True, f"Uploaded to {bucket_name}/{filename}"
        except Exception as e:
            return False, f"Storage Error: {str(e)}"

    # ─────────────────── Database ──────────────────

    def save_review(self, reviewer: str, filename: str, findings: list, summary: str, score: int) -> tuple[bool, str]:
        """Saves completed audit review results to Supabase 'audit_reviews' table."""
        if not self.is_connected:
            return False, "Supabase not connected. Review not saved to cloud."

        try:
            data = {
                "reviewer": reviewer,
                "filename": filename,
                "findings_json": json.dumps(findings, ensure_ascii=False),
                "executive_summary": summary,
                "audit_readiness_score": score,
                "reviewed_at": datetime.datetime.now().isoformat()
            }
            self.supabase.table("audit_reviews").insert(data).execute()
            return True, "Review saved to Supabase."
        except Exception as e:
            return False, f"DB Error: {str(e)}"

    def get_reviews(self, reviewer: str) -> list:
        """Fetches past reviews for the given reviewer email."""
        if not self.is_connected:
            return []
        try:
            res = (
                self.supabase.table("audit_reviews")
                .select("*")
                .eq("reviewer", reviewer)
                .order("reviewed_at", desc=True)
                .limit(20)
                .execute()
            )
            return res.data or []
        except Exception:
            return []
