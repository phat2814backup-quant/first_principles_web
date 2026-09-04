# -*- coding: utf-8 -*-
"""
Elite Thinking Family — Streamlit Cloud ready
- Shared knowledge base (JSON)
- Per-user history & training progress
- Admin (Phat) can view all users
- Training tab: Grade 6 + Grade 9 lessons
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import streamlit as st
from dotenv import load_dotenv

from utils.auth import require_login, logout, current_user, is_admin
from utils.knowledge import (
    get_principles,
    get_domains,
    search_principles,
    append_analysis,
    save_training_answer,
    load_user_history,
    list_all_user_histories,
)
from utils.training import load_lessons, get_lessons_by_grade, get_lesson, save_lessons
from utils.ai_engine import analyze_problem, feedback_on_answer

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
CURRENT_DIR = Path(__file__).parent.resolve()
load_dotenv(CURRENT_DIR / ".env")

st.set_page_config(
    page_title="Elite Thinking Family",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_api_key() -> str:
    # Priority: Streamlit secrets → env → sidebar input (handled later)
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    for k in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEY_1"):
        v = os.getenv(k)
        if v and v.strip():
            return v.strip()
    return ""


# -----------------------------------------------------------------------------
# Auth gate
# -----------------------------------------------------------------------------
if not require_login():
    st.stop()

user = current_user()
username = user["username"]
display_name = user.get("display_name", username)
role = user.get("role", "user")

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 {display_name}")
    st.caption(f"Vai trò: **{'Quản trị' if role == 'admin' else 'Thành viên'}**")
    if st.button("Đăng xuất", use_container_width=True):
        logout()

    st.divider()
    st.markdown("#### 🔑 Gemini API Key")
    default_key = get_api_key()
    api_key = st.text_input(
        "API Key (để trống nếu đã cấu hình Secrets)",
        value=default_key if default_key else "",
        type="password",
        help="Trên Streamlit Cloud nên để trong Secrets: GOOGLE_API_KEY",
    )
    if not api_key:
        api_key = default_key

    model_choice = st.selectbox(
        "Model",
        ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"],
        index=0,
    )

    st.divider()
    st.caption("Knowledge dùng chung · Tiến độ học riêng")
    st.caption("Admin (Phat) xem được lịch sử mọi người")

# -----------------------------------------------------------------------------
# Main tabs
# -----------------------------------------------------------------------------
tab_labels = [
    "🚀 Phân rã vấn đề",
    "📚 Thư viện nguyên lý",
    "🎓 Đào tạo tư duy",
    "📝 Lịch sử của tôi",
]
if is_admin():
    tab_labels.append("👑 Admin")

tabs = st.tabs(tab_labels)

# ========== TAB 1: Phân rã ==========
with tabs[0]:
    st.title("🧠 Phân rã đa chế độ (Elite Lenses)")
    st.markdown("Nhập vấn đề / quyết định / tình huống cần làm rõ.")

    sample = st.selectbox(
        "Ví dụ nhanh",
        [
            "— Chọn ví dụ —",
            "Cuối tuần nên chơi game cả ngày hay dành 2 giờ ôn bài?",
            "Bạn rủ mình học theo method TikTok để điểm tăng nhanh, có nên không?",
            "Muốn tham gia nhiều CLB nhưng sợ điểm giảm, phải làm sao?",
        ],
    )
    initial = "" if sample.startswith("—") else sample

    problem = st.text_area("Nội dung cần phân rã", value=initial, height=120)

    if st.button("🚀 Phân rã ngay", type="primary", use_container_width=True):
        if not api_key:
            st.warning("Cần Gemini API Key (sidebar hoặc Streamlit Secrets).")
        elif not problem.strip():
            st.warning("Hãy nhập nội dung.")
        else:
            with st.spinner("Đang chạy 9 lenses..."):
                result = analyze_problem(api_key, model_choice, problem.strip())

            if not result:
                st.error("Không có kết quả.")
            elif result.get("error"):
                st.error(result["error"])
                if result.get("raw"):
                    st.code(result["raw"])
            else:
                # Save personal history
                summary = result.get("first_principles_breakdown", "")[:300]
                append_analysis(username, problem.strip(), summary, result)

                st.success("Đã phân rã xong · Đã lưu vào lịch sử của bạn")

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### First Principles")
                    st.write(result.get("first_principles_breakdown", "—"))
                    st.markdown("#### Nguyên lý liên quan")
                    for p in result.get("core_principles_found", [])[:5]:
                        st.markdown(f"- **{p.get('name')}** ({p.get('domain')}): {p.get('description', '')[:120]}")

                with c2:
                    st.markdown("#### Elite Lenses")
                    lenses = result.get("elite_lenses", {})
                    for k, v in lenses.items():
                        st.markdown(f"**{k}**: {v}")

                st.markdown("#### Hành động gợi ý")
                for a in result.get("actionable_insights", []):
                    st.markdown(f"- {a}")

                st.markdown("#### Cần bạn quyết định")
                for h in result.get("human_decision_needed", []):
                    st.markdown(f"- {h}")

# ========== TAB 2: Thư viện ==========
with tabs[1]:
    st.title("📚 Thư viện nguyên lý cốt lõi (dùng chung)")
    domains = get_domains()
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        domain = st.selectbox("Lọc trụ cột", domains)
    with col_f2:
        q = st.text_input("Tìm kiếm", placeholder="Bayes, đòn bẩy, bảo toàn...")

    if q.strip():
        principles = search_principles(q)
    else:
        principles = get_principles(domain if domain != "Tất cả" else None)

    st.caption(f"Hiển thị {len(principles)} nguyên lý")

    for p in principles[:40]:
        with st.expander(f"{p.get('principle_name', '?')} · {p.get('domain', '')}"):
            st.markdown(f"**Mô tả:** {p.get('description', '')}")
            if p.get("formal_definition"):
                st.info(p["formal_definition"])
            if p.get("intuitive_summary"):
                st.write(f"💡 {p['intuitive_summary']}")
            c1, c2 = st.columns(2)
            with c1:
                if p.get("boundary_conditions"):
                    st.caption(f"Điều kiện biên: {p['boundary_conditions']}")
            with c2:
                if p.get("falsification_test"):
                    st.caption(f"Falsify: {p['falsification_test']}")

# ========== TAB 3: Đào tạo tư duy ==========
with tabs[2]:
    st.title("🎓 Đào tạo tư duy theo lộ trình")
    st.markdown("Bài học từ dễ → khó · Lớp 6 trước, lớp 9 sau · Tiến độ lưu riêng cho từng người")

    grade = st.radio("Chọn cấp", ["Lớp 6", "Lớp 9"], horizontal=True)
    grade_key = "6" if grade == "Lớp 6" else "9"
    lessons = get_lessons_by_grade(grade_key)

    if not lessons:
        st.warning("Chưa có bài học.")
    else:
        lesson_titles = [f"{l['id']} — {l['title']} ({l.get('level', '')})" for l in lessons]
        choice = st.selectbox("Chọn bài", lesson_titles)
        idx = lesson_titles.index(choice)
        lesson = lessons[idx]

        st.subheader(lesson["title"])
        st.caption(f"Chế độ: **{lesson.get('mode')}** · Mức: {lesson.get('level')}")

        st.markdown(f"**Mục tiêu:** {lesson.get('objective')}")
        st.markdown("#### Tình huống")
        st.info(lesson.get("situation", ""))

        st.markdown("#### Các bước hướng dẫn")
        for i, step in enumerate(lesson.get("guide_steps", []), 1):
            st.markdown(f"{i}. {step}")

        with st.expander("💡 Gợi ý (mở khi cần)"):
            st.write(lesson.get("hint", ""))

        st.markdown("#### Bài tập của bạn")
        st.write(lesson.get("exercise_prompt", ""))

        # Load previous answer if any
        hist = load_user_history(username)
        prev = hist.get("training", {}).get(lesson["id"], {})
        prev_answer = prev.get("answer", "")
        prev_feedback = prev.get("feedback", "")

        answer = st.text_area("Câu trả lời", value=prev_answer, height=150, key=f"ans_{lesson['id']}")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Lưu câu trả lời", use_container_width=True):
                save_training_answer(username, lesson["id"], answer.strip())
                st.success("Đã lưu vào tiến độ của bạn.")
                st.rerun()
        with col_b:
            if st.button("🤖 Xin feedback AI", type="primary", use_container_width=True):
                if not answer.strip():
                    st.warning("Hãy viết câu trả lời trước.")
                elif not api_key:
                    st.warning("Cần API Key để nhận feedback.")
                else:
                    with st.spinner("Đang nhận xét..."):
                        fb = feedback_on_answer(api_key, model_choice, lesson, answer.strip())
                    save_training_answer(username, lesson["id"], answer.strip(), fb)
                    st.rerun()

        if prev_feedback:
            st.markdown("#### Feedback gần nhất")
            st.success(prev_feedback)

        # Progress overview
        st.divider()
        st.markdown("#### Tiến độ của bạn ở cấp này")
        done = 0
        for l in lessons:
            done_flag = l["id"] in hist.get("training", {})
            icon = "✅" if done_flag else "⬜"
            st.markdown(f"{icon} {l['title']}")
            if done_flag:
                done += 1
        st.progress(done / max(len(lessons), 1))
        st.caption(f"Hoàn thành {done}/{len(lessons)} bài")

# ========== TAB 4: Lịch sử cá nhân ==========
with tabs[3]:
    st.title("📝 Lịch sử của tôi")
    hist = load_user_history(username)

    st.markdown("#### Phân rã đã làm")
    analyses = hist.get("analyses", [])
    if not analyses:
        st.info("Chưa có phân rã nào.")
    else:
        for a in analyses[:30]:
            with st.expander(f"{a.get('time', '')} — {a.get('problem', '')[:80]}"):
                st.write(a.get("summary", ""))

    st.markdown("#### Bài đào tạo đã làm")
    training = hist.get("training", {})
    if not training:
        st.info("Chưa hoàn thành bài nào.")
    else:
        for lid, info in training.items():
            lesson = get_lesson(lid)
            title = lesson["title"] if lesson else lid
            with st.expander(f"{title} · {info.get('time', '')}"):
                st.markdown("**Câu trả lời:**")
                st.write(info.get("answer", ""))
                if info.get("feedback"):
                    st.markdown("**Feedback:**")
                    st.write(info["feedback"])

# ========== TAB 5: Admin (Phat) ==========
if is_admin():
    with tabs[4]:
        st.title("👑 Khu vực quản trị (Phat)")
        st.markdown("Xem tiến độ mọi thành viên · Cập nhật bài học")

        admin_tabs = st.tabs(["Tiến độ mọi người", "Cập nhật bài học", "Thông tin hệ thống"])

        with admin_tabs[0]:
            all_h = list_all_user_histories()
            if not all_h:
                st.info("Chưa có dữ liệu lịch sử nào được ghi.")
            else:
                for h in all_h:
                    uname = h.get("username", "?")
                    n_ana = len(h.get("analyses", []))
                    n_train = len(h.get("training", {}))
                    with st.expander(f"**{uname}** · {n_ana} phân rã · {n_train} bài học · cập nhật {h.get('updated_at', '—')}"):
                        st.markdown("##### Phân rã gần đây")
                        for a in h.get("analyses", [])[:10]:
                            st.markdown(f"- `{a.get('time')}` {a.get('problem', '')[:100]}")
                        st.markdown("##### Bài đào tạo")
                        for lid, info in h.get("training", {}).items():
                            lesson = get_lesson(lid)
                            title = lesson["title"] if lesson else lid
                            st.markdown(f"- **{title}** ({info.get('time')})")
                            st.caption(info.get("answer", "")[:200])

        with admin_tabs[1]:
            st.markdown("Chỉnh sửa nội dung bài học (lưu vào `data/lessons.json`).")
            data = load_lessons()
            st.caption(f"Version {data.get('version')} · Cập nhật lần cuối: {data.get('updated_at')} bởi {data.get('updated_by')}")

            g_edit = st.radio("Cấp cần sửa", ["grade_6", "grade_9"], horizontal=True)
            lessons_edit = data.get(g_edit, [])
            if lessons_edit:
                ids = [l["id"] for l in lessons_edit]
                sel_id = st.selectbox("Chọn bài", ids)
                lesson_e = next(l for l in lessons_edit if l["id"] == sel_id)

                new_title = st.text_input("Tiêu đề", value=lesson_e.get("title", ""))
                new_obj = st.text_area("Mục tiêu", value=lesson_e.get("objective", ""))
                new_sit = st.text_area("Tình huống", value=lesson_e.get("situation", ""))
                new_ex = st.text_area("Bài tập", value=lesson_e.get("exercise_prompt", ""))
                new_hint = st.text_area("Gợi ý", value=lesson_e.get("hint", ""))

                if st.button("💾 Lưu thay đổi bài học", type="primary"):
                    for i, l in enumerate(data[g_edit]):
                        if l["id"] == sel_id:
                            data[g_edit][i].update({
                                "title": new_title,
                                "objective": new_obj,
                                "situation": new_sit,
                                "exercise_prompt": new_ex,
                                "hint": new_hint,
                            })
                            break
                    save_lessons(data, updated_by=username)
                    st.success("Đã cập nhật bài học.")
                    st.rerun()

            st.divider()
            st.markdown("#### Thêm bài mới (cơ bản)")
            with st.form("add_lesson"):
                add_grade = st.selectbox("Thêm vào", ["grade_6", "grade_9"])
                add_id = st.text_input("ID (vd: g6_07)")
                add_title = st.text_input("Tiêu đề")
                add_level = st.selectbox("Mức", ["Dễ", "Trung bình", "Khó hơn"])
                add_mode = st.text_input("Chế độ tư duy", value="First Principles")
                add_obj = st.text_area("Mục tiêu")
                add_sit = st.text_area("Tình huống")
                add_ex = st.text_area("Bài tập")
                add_hint = st.text_area("Gợi ý")
                if st.form_submit_button("Thêm bài"):
                    if add_id and add_title:
                        data.setdefault(add_grade, []).append({
                            "id": add_id,
                            "title": add_title,
                            "level": add_level,
                            "mode": add_mode,
                            "objective": add_obj,
                            "situation": add_sit,
                            "guide_steps": ["Đọc tình huống", "Trả lời bài tập", "Đối chiếu gợi ý"],
                            "exercise_prompt": add_ex,
                            "hint": add_hint,
                            "related_principle": "",
                        })
                        save_lessons(data, updated_by=username)
                        st.success(f"Đã thêm {add_id}")
                        st.rerun()
                    else:
                        st.warning("Cần ID và tiêu đề.")

        with admin_tabs[2]:
            st.markdown("""
            **Kiến trúc hiện tại (Streamlit Cloud ready)**
            - Knowledge base: `data/knowledge_base.json` (dùng chung)
            - Bài học: `data/lessons.json` (admin cập nhật được)
            - Lịch sử / tiến độ: `data/histories/<user>.json` (riêng từng người)
            - Đăng nhập: `data/users.json`
            - API Key: Streamlit Secrets hoặc nhập sidebar

            **Lưu ý Cloud:**  
            File ghi trên Streamlit Community Cloud có thể bị reset khi reboot app.  
            Với gia đình 6 người vẫn dùng được; nếu cần bền vững hơn hãy chuyển histories sang Google Sheet / Supabase sau.
            """)
            st.code("Users: Phat (admin), Ha, xuka, bong, A1, A2\nPassword pattern: <Tên>@12345", language="text")

# Footer
st.divider()
st.caption(f"Elite Thinking Family · Đăng nhập: {display_name} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
