# -*- coding: utf-8 -*-
"""Simple family authentication for Streamlit Cloud."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Any

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"


def load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {"users": {}}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    data = load_users()
    user = data.get("users", {}).get(username)
    if user and user.get("password") == password:
        return {
            "username": username,
            "role": user.get("role", "user"),
            "display_name": user.get("display_name", username),
        }
    return None


def init_auth_state() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None


def require_login() -> bool:
    """Show login form if not authenticated. Return True if logged in."""
    init_auth_state()

    if st.session_state.authenticated and st.session_state.user:
        return True

    st.title("🧠 Elite Thinking Family")
    st.markdown("Đăng nhập để sử dụng hệ thống tư duy & đào tạo.")

    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập", placeholder="Phat / Ha / xuka / bong / A1 / A2")
        password = st.text_input("Mật khẩu", type="password", placeholder="Tên@12345")
        submitted = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)

        if submitted:
            user = authenticate(username.strip(), password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.session_state.history = []  # personal analysis history this session
                st.session_state.training_progress = {}  # lesson_id -> answers
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu.")

    st.caption("Tài khoản gia đình · Dữ liệu kiến thức dùng chung · Tiến độ học tập riêng")
    return False


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def current_user() -> Optional[Dict[str, Any]]:
    return st.session_state.get("user")


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.get("role") == "admin")
