import streamlit as st
from cloud_utils import CloudManager


class AuthManager:
    def __init__(self):
        self.cloud = CloudManager()

    def register_user(self, email: str, password: str, name: str) -> tuple[bool, str]:
        """Registers a user using Supabase Auth."""
        if not self.cloud.supabase:
            return False, "Supabase credentials missing. Check your .env file."

        try:
            response = self.cloud.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {"full_name": name}
                }
            })

            if response.user:
                if response.user.identities and len(response.user.identities) == 0:
                    return False, "User already exists."
                return True, "Registration successful! Please check your email if confirmation is required."
            else:
                return False, "Registration failed (no user returned)."

        except Exception as e:
            return False, f"Registration Error: {str(e)}"

    def login_user(self, email: str, password: str) -> tuple[bool, object]:
        """Logs in using Supabase Auth. Falls back to local admin for testing."""
        if not self.cloud.supabase:
            # Local fallback for development / no-Supabase environment
            if email == "admin" and password == "admin":
                return True, {"email": "admin", "user_metadata": {"full_name": "Local Admin"}}
            return False, "Supabase credentials missing. Use admin/admin for local test."

        try:
            response = self.cloud.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user:
                return True, response.user
            else:
                return False, "Login failed."

        except Exception as e:
            return False, f"Login Error: {str(e)}"
