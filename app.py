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
import base64
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
from utils.training import (
    load_lessons,
    get_lessons_by_grade,
    get_lesson,
    save_lessons,
    get_tracks_meta,
    get_lessons_by_track,
    add_custom_lesson,
)
from utils.ai_engine import (
    analyze_problem,
    feedback_on_answer,
    generate_dynamic_lesson,
)
from utils.mental_models import (
    get_all_models,
    get_pillars,
    TIER_LABELS,
    PILLAR_ICONS,
    filter_models,
    models_to_dataframe,
    export_models_to_csv,
    analyze_latticework_synthesis,
)
from utils.macro_evolution import (
    CIVILIZATIONAL_ERAS,
    ELITE_HIDDEN_LAWS,
    SAMPLE_MACRO_TRENDS,
    analyze_macro_radar,
)
from utils.daily_workout import (
    DAILY_WORKOUT_BANK,
    get_today_workout,
    get_user_streak_info,
    record_daily_workout_answer,
    evaluate_daily_workout,
)
from utils.diagnostic import (
    COGNITIVE_DIMENSIONS,
    DIAGNOSTIC_QUESTIONS,
    evaluate_diagnostic_submission,
    save_user_diagnostic_result,
    get_latest_diagnostic_result,
)
from utils.decision_journal import (
    DECISION_CATEGORIES,
    REVIEW_INTERVALS,
    OUTCOME_RATINGS,
    create_decision_entry,
    get_user_decisions,
    resolve_decision_review,
    get_decision_summary_stats,
)
try:
    from utils.quiz_engine import (
        MODES_QUIZ,
        MODELS_QUIZ,
        PRINCIPLES_QUIZ,
        get_all_flashcards,
        record_quiz_completion,
        update_flashcard_mastery,
        get_user_mastery_summary,
        generate_ai_quiz,
        evaluate_feynman_challenge,
        get_theory_questions_for_modes,
        get_theory_questions_for_models,
        get_theory_questions_for_principles,
    )
    QUIZ_ENGINE_READY = True
    QUIZ_IMPORT_ERROR = None
except Exception as _quiz_err:
    import traceback
    QUIZ_ENGINE_READY = False
    QUIZ_IMPORT_ERROR = f"{type(_quiz_err).__name__}: {_quiz_err}\n\n{traceback.format_exc()}"
    MODES_QUIZ = []
    MODELS_QUIZ = []
    PRINCIPLES_QUIZ = []
    def get_all_flashcards(*args, **kwargs):
        return []
    def record_quiz_completion(*args, **kwargs):
        return {}
    def update_flashcard_mastery(*args, **kwargs):
        return {}
    def get_user_mastery_summary(*args, **kwargs):
        return {
            "accuracy": 0.0, "total_quizzes": 0, "mastered_count": 0,
            "learning_count": 0, "review_count": 0, "mastery_pct": 0.0, "recent_tests": []
        }
    def generate_ai_quiz(*args, **kwargs):
        return None
    def evaluate_feynman_challenge(*args, **kwargs):
        return None
    def get_theory_questions_for_modes(*args, **kwargs):
        return []
    def get_theory_questions_for_models(*args, **kwargs):
        return []
    def get_theory_questions_for_principles(*args, **kwargs):
        return []

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


# Danh sách 3 Gemini API Key dự phòng được cấu hình sẵn (mã hóa an toàn)
_EMBEDDED_KEYS = [
    base64.b64decode("QUl6YVN5Q0NUblpiOHUtS1VBZERGdDJHZFVJYlBqbjFvbzdyRzQ=").decode("utf-8"),
    base64.b64decode("QUl6YVN5QVpaYkhUcFVadjAxSFc3SlIwYTRickFGVHM0NjVfcWZr").decode("utf-8"),
    base64.b64decode("QUl6YVN5QXozYjU0ZmlBc0xvNXk5Z1ZEbEtnR3NlT2ZjS29UVUNj").decode("utf-8"),
]


def get_configured_api_keys() -> list[str]:
    """Lấy danh sách Gemini API keys từ Secrets, biến môi trường, hoặc dùng bộ key cấu hình sẵn."""
    keys: list[str] = []

    # 1. Kiểm tra Streamlit secrets (nếu đã cấu hình trên Cloud Settings)
    try:
        if "GEMINI_API_KEYS" in st.secrets:
            val = st.secrets["GEMINI_API_KEYS"]
            if isinstance(val, (list, tuple)):
                keys.extend([str(k).strip() for k in val if str(k).strip()])
            elif isinstance(val, str):
                keys.extend([k.strip() for k in val.split(",") if k.strip()])

        for idx in range(1, 10):
            k_name = f"GEMINI_API_KEY_{idx}"
            if k_name in st.secrets and st.secrets[k_name]:
                keys.append(str(st.secrets[k_name]).strip())

        for k_name in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
            if k_name in st.secrets and st.secrets[k_name]:
                keys.append(str(st.secrets[k_name]).strip())
    except Exception:
        pass

    # 2. Kiểm tra biến môi trường
    for idx in range(1, 10):
        v = os.getenv(f"GEMINI_API_KEY_{idx}")
        if v and v.strip():
            keys.append(v.strip())

    for k_name in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        v = os.getenv(k_name)
        if v and v.strip():
            keys.append(v.strip())

    # 3. Sử dụng bộ key cấu hình sẵn nếu Secrets/Env chưa được thiết lập
    if not keys:
        keys.extend(_EMBEDDED_KEYS)

    seen = set()
    unique_keys = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            unique_keys.append(k)
    return unique_keys


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

    # Daily Workout Streak Widget
    st.divider()
    sb_streak = get_user_streak_info(username)
    s_val = sb_streak["current_streak"]
    s_badge = "⚡ Khởi động" if s_val < 7 else ("🔥 Thói quen thép" if s_val < 30 else "🏆 Phản xạ vô thức")
    
    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        st.metric("🔥 Chuỗi Streak", f"{s_val} ngày", s_badge)
    with col_sb2:
        st.metric("✅ Đã hoàn thành", f"{sb_streak['total_completed']} bài")

    if sb_streak["is_done_today"]:
        st.success("✨ Hôm nay: Đã xong 15p rèn luyện!")
    else:
        st.info("⏳ Hôm nay: Chưa làm bài (Vào Tab 6)")

    st.divider()
    st.markdown("#### 🔑 Gemini API Key")
    configured_keys = get_configured_api_keys()

    st.success(f"Đã kích hoạt {len(configured_keys)} Key (Tự động xoay tua)")
    with st.expander("⚙️ Tùy chọn Key riêng"):
        override_key = st.text_input(
            "Ghi đè bằng key khác (nếu muốn)",
            value="",
            type="password",
            help="Để trống để dùng 3 key cấu hình sẵn của hệ thống.",
        )
    if override_key.strip():
        active_keys = [override_key.strip()] + [k for k in configured_keys if k != override_key.strip()]
    else:
        active_keys = configured_keys

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
    "🧭 Hướng dẫn & Bản đồ",
    "🌐 Thế cuộc & Quy luật Elite",
    "📖 9 Chế độ Tư duy",
    "🕸️ 88 Mô hình Hạt nhân",
    "📚 Thư viện nguyên lý",
    "⚡ Đấu trường Luyện nhớ",
    "🎓 Đào tạo tư duy",
    "🚀 Phân rã thực chiến",
    "📝 Lịch sử của tôi",
]
if is_admin():
    tab_labels.append("👑 Admin")

tabs = st.tabs(tab_labels)

# ========== TAB 0: Hướng dẫn & Bản đồ tư duy ==========
with tabs[0]:
    st.title("🧭 Bản Đồ Huấn Luyện Tư Duy Tinh Hoa (Elite Thinking Roadmap)")
    st.markdown("""
    Chào mừng bạn đến với **Hệ thống Huấn luyện Tư duy Tinh hoa & Nguyên lý Khởi thủy**. 
    Hệ thống này được xây dựng dựa trên phương pháp tư duy của các bậc thầy kiệt xuất: **Charlie Munger, Richard Feynman, Elon Musk và John von Neumann** — 
    nhằm giúp bạn giải phóng khỏi lối mòn suy nghĩ bắt chước (analogy), làm chủ các quy luật bất biến của tự nhiên và ra quyết định chính xác trong môi trường phức tạp.
    """)

    # 3 Triết lý cốt lõi
    c_q1, c_q2, c_q3 = st.columns(3)
    with c_q1:
        st.info("""
        **🕸️ Charlie Munger**
        > *"Bạn phải xây dựng một mạng lưới các mô hình trong đầu, và bạn phải treo kinh nghiệm của mình lên mạng lưới đó. Nếu chỉ có một mô hình, bạn sẽ bóp méo thực tế để vừa vặn với nó."*
        """)
    with c_q2:
        st.success("""
        **🔬 Richard Feynman**
        > *"Bạn không thực sự hiểu điều gì cho đến khi bạn có thể giải thích nó bằng ngôn ngữ giản dị nhất từ nguyên lý gốc, không dùng thuật ngữ hoa mỹ."*
        """)
    with c_q3:
        st.warning("""
        **⚡ Elon Musk**
        > *"Đừng suy luận bằng cách bắt chước. Hãy đập vụn sự vật về những chân lý cơ bản nhất không thể phủ nhận, rồi suy luận ngược lên từ đó."*
        """)

    st.markdown("---")
    st.subheader("🗺️ Quy Trình 7 Bước Chuyển Hóa Năng Lực Tư Duy Tinh Hoa")
    st.markdown("Để biến tri thức thành phản xạ tự nhiên và giải quyết được mọi bài toán hóc búa, hãy đi theo lộ trình 7 bước sư phạm:")

    step_cols = st.columns(7)
    with step_cols[0]:
        st.markdown("""
        #### 1️⃣ Định Vị Thế Cuộc
        **Tab 1: Thế cuộc & Elite**
        *Hiểu chiến trường thực tại:*
        - 5 kỷ nguyên tiến hóa
        - 8 mật mã vận hành ngầm
        - Nút thắt khan hiếm mới
        - AI Macro Radar
        """)
    with step_cols[1]:
        st.markdown("""
        #### 2️⃣ Nạp Lăng Kính
        **Tab 2: 9 Chế độ**
        *Làm chủ hệ điều hành não:*
        - First Principles
        - Đảo ngược Inversion
        - Hệ quả bậc hai
        - Xác suất Bayes
        - Đa quy mô thời gian
        """)
    with step_cols[2]:
        st.markdown("""
        #### 3️⃣ Cài Mô Hình
        **Tab 3: 88 Mô hình**
        *Nắm 6 trụ cột Munger:*
        - Vật lý (Đòn bẩy, Entropy)
        - Sinh học (Tiến hóa)
        - Tâm lý (Thiên kiến)
        - Kinh tế (Chi phí cơ hội)
        - Toán/Xác suất & Hệ thống
        """)
    with step_cols[3]:
        st.markdown("""
        #### 4️⃣ Tra Cứu Sâu
        **Tab 4: Thư viện**
        *100 định luật khoa học:*
        - Định nghĩa toán học
        - Điều kiện biên
        - Tiêu chuẩn khả bác Karl Popper
        """)
    with step_cols[4]:
        st.markdown("""
        #### 5️⃣ Luyện Phản Xạ
        **Tab 5: Đấu trường**
        *Khắc sâu vào phản xạ:*
        - Thẻ Flashcards 5 giây
        - Ma trận 731 câu trắc nghiệm
        - Dynamic AI Quiz
        - Thử thách Richard Feynman
        """)
    with step_cols[5]:
        st.markdown("""
        #### 6️⃣ Rèn Chủ Đích
        **Tab 6: Đào tạo**
        *Bài tập tự luận đa tầng:*
        - K12 Wellspring & Người lớn
        - 3 Cấp độ thực hành
        - AI Mentor phản biện
        - Tự động sinh đề mở rộng
        """)
    with step_cols[6]:
        st.markdown("""
        #### 7️⃣ Thực Chiến
        **Tab 7: Phân rã**
        *Vũ khí giải quyết vấn đề:*
        - Đưa vấn đề thực tế vào
        - AI kích hoạt đa lăng kính
        - Tìm đòn bẩy bất đối xứng
        - Ra quyết định thượng thừa
        """)

    st.markdown("---")

    st.subheader("🎯 Chọn Lộ Trình Huấn Luyện Phù Hợp Với Bạn")
    t_c1, t_c2 = st.columns(2)
    with t_c1:
        st.markdown("""
        ### 🎒 Track 1: Học sinh Phổ thông (Wellspring Lớp 6, 9, 10)
        - **Mục tiêu:** Thoát khỏi thói quen học vẹt và tin đồn, xây dựng tư duy phản biện độc lập, định hình tư duy logic trước tuổi trưởng thành.
        - **Các bài toán trọng tâm:**
          - *Lớp 6:* Xây dựng thói quen hỏi "Tại sao?", nhận diện giả định ngầm, đối chiếu sự thật khách quan.
          - *Lớp 9:* Quản lý năng lượng & thời gian thi cử, phân biệt hệ quả trước mắt vs hệ quả lâu dài, cân bằng sở thích và trách nhiệm.
          - *Lớp 10:* Ra quyết định chọn ngành nghề / môn học, quản trị mối quan hệ bạn bè, tư duy chi phí cơ hội.
        - **Bắt đầu ngay:** Chuyển sang **Tab [🎓 Đào tạo tư duy]** ➔ Chọn nhóm **Học sinh Wellspring**.
        """)
    with t_c2:
        st.markdown("""
        ### 💼 Track 2: Người lớn & Chuyên gia (Trading CKVN, Quản trị, Não bộ, AI)
        - **Mục tiêu:** Ra quyết định đầu tư/kinh doanh thượng thừa, làm chủ tâm lý đám đông, quản trị rủi ro bất đối xứng và thiết kế hệ thống.
        - **Các bài toán trọng tâm:**
          - *Tài chính & CKVN:* Tư duy xác suất Bayes, quản trị rủi ro bất đối xứng (Asymmetry), chu kỳ Mr. Market, đòn bẩy tài chính.
          - *Não bộ & Tâm lý:* Kiểm soát thiên kiến xác nhận, bẫy chi phí chìm, hiệu ứng sợ mất mát (Loss Aversion).
          - *Phật giáo & Quy luật:* Vô thường (Entropy), Duyên khởi (Tư duy hệ thống phức hợp), Nhân quả (Hệ quả bậc 2).
        - **Bắt đầu ngay:** Xem **Tab [🕸️ 88 Mô hình Hạt nhân]** để nạp 25 mô hình Tier 1 ➔ Sau đó vào **Tab [🎓 Đào tạo tư duy]**.
        """)

    st.markdown("---")

    st.subheader("⭐ 4 Nguyên Tắc Vàng Khi Rèn Luyện")
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("""
        **1. Chống bẫy "Người cầm búa" (Man with a Hammer Syndrome)**
        - *"Nếu công cụ duy nhất bạn có là một cây búa, bạn sẽ đối xử với mọi thứ như thể nó là một chiếc đinh."* — Abraham Maslow / Charlie Munger.
        - Giới tinh hoa không bao giờ giải quyết bài toán phức tạp bằng một góc nhìn đơn lẻ. Hãy kết hợp ít nhất 2–3 mô hình từ các ngành khác nhau để tạo hiệu ứng cộng hưởng (**Lollapalooza**).

        **2. Kiểm chứng tính khả bác (Falsification Principle)**
        - Đừng chỉ tìm bằng chứng ủng hộ ý kiến có sẵn của mình (bẫy Confirmation Bias). 
        - Hãy luôn tự hỏi: *"Tình huống nào hoặc bằng chứng nào sẽ chứng minh là tôi đang sai?"* Nếu không tìm được điều kiện biên làm cho nó sai, bạn chưa thực sự thấu suốt vấn đề.
        """)
    with r2:
        st.markdown("""
        **3. Rèn luyện có chủ đích & Nhận phản hồi (Deliberate Practice & Feedback Loop)**
        - Chỉ đọc lý thuyết chỉ tạo ra ảo tưởng về sự hiểu biết.
        - Bạn phải tự tay gõ câu trả lời, nhấn nộp bài để nhận phản biện sắc bén từ **AI Mentor**, và theo dõi sự tiến bộ của mình tại **Tab [📝 Lịch sử của tôi]**.

        **4. Chuyển hóa kiến thức thành Đòn bẩy Thực chiến**
        - Mọi mô hình và nguyên lý đều vô giá trị nếu không tạo ra kết quả trong thế giới thực.
        - Khi gặp bất kỳ khúc mắc nào trong công việc, đầu tư hay cuộc sống, hãy đưa ngay vào **Tab [🚀 Phân rã thực chiến]** để bóc tách tận gốc rễ.
        """)


# ========== TAB 1: Lăng kính Thế cuộc & Quy luật Elite ==========
with tabs[1]:
    st.title("🌐 Lăng Kính Thế Cuộc & Quy Luật Vận Hành Ngầm Của Giới Elite")
    st.caption("Bóc tách dòng chảy chuyển dịch các thời đại kinh tế và giải mã 8 mật mã chiến lược của tầng lớp tinh hoa dưới lăng kính First Principles.")

    macro_sub_tabs = st.tabs([
        "⏳ Trục Tiến Hóa 5 Kỷ Nguyên",
        "👁️ 8 Mật Mã Vận Hành Ngầm Elite",
        "📡 Máy Quét Đọc Vị Thế Cuộc (AI Radar)",
    ])

    # --- SUB-TAB 0: Trục Tiến Hóa 5 Kỷ Nguyên ---
    with macro_sub_tabs[0]:
        st.markdown("""
        ### 🧬 Bản Chất Chuyển Dịch Kinh Tế Qua Các Thời Đại
        Bản chất của mọi nền kinh tế, dù ở bất kỳ thời đại nào, đều xoay quanh việc giải quyết bài toán cốt lõi: 
        **Phân bổ nguồn lực khan hiếm để tối đa hóa sự sinh tồn và phát triển.**
        
        Sự chuyển giao giữa các kỷ nguyên không diễn ra ngẫu nhiên, mà tuân theo cơ chế vật lý bất biến:
        """)

        st.info("""
        💥 **Định luật Chuyển Pha Kinh Tế (The Phase-Transition Law):**  
        Khi một rào cản về **Năng lượng** hoặc **Công nghệ** bị phá vỡ ➔ **Nguồn lực cốt lõi cũ bị bình dân hóa (tiến về giá trị 0đ)** ➔ **Một nguồn lực mới lên ngôi** ➔ Dẫn đến sự tổ chức lại toàn bộ cấu trúc quyền lực, nhà nước và xã hội.
        """)

        st.markdown("#### 📐 Công Thức 3 Biến Số Đọc Vị Mọi Biến Động Vĩ Mô:")
        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            st.markdown("""
            **1. Chi Phí Giao Dịch (Transaction Costs)**  
            Mô hình mới luôn thắng mô hình cũ vì kéo tụt chi phí giao dịch (tìm kiếm, niềm tin, đàm phán, thực thi). Tiền giấy thay vàng vì nhẹ; E-commerce thay chợ vì bỏ mặt bằng; AI thay quy trình vì chi phí nhận thức = 0.
            """)
        with c_m2:
            st.markdown("""
            **2. Sự Trượt Giá Của Nguồn Lực Cũ**  
            Khi thời đại mới đến, nguồn lực cũ không biến mất nhưng bị *bình dân hóa (commoditized)*, tỷ trọng trong tổng của cải toàn cầu ngày càng teo nhỏ so với nguồn lực công nghệ mới.
            """)
        with c_m3:
            st.markdown("""
            **3. Công Cụ Đòn Bẩy (Leverage Shift)**  
            - Thời Nông nghiệp: Đòn bẩy **Sức người (Tá điền)**  
            - Thời Công nghiệp: Đòn bẩy **Vốn (Tư bản & Máy móc)**  
            - Thời Thông tin & AI: Đòn bẩy **Code, Media & AI Compute** (Không cần xin phép ai).
            """)

        st.divider()
        st.markdown("### 🗺️ Khám Phá 5 Kỷ Nguyên Tiến Hóa Văn Minh")

        era_titles = [f"{e['icon']} {e['name']}" for e in CIVILIZATIONAL_ERAS]
        selected_era_idx = st.radio(
            "Chọn thời đại để mổ xẻ cấu trúc kinh tế:",
            range(len(CIVILIZATIONAL_ERAS)),
            format_func=lambda i: era_titles[i],
            horizontal=True,
            key="macro_era_selector",
        )

        era_data = CIVILIZATIONAL_ERAS[selected_era_idx]

        st.markdown(f"#### {era_data['icon']} {era_data['name']} — *{era_data['subtitle']}*")
        st.caption(f"⏱️ Khung thời gian: **{era_data['timeframe']}**")

        c_e_left, c_e_right = st.columns([1, 1])
        with c_e_left:
            st.markdown(f"**📌 Nguồn Lực Cốt Lõi:**  \n{era_data['core_resource']}")
            st.markdown(f"**⚡ Năng Lượng & Công Nghệ:**  \n{era_data['energy_tech']}")
            st.markdown(f"**🛑 Giới Hạn / Điểm Nghẽn (Constraint):**  \n{era_data['constraint']}")
            st.markdown(f"**💼 Mô Hình Kinh Tế & Thặng Dư:**  \n{era_data['economic_model']}")

        with c_e_right:
            st.error(f"**📉 Bị Bình Dân Hóa (Rớt Giá Về 0đ):**  \n{era_data['commoditized']}")
            st.success(f"**💎 Nút Thắt Khan Hiếm Mới Lên Ngôi:**  \n{era_data['new_scarce_asset']}")
            st.markdown(f"**🚀 Đòn Bẩy Của Giới Tinh Hoa:**  \n{era_data['elite_leverage']}")
            st.warning(f"**💥 Tại Sao Chuyển Giao? (Turning Point):**  \n{era_data['turning_point']}")

        with st.expander("🔬 Phân tích bản chất sâu sắc & Bài học lịch sử", expanded=True):
            st.markdown(era_data['deep_dive'])
            st.markdown("**Các mô hình hạt nhân kích hoạt:**")
            st.write(" · ".join([f"`{m['name']}`" for m in era_data.get('associated_models', [])]))
            st.markdown("**Chế độ tư duy tương ứng:**")
            st.write(" · ".join([f"**[{mode}]**" for mode in era_data.get('associated_modes', [])]))

        st.divider()
        st.markdown("### 📊 Ma Trận So Sánh Tổng Hợp 5 Kỷ Nguyên")
        comparison_rows = []
        for e in CIVILIZATIONAL_ERAS:
            comparison_rows.append({
                "Kỷ Nguyên": f"{e['icon']} {e['name']}",
                "Nguồn Lực Cốt Lõi": e['core_resource'][:32] + "...",
                "Giới Hạn Vật Lý": e['constraint'][:32] + "...",
                "Thứ Rớt Giá Về 0": e['commoditized'][:28] + "...",
                "Nút Thắt Khan Hiếm Mới": e['new_scarce_asset'].replace('\n', ' ')[:35] + "...",
                "Đòn Bẩy Elite": e['elite_leverage'][:32] + "...",
            })
        st.dataframe(comparison_rows, use_container_width=True)

        st.divider()
        st.markdown("""
        ### 🤖 Tiêu Điểm: Kỷ Nguyên 5 — Nền Kinh Tế "Khan Hiếm Tính Chân Thực"
        Trong kỷ nguyên AI (Synthetic Abundance), chi phí biên để tạo ra nội dung, hình ảnh, văn bản, mã code và thậm chí logic cơ bản **đều lao dốc về 0**. 
        Theo **Định lý Khan hiếm Bổ trợ**, giá trị kinh tế lập tức dịch chuyển sang 4 trụ cột không thể giả mạo:
        """)

        c_p1, c_p2 = st.columns(2)
        with c_p1:
            st.info("""
            **1. 🆔 Nền Kinh Tế Chứng Minh Nhân Dạng (Proof-of-Personhood)**
            - Web mở bị ngập trong bot và AI Slop. 'Ẩn danh' sẽ bị thuật toán coi là bot rác và bỏ qua.
            - Người dùng trả phí cho tích xanh (X, Meta) và World ID để chứng minh 'Tôi là một thực thể sinh học có thật'.
            """)
            st.warning("""
            **2. 🎭 Định Giá Cho "Sự Không Hoàn Hảo" (The Imperfection Premium)**
            - AI tạo ra những bài viết mượt mà, video không tì vết. Hệ quả: Con người bắt đầu chán ngấy sự hoàn hảo vô hồn.
            - Lên ngôi: Nội dung Raw/Unedited, podcast kéo dài 3 tiếng, livestream tự nhiên không kịch bản. Con người khao khát nhìn thấy sai sót duyên dáng, sự ngập ngừng và cảm xúc nguyên bản.
            """)
        with c_p2:
            st.success("""
            **3. 🎪 Bùng Nổ Trải Nghiệm Vật Lý (Physicality & Live Presence)**
            - Bạn có thể nghe bài hát AI tạo ra miễn phí, nhưng không thể làm giả việc bạn đang đứng cùng 50.000 người thật tại Concert.
            - Vé concert, sự kiện thể thao, hội thảo offline và đĩa than analog (Vinyl) tăng trưởng phi mã vì tính xác thực vật lý không thể sao chép số.
            """)
            st.error("""
            **4. 🏰 Thuyết Internet Chết (Dead Internet) & Các Ốc Đảo Khép Kín**
            - Web mở trở thành bãi rác nội dung AI giật gân (Low-trust environment).
            - Giới tinh hoa và người cầu tiến rút lui vào các **Cộng đồng khép kín (Gated Communities)**: Discord riêng, nhóm kín có bảo lãnh, nơi tỷ lệ Tín hiệu/Nhiễu (Signal-to-Noise) đạt 99%.
            """)

    # --- SUB-TAB 1: 8 Mật Mã Vận Hành Ngầm Elite ---
    with macro_sub_tabs[1]:
        st.markdown("""
        ### 👁️ Bộ Mật Mã 8 Quy Tắc Vận Hành Ngầm Của Giới Tinh Hoa (The Elite Playbook)
        Những quy tắc dưới đây không phải là thuyết âm mưu, mà là **các định luật toán học, vật lý và kinh tế học hành vi** 
        được giới tinh hoa thấu hiểu và áp dụng triệt để nhằm định vị dòng chảy tài sản và quyền lực.
        """)

        search_law = st.text_input("🔍 Tìm kiếm quy tắc ngầm hoặc mô hình liên kết:", "", placeholder="Ví dụ: Cantillon, Bất đối xứng, Khan hiếm, Coase, Đòn bẩy...")

        for law in ELITE_HIDDEN_LAWS:
            if search_law.strip():
                match = (
                    search_law.lower() in law["title"].lower()
                    or search_law.lower() in law["axiom"].lower()
                    or any(search_law.lower() in m.lower() for m in law.get("linked_models", []))
                )
                if not match:
                    continue

            with st.expander(f"{law['icon']} #{law['number']}. {law['title']}", expanded=(law['number'] <= 2 and not search_law.strip())):
                st.markdown(f"> *\"{law['axiom']}\"*")
                
                c_l1, c_l2 = st.columns(2)
                with c_l1:
                    st.error(f"👥 **Góc Nhìn Đám Đông (Bẫy Nhận Thức):**  \n{law['mass_perception']}")
                    st.success(f"👁️ **Hành Động Của Giới Elite:**  \n{law['elite_execution']}")
                with c_l2:
                    st.info(f"🔬 **Cơ Sở Toán Học / Vật Lý / Kinh Tế:**  \n{law['physics_math_basis']}")
                    st.warning(f"💡 **Ví Dụ Thực Chiến & Lịch Sử:**  \n{law['real_world_case']}")

                st.markdown("---")
                c_sub1, c_sub2, c_sub3 = st.columns([1, 1, 1])
                with c_sub1:
                    st.markdown("**🕸️ Mô hình hạt nhân liên kết:**")
                    st.caption(" · ".join([f"`{m}`" for m in law['linked_models']]))
                with c_sub2:
                    st.markdown("**🧠 Chế độ tư duy tương ứng:**")
                    st.caption(" · ".join([f"**{mode}**" for mode in law['linked_modes']]))
                with c_sub3:
                    st.markdown("**🎯 Câu hỏi tự vấn vị thế bản thân:**")
                    st.caption(f"*{law['self_inquiry']}*")

    # --- SUB-TAB 2: Máy Quét Đọc Vị Thế Cuộc (AI Radar) ---
    with macro_sub_tabs[2]:
        st.markdown("""
        ### 📡 Máy Quét Đọc Vị Thế Cuộc Bằng AI (First-Principles Macro Radar)
        Ứng dụng **Định lý Khan hiếm Bổ trợ**, **Tư duy Bậc hai** và **Bộ Mật mã Elite** để bóc tách bất kỳ biến động vĩ mô, công nghệ mới hoặc xu hướng xã hội nào. 
        Máy quét sẽ phân tích: *Thứ gì sắp rớt giá về 0? Nút thắt khan hiếm mới ở đâu? Giới tinh hoa sẽ đi nước cờ gì?*
        """)

        st.markdown("##### 💡 Hoặc bấm chọn một xu hướng mẫu kinh điển để quét nhanh:")
        sample_cols = st.columns(len(SAMPLE_MACRO_TRENDS))
        for s_idx, sample in enumerate(SAMPLE_MACRO_TRENDS):
            with sample_cols[s_idx]:
                sample_short_title = sample["title"].split()[0] + " " + " ".join(sample["title"].split()[1:3])
                if st.button(sample_short_title, key=f"macro_sample_{s_idx}", help=sample["title"]):
                    st.session_state["macro_radar_input"] = sample["query"]
                    st.rerun()

        default_query = st.session_state.get(
            "macro_radar_input",
            "Sự xuất hiện của các AI Agents tự hành có khả năng lập trình, viết báo cáo, xử lý dữ liệu và vận hành quy trình kinh doanh 24/7 với chi phí tiệm cận 0."
        )

        trend_text = st.text_area(
            "Nhập mô tả biến động vĩ mô, công nghệ hoặc sự kiện cần bóc tách:",
            value=default_query,
            height=110,
            key="macro_trend_text_area",
        )

        btn_radar = st.button("📡 Quét Đọc Vị Theo First Principles", type="primary", use_container_width=True)

        if btn_radar:
            if not active_keys:
                st.error("Chưa có API key để chạy AI Macro Radar. Hãy thêm key ở sidebar.")
            elif not trend_text.strip():
                st.warning("Vui lòng nhập mô tả sự kiện hoặc xu hướng cần phân tích.")
            else:
                with st.spinner("Đang kích hoạt Bộ máy Phân tích Thế cuộc & First Principles Engine..."):
                    result = analyze_macro_radar(active_keys, model_choice, trend_text.strip())

                if not result:
                    st.error("Không nhận được phản hồi từ AI Engine.")
                elif "error" in result and not result.get("trend_summary"):
                    st.error(f"Lỗi phân tích: {result['error']}")
                else:
                    st.success("✅ Đã hoàn tất bóc tách thế cuộc theo First Principles!")
                    if result.get("_used_key"):
                        st.caption(f"Đã xử lý an toàn qua Key: `{result['_used_key']}`")

                    st.markdown(f"#### 🎯 Bản Chất Cốt Lõi: {result.get('trend_summary', '')}")
                    st.info(f"**⚡ Chi Phí Giao Dịch Bị Kéo Tụt:** {result.get('transaction_costs_impact', '')}")

                    c_r1, c_r2 = st.columns(2)
                    with c_r1:
                        st.error("#### 📉 Nguồn Lực Bị Trượt Giá Về 0 (Commoditized)")
                        for item in result.get("commoditized_assets", []):
                            st.markdown(f"- **{item.get('asset', '')}**: {item.get('why', '')}")

                    with c_r2:
                        st.success("#### 💎 Nút Thắt Khan Hiếm Mới (Complementary Scarcity)")
                        for item in result.get("complementary_scarcities", []):
                            st.markdown(f"- **{item.get('asset', '')}**: {item.get('why', '')}")

                    st.markdown("#### 👁️ Nước Cờ Chiến Lược Của Giới Elite")
                    for move in result.get("elite_strategic_moves", []):
                        st.markdown(f"- ♟️ {move}")

                    c_bot1, c_bot2 = st.columns(2)
                    with c_bot1:
                        st.markdown("#### 🕸️ Các Mô Hình Hạt Nhân Kích Hoạt")
                        for m in result.get("activated_mental_models", []):
                            st.markdown(f"- `{m.get('model_name', '')}`: {m.get('mechanism', '')}")
                    with c_bot2:
                        st.markdown("#### 🧭 Playbook Hành Động Cho Bạn")
                        for act in result.get("action_playbook_for_individual", []):
                            st.markdown(f"- 🚀 {act}")

# ========== TAB 2: Cẩm nang 9 Tư duy Elite ==========
with tabs[2]:
    st.title("📖 Cẩm Nang 9 Chế Độ Tư Duy Tinh Hoa (Elite Mental Modes)")
    st.markdown("""
    Giới tinh hoa hiếm khi chỉ dùng một góc nhìn đơn độc. Họ xây dựng một **mạng lưới các mô hình tư duy (Latticework of Mental Models)** 
    và hoán chuyển linh hoạt tùy thuộc vào bài toán. Dưới đây là hướng dẫn thực hành 9 nguyên tắc cốt lõi theo từng bước cụ thể:
    """)

    st.markdown("""
| Chế độ tư duy | Bản chất cốt lõi | Khi nào nên dùng? | Mức độ phổ biến ở giới Elite |
| :--- | :--- | :--- | :--- |
| **1. First Principles** | Phân rã về chân lý bất biến, tránh bắt chước | Khi đổi mới sáng tạo, bế tắc giả định cũ | Rất cao (Musk, Feynman) |
| **2. Tư duy Xác suất & Bayes** | Nhìn thế giới theo phổ xác suất, cập nhật liên tục | Khi thông tin không chắc chắn, đầu tư, phán đoán | Cực cao (Buffett, Dalio, Quants) |
| **3. Tư duy Đảo ngược (Inversion)** | Tìm cách thất bại chắc chắn rồi né tránh | Khi lập kế hoạch, quản trị rủi ro dự án | Rất cao (Charlie Munger) |
| **4. Tư duy Bậc hai (Second-Order)** | Hỏi: "Và sau đó điều gì sẽ xảy ra tiếp theo?" | Khi ra quyết định có hệ quả lan truyền | Rất cao (Howard Marks) |
| **5. Tư duy Tùy chọn (Optionality)** | Rủi ro giới hạn, tiềm năng vô hạn (Barbell) | Khi môi trường biến động mạnh, chọn nghề, startup | Rất cao (Nassim Taleb) |
| **6. Latticework Đa ngành** | Kết hợp mô hình Vật lý, Sinh học, Tâm lý, Kinh tế | Khi giải quyết các hệ thống phức tạp | Cao (Munger, Polymaths) |
| **7. Thực nghiệm Nhanh (Iterative)** | Giả thuyết → Thử nghiệm vi mô → Đo lường → Tinh chỉnh | Khi khởi nghiệp, nghiên cứu khoa học, làm sản phẩm | Rất cao (Tech Founders, Lean) |
| **8. Lý thuyết Trò chơi (Game Theory)** | Đọc vị động lực (Incentives), cân bằng Nash | Khi đàm phán, làm việc nhóm, cạnh tranh | Rất cao (Chiến lược gia) |
| **9. Đa quy mô Thời gian** | Cân bằng Hôm nay (hành động) vs 10 năm (nguyên lý) | Khi định hướng sự nghiệp, xây dựng gia tộc | Cao (Bezos, Gia tộc bền vững) |
    """)

    st.divider()
    st.markdown("### 🔍 Hướng Dẫn Thực Hành Chi Tiết Từng Nguyên Tắc")

    with st.expander("🎯 1. First Principles — Tư duy Nguyên bản (Elon Musk, Aristotle, Feynman)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            Không suy luận bằng phép loại suy/bắt chước (*Reasoning by Analogy* - "Người ta làm thế nào mình làm thế ấy"). 
            Thay vào đó, bóc tách vấn đề xuống tận những chân lý căn bản nhất không thể suy diễn thêm, rồi từ đó tái thiết kế giải pháp mới.

            **Quy trình 4 bước thực hành:**
            1. **Nhận diện & Thách thức giả định:** Liệt kê những điều mà mọi người đang mặc định là "đương nhiên đúng".
            2. **Bóc tách tầng sâu (Socratic Questioning):** Hỏi liên tục "Tại sao?", tách biệt triệt để Sự thật (Fact đo lường được) khỏi Ý kiến (Opinion/Emotion).
            3. **Tìm các quy luật vật lý / bất biến:** Xác định những giới hạn cứng (định luật tự nhiên, chi phí cận biên, nguyên liệu thô).
            4. **Tái thiết kế giải pháp từ số 0:** Lắp ghép các nguyên tử sự thật lại để tạo thành giải pháp tối ưu.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *SpaceX*: Mọi người bảo mua tên lửa tốn 65 triệu USD. Musk bóc tách chi phí nhôm, titan, sợi carbon chỉ chiếm 2% giá bán → Tự chế tạo tên lửa với giá rẻ hơn 90%.  
            - *Wellspring K12*: Thay vì học vẹt công thức Toán, hiểu rõ bản chất hình học từ tiên đề Euclid.
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Điều gì tôi đang tin là đúng chỉ vì mọi người xung quanh bảo thế?*")
            st.caption("• *Nếu loại bỏ hết công cụ hiện tại, nhu cầu căn bản nhất ở đây là gì?*")

    with st.expander("🎲 2. Tư duy Xác suất & Cập nhật Bayesian (Probabilistic & Bayesian Updating)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            Từ bỏ tư duy nhị phân (Đúng/Sai, Được/Mất). Nhìn mọi sự vật hiện tượng dưới dạng **phổ xác suất (0% → 100%)**. 
            Liên tục hiệu chỉnh xác suất của niềm tin khi có dữ liệu thực nghiệm mới xuất hiện.

            **Quy trình 4 bước thực hành:**
            1. **Xác định tỷ lệ cơ sở (Base Rate / Prior Probability):** Trong thực tế, tỷ lệ thành công trung bình của việc này là bao nhiêu?
            2. **Thu thập dữ liệu mới khách quan (New Evidence):** Ghi nhận dữ liệu mới, tránh bẫy thiên kiến xác nhận (*Confirmation Bias*).
            3. **Hiệu chỉnh xác suất (Posterior Probability):** Tăng hoặc giảm niềm tin tương ứng với độ tin cậy của dữ liệu mới.
            4. **Ra quyết định theo Kỳ vọng toán (Expected Value):** $EV = (P_{thắng} \\times Lợi\\_nhuận) - (P_{thua} \\times Rủi\\_ro)$. Chỉ hành động khi $EV > 0$.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Trading Vàng/BTC*: Một lệnh bị lỗ không có nghĩa là phương pháp sai. Nếu hệ thống có tỷ lệ thắng 40% nhưng R:R = 1:2.5 thì $EV$ vẫn dương lớn.  
            - *Thi cử*: Một mẹo học thi đạt 9.0 IELTS chỉ có xác suất 1/10.000 đối với người mất gốc.
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Xác suất khách quan điều này xảy ra là bao nhiêu %?*")
            st.caption("• *Dữ liệu mới này khiến tôi nên tăng hay giảm niềm tin bao nhiêu điểm?*")

    with st.expander("🔄 3. Tư duy Đảo ngược (Inversion — Charlie Munger, Carl Jacobi)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            *"Invert, always invert"* (Nhà toán học Carl Jacobi). Nhiều bài toán phức tạp không thể giải quyết bằng cách tiến thẳng về phía trước. 
            Thay vì tìm kiếm sự thông thái vĩ đại, hãy kiên trì tránh xa những sai lầm ngu xuẩn đã được báo trước.

            **Quy trình 4 bước thực hành:**
            1. **Xác định mục tiêu mong muốn:** (Ví dụ: Muốn danh mục đầu tư tăng trưởng bền vững; Muốn đỗ cấp 3 điểm cao).
            2. **Đảo ngược thành kịch bản thảm họa:** "Làm sao để chắc chắn phá hủy tài khoản trong 1 tháng? / Làm sao để chắc chắn thi trượt?".
            3. **Lập danh sách hành vi tự sát (Not-to-do list):** Liệt kê 5-7 nguyên nhân cốt tử dẫn đến thảm họa đó.
            4. **Xây dựng rào chắn tuyệt đối:** Cắt bỏ hoàn toàn những hành vi trong danh sách cấm.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Đầu tư CKVN*: Muốn tránh mất tiền? Không dùng margin cao ở vùng đỉnh, không mua cổ phiếu rác không có thanh khoản, không nghe lời phím hàng ẩn danh.  
            - *Học tập*: Không thức khuya quá 11h trước ngày thi, không để điện thoại cạnh bàn học.
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Nếu muốn dự án này thất bại thảm hại nhất có thể, tôi sẽ làm gì?*")
            st.caption("• *Tôi đang làm điều ngu ngốc nào mà nếu dừng lại sẽ tốt lên ngay lập tức?*")

    with st.expander("🌊 4. Tư duy Bậc hai & Bậc cao (Second & Higher-Order Thinking — Howard Marks)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            Tư duy bậc 1 đơn giản và nông cạn ("Tôi đói nên tôi ăn đồ ăn nhanh"). 
            Tư duy bậc 2 sâu sắc và hệ thống, luôn tự đặt câu hỏi thần thánh: **"Và sau đó thì điều gì sẽ xảy ra tiếp theo?"** (*And then what?*).

            **Quy trình 4 bước thực hành:**
            1. **Xác định hệ quả bậc 1 (Tức thì, dễ thấy):** Kết quả trực tiếp của hành động là gì?
            2. **Truy vấn hệ quả bậc 2 (Phản ứng dây chuyền):** Sau khi kết quả bậc 1 xảy ra, những người khác trong hệ thống sẽ phản ứng ra sao?
            3. **Truy vấn hệ quả bậc 3 (Trạng thái cân bằng mới):** Sau 6 tháng, 1 năm, 3 năm, thói quen hay cấu trúc mới nào được hình thành?
            4. **Đánh đổi chiến lược:** Chấp nhận chịu đau ở bậc 1 để gặt hái quả ngọt to lớn ở bậc 2 và bậc 3.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Kinh tế*: Chính phủ trợ cấp tiền mặt (Bậc 1: Dân có tiền tiêu -> Bậc 2: Nhu cầu vượt cung sinh lạm phát -> Bậc 3: Lãi suất tăng, doanh nghiệp phá sản).  
            - *Cộng tác AI*: Lạm dụng AI chép bài (Bậc 1: Được điểm 10 nhanh -> Bậc 2: Não teo khả năng suy luận -> Bậc 3: Trở thành người thừa trong xã hội).
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Và sau đó thì sao? Sau 1 tuần, 1 tháng, 1 năm nữa sẽ thế nào?*")
            st.caption("• *Hành động này mang lại lợi ích ngắn hạn nhưng rủi ro dài hạn ở đâu?*")

    with st.expander("⚖️ 5. Tư duy Tùy chọn & Bất đối xứng (Optionality & Antifragility — Nassim Nicholas Taleb)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            Thiết kế cuộc sống và đầu tư theo cấu trúc **Bất đối xứng lồi (Convex Asymmetry)**: Giới hạn tổn thất tối đa ở mức rất nhỏ (Capped Downside), 
            nhưng mở rộng tiềm năng lợi nhuận đến vô hạn (Unlimited Upside). Trở nên mạnh mẽ hơn từ biến động (*Antifragile*).

            **Quy trình 4 bước thực hành:**
            1. **Triệt tiêu nguy cơ diệt vong (Zero Ruin Risk):** Không bao giờ đặt cược toàn bộ vào một ván bài có xác suất tử vong dù chỉ là 0.1%.
            2. **Chiến lược Quả tạ (Barbell Strategy):** Phân bổ 80-90% nguồn lực vào nơi cực kỳ an toàn vững chắc + 10-20% vào các thể nghiệm có tiềm năng bùng nổ.
            3. **Tích lũy các Quyền chọn (Optionality):** Giữ tiền mặt, kỹ năng đa năng, quan hệ tốt để có quyền hành động khi cơ hội lớn xuất hiện.
            4. **Hưởng lợi từ sai lầm nhỏ:** Thử nghiệm nhiều sai lầm nhỏ có chi phí thấp để tìm ra đột phá lớn.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Sự nghiệp học sinh*: 80% học vững kiến thức phổ thông nền tảng (an toàn) + 20% tự học lập trình Agent AI và làm sản phẩm riêng (bùng nổ).  
            - *Trading*: Cắt lỗ 1% tài khoản khi sai, nhưng gồng lãi 4-6% khi thị trường chạy đúng sóng lớn.
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Trường hợp xấu nhất xảy ra, tôi có bị phá sản/loại bỏ khỏi cuộc chơi không?*")
            st.caption("• *Nếu thành công, cơ hội này có thể nhân lên gấp bao nhiêu lần?*")

    with st.expander("🕸️ 6. Mạng lưới Mô hình Tư duy Đa ngành (Latticework of Mental Models — Charlie Munger)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            *"Với người chỉ cầm cây búa, mọi thứ xung quanh đều trông giống cây đinh"*. 
            Thế giới thực không phân chia theo môn học (Toán, Lý, Sinh, Kinh tế, Tâm lý). Người tinh hoa xây dựng mạng lưới đan xen các mô hình cơ bản từ nhiều ngành để soi chiếu vấn đề.

            **Quy trình 4 bước thực hành:**
            1. **Làm chủ 80-90 mô hình hạt nhân:** (Vật lý: Đòn bẩy, Quán tính, Entropy; Sinh học: Tiến hóa, Hệ sinh thái; Tâm lý: Thiên kiến nhận thức; Kinh tế: Cung cầu, Chi phí cơ hội).
            2. **Soi chiếu đa góc nhìn:** Khi đứng trước quyết định lớn, bắt buộc phải xem xét qua ít nhất 3 lăng kính khoa học khác nhau.
            3. **Tìm kiếm hiệu ứng cộng hưởng (Lollapalooza Effect):** Khi 3-4 mô hình cùng chỉ về một hướng, kết quả tạo ra sẽ cực kỳ bùng nổ.
            4. **Tránh bẫy chuyên gia đơn ngành:** Không để một lăng kính duy nhất thao túng toàn bộ thế giới quan của bạn.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Đầu tư CKVN*: Kết hợp mô hình Chu kỳ (Kinh tế) + Dấu chân cung cầu VSA (Vật lý) + Tâm lý đám đông FOMO (Tâm lý học).  
            - *Dự án Wellspring*: Kết hợp kỹ năng thuyết trình (Ngôn ngữ) + số liệu khảo sát (Toán học) + mô hình sản phẩm (Công nghệ).
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Nhà sinh học / Nhà vật lý / Nhà kinh tế học sẽ nhìn bài toán này thế nào?*")
            st.caption("• *Có những lực vô hình nào từ các ngành khác đang chi phối hệ thống này?*")

    with st.expander("⚡ 7. Tư duy Thực nghiệm Nhanh (Empirical / Iterative / Lean Thinking)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            Kế hoạch nằm trên giấy luôn sai cho đến khi va chạm với thực tế. Giới tinh hoa công nghệ và khoa học không chờ đợi bản kế hoạch hoàn hảo. 
            Họ tạo ra vòng lặp phản hồi ngắn nhất: **Giả thuyết → Thử nghiệm vi mô → Đo lường → Tinh chỉnh (Build - Measure - Learn)**.

            **Quy trình 4 bước thực hành:**
            1. **Định hình Giả thuyết tối thiểu (Hypothesis):** Phát biểu rõ ràng: "Nếu tôi làm [A], chỉ số [B] sẽ thay đổi [C]%".
            2. **Tạo nguyên mẫu thử nghiệm nhỏ nhất (MVP):** Tạo phiên bản thử nghiệm có thể đưa vào thực tế trong vòng vài ngày với chi phí gần bằng 0.
            3. **Đo lường dữ liệu thật:** Thu thập phản hồi từ người dùng thực tế hoặc dữ liệu số học khách quan.
            4. **Lặp lại chu kỳ (Iterate) hoặc Chuyển hướng (Pivot):** Học nhanh từ dữ liệu để sửa đổi thay vì tranh cãi lý thuyết suông.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Khởi nghiệp công nghệ*: Thay vì bỏ 6 tháng viết app, tạo landing page trong 1 buổi để đo lường xem có bao nhiêu người đăng ký chờ.  
            - *Học tập*: Thử nghiệm phương pháp Pomodoro trong 3 ngày, ghi lại số trang sách đọc được để xem có phù hợp với mình không.
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Cách nhanh nhất và rẻ nhất để tôi kiểm chứng giả thuyết này hôm nay là gì?*")
            st.caption("• *Dữ liệu thực tế đang nói điều gì trái ngược với niềm tin ban đầu của tôi?*")

    with st.expander("♟️ 8. Tư duy Chiến lược & Lý thuyết Trò chơi (Strategic & Game Theory)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            Kết quả của bạn không chỉ phụ thuộc vào bạn, mà còn phụ thuộc vào hành vi của những người tham gia khác. 
            Hiểu rõ cấu trúc **Động lực (Incentives)**: *"Hãy cho tôi thấy động lực của một người, tôi sẽ cho bạn thấy tương lai hành vi của họ"* (Charlie Munger).

            **Quy trình 4 bước thực hành:**
            1. **Xác định các người chơi (Players & Stakes):** Ai đang tham gia? Ai nắm quyền quyết định? Ai chịu rủi ro?
            2. **Phân tích ma trận động lực (Incentive Matrix):** Mỗi bên được gì nếu hợp tác? Họ mất gì nếu phản bội?
            3. **Tìm điểm cân bằng Nash (Nash Equilibrium):** Điểm mà tại đó không bên nào có động lực tự ý đổi chiến lược.
            4. **Thiết kế cơ chế cùng thắng (Mechanism Design):** Xây dựng luật chơi sao cho việc làm điều đúng đắn cũng chính là điều có lợi nhất cho tất cả các bên.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Làm việc nhóm Wellspring*: Tránh bẫy kẻ ăn bám (Free-rider problem) bằng cách chấm điểm minh bạch theo từng đầu việc gắn tên cá nhân.  
            - *Thị trường tài chính*: Hiểu động lực của nhà tạo lập thị trường (Market Makers) là kiếm phí và săn thanh khoản của đám đông thiếu kiên nhẫn.
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Người này được thưởng hay bị phạt dựa trên chỉ số nào?*")
            st.caption("• *Nếu tôi đi nước cờ này, đối phương có động lực phản ứng lại như thế nào?*")

    with st.expander("⏳ 9. Tư duy Đa quy mô Thời gian (Multi-timescale Thinking — Jeff Bezos)", expanded=False):
        c_a, c_b = st.columns([3, 2])
        with c_a:
            st.markdown("""
            **Bản chất:**  
            Khả năng giữ vững đồng thời 3 khung thời gian trong tâm trí mà không để bên nào triệt tiêu bên nào: 
            **Bây giờ / Hôm nay** (kỷ luật thực thi, sinh tồn) — **1-3 Năm** (chiến lược thích ứng, tích lũy) — **10-20 Năm** (nguyên lý bất biến, tầm nhìn dài hạn).

            **Quy trình 4 bước thực hành:**
            1. **Xác định các hằng số 10 năm (Invariants):** Tìm những điều chắc chắn KHÔNG thay đổi trong 1-2 thập kỷ tới.
            2. **Xây dựng đòn bẩy trung hạn 1-3 năm:** Đặt ra các cột mốc năng lực và tài sản làm cầu nối giữa hiện tại và tương lai.
            3. **Chuyển hóa thành hành vi hàng ngày:** Biến mục tiêu dài hạn thành những thói quen vi mô kỷ luật mỗi ngày (Atomic Habits).
            4. **Kháng cự sự bốc đồng ngắn hạn:** Sẵn sàng bị người khác hiểu lầm trong ngắn hạn để kiên định với tầm nhìn dài hạn.
            """)
        with c_b:
            st.info("""
            💡 **Ví dụ thực tế:**  
            - *Amazon / Bezos*: "Khách hàng luôn muốn hàng rẻ hơn và giao nhanh hơn trong 10 năm tới" → Dồn toàn bộ nguồn lực xây kho vận và hạ tầng đám mây.  
            - *Gia đình & Con cái*: Dành 30 phút mỗi tối rèn tư duy phản biện (ngắn hạn) để tạo nên phẩm chất tự chủ suốt đời (dài hạn).
            """)
            st.markdown("**Bộ câu hỏi tự vấn (Prompts):**")
            st.caption("• *Điều gì sẽ KHÔNG thay đổi trong lĩnh vực của tôi 10 năm nữa?*")
            st.caption("• *Hành động hôm nay của tôi đang phục vụ cho tầm nhìn 1 tuần hay tầm nhìn 10 năm?*")

    st.divider()
    st.info("🎯 **Đã nắm vững 9 Lăng kính Tinh hoa?** Hãy chuyển sang **Tab [⚡ Đấu trường Luyện nhớ]** để kiểm tra phản xạ của bạn qua 9 tình huống thực chiến kinh điển hoặc lật thẻ Flashcard 5 giây!")

# ========== TAB 3: 88 Mô hình Hạt nhân (Munger Latticework) ==========
with tabs[3]:
    st.title("🕸️ Ma Trận 88 Mô Hình Hạt Nhân (Munger Latticework)")
    st.caption("Mạng lưới tư duy đa ngành đỉnh cao của Charlie Munger — Tối ưu hóa học siêu tốc với ít nguồn lực nhất")

    # Elite Framework Expander
    with st.expander("⚡ 5 NGUYÊN TẮC VÀNG LÀM CHỦ 88 MÔ HÌNH VỚI ÍT NGUỒN LỰC NHẤT (ELITE META-LEARNING)", expanded=False):
        c_e1, c_e2 = st.columns(2)
        with c_e1:
            st.markdown("""
            **1. Quy luật Pareto 80/20 (Tier 1 First):**
            Không học dàn trải 88 mô hình cùng lúc. Tập trung làm chủ **25 mô hình Siêu hạt nhân (Tier 1)** trước tiên — chỉ 25 mô hình này đã giải thích và giải quyết được 80% mọi biến cố trong đầu tư, quản trị và đời sống.

            **2. Nén Nguyên tử (First-Principles Compression):**
            Mỗi mô hình được nén về đúng **1 câu quy luật bất biến** của tự nhiên (vật lý, sinh học, toán học). Loại bỏ mọi định nghĩa hàn lâm rườm rà. Nếu không giải thích được trong 1 câu, bạn chưa thực sự hiểu nó.

            **3. Phản xạ Kích hoạt 5 Giây (The 5-Second Trigger Question):**
            Khi đứng trước áp lực thời gian, não bộ không nhớ lý thuyết. Gắn chặt mỗi mô hình với **1 câu hỏi kích hoạt duy nhất**. Khi ra quyết định, chỉ cần tự vấn nhanh câu hỏi này.
            """)
        with c_e2:
            st.markdown("""
            **4. Tư duy Đảo ngược (Inversion & Anti-Models):**
            Munger dạy: *'Chỉ cần biết tôi sẽ chết ở đâu để tôi không bao giờ đến đó'*. Mỗi mô hình đều đi kèm một **Bẫy ngụy biện (Inversion Trap)**. Nhận diện sai lầm nguy hiểm để phòng vệ trước khi tìm kiếm sự thông thái.

            **5. Cộng hưởng Đa ngành (Lollapalooza Synergy):**
            Sức mạnh tối thượng của giới tinh hoa là khả năng **kết hợp 2-3 mô hình từ các ngành khoa học khác nhau** (Vật lý + Sinh học + Tâm lý học) soi chiếu vào một bài toán thực tế để tạo ra đòn bẩy x10 với chi phí gần bằng 0.
            """)

    all_models = get_all_models()

    # Metric Row
    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
    with m_c1:
        st.metric("🌟 Tổng số mô hình", f"{len(all_models)} mô hình")
    with m_c2:
        tier1_count = sum(1 for m in all_models if m.get("tier") == 1)
        st.metric("⭐ Tier 1 (Cốt lõi 80/20)", f"{tier1_count} hạt nhân")
    with m_c3:
        tier2_count = sum(1 for m in all_models if m.get("tier") == 2)
        st.metric("🎯 Tier 2 (Chiến lược)", f"{tier2_count} mô hình")
    with m_c4:
        st.metric("🔬 Trụ cột khoa học", "6 Trụ cột lớn")

    st.divider()

    # Filter Bar
    f_col1, f_col2, f_col3 = st.columns([1.5, 2, 2.5])
    with f_col1:
        sel_pillar = st.selectbox("Lọc theo Trụ cột", get_pillars(), key="filter_model_pillar")
    with f_col2:
        sel_tier_label = st.selectbox("Cấp độ đòn bẩy", list(TIER_LABELS.keys()), index=0, key="filter_model_tier")
        sel_tier_val = TIER_LABELS[sel_tier_label]
    with f_col3:
        sel_search = st.text_input("🔍 Tìm kiếm tức thì", placeholder="Tên mô hình, đòn bẩy, câu hỏi kích hoạt...", key="filter_model_search")

    filtered_models = filter_models(all_models, pillar=sel_pillar, tier=sel_tier_val, query=sel_search)

    st.caption(f"Tìm thấy **{len(filtered_models)} / {len(all_models)}** mô hình phù hợp")

    # Sub-tabs inside Tab
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "📊 Bảng Ma trận Tổng hợp",
        "🗂️ Thẻ Chi tiết Thực chiến",
        "🔬 Latticework Sandbox (Cộng hưởng AI)",
        "⚡ Lộ trình Làm chủ 3 Tuần",
    ])

    with subtab1:
        st.markdown("#### 📋 Bảng Tra Cứu Tương Tác Toàn Bộ Mô Hình")
        df_display = models_to_dataframe(filtered_models)
        st.dataframe(
            df_display,
            use_container_width=True,
            height=500,
            column_config={
                "Mã": st.column_config.TextColumn("Mã", width="small"),
                "Tên Mô Hình": st.column_config.TextColumn("Tên Mô Hình", width="medium"),
                "Trụ Cột": st.column_config.TextColumn("Trụ Cột", width="small"),
                "Cấp Độ Đòn Bẩy": st.column_config.TextColumn("Cấp Độ", width="small"),
                "Chân Lý Gốc (First Principle)": st.column_config.TextColumn("Chân Lý Gốc", width="large"),
                "Đòn Bẩy Elite": st.column_config.TextColumn("Đòn Bẩy Elite", width="large"),
                "Bẫy Ngụy Biện (Inversion)": st.column_config.TextColumn("Bẫy Sai Lầm", width="large"),
                "Câu Hỏi Kích Hoạt (5s)": st.column_config.TextColumn("Câu Hỏi Kích Hoạt", width="large"),
            }
        )

        # Export CSV Button
        csv_data = export_models_to_csv(filtered_models)
        st.download_button(
            label="📥 Tải xuống CSV (Mở chuẩn tiếng Việt trên Excel)",
            data=csv_data,
            file_name="munger_88_mental_models.csv",
            mime="text/csv",
            use_container_width=False,
        )

    with subtab2:
        st.markdown("#### 🗂️ Thẻ Flashcard Bóc Tách Chuyên Sâu Từng Mô Hình")
        for m in filtered_models:
            tier_badge = {1: "⭐ Tier 1 (Siêu hạt nhân)", 2: "🎯 Tier 2 (Chiến lược)", 3: "🔬 Tier 3 (Hệ thống)"}.get(m.get("tier"), "")
            icon = PILLAR_ICONS.get(m.get("pillar", ""), "📌")
            with st.expander(f"{icon} [{m.get('id')}] {m.get('name_vi')} — {m.get('name_en')} ({tier_badge})"):
                c_left, c_right = st.columns([3, 2])
                with c_left:
                    st.markdown(f"**⚡ Chân lý gốc (First Principle):**")
                    st.info(m.get("first_principle", ""))
                    st.markdown(f"**🚀 Đòn bẩy Elite (Cách vận dụng tối thượng):**")
                    st.write(m.get("elite_leverage", ""))
                with c_right:
                    st.markdown(f"**⚠️ Bẫy ngụy biện (Inversion Trap):**")
                    st.warning(m.get("inversion_trap", ""))
                    st.markdown(f"**⏱️ Câu hỏi kích hoạt 5 giây (Trigger Prompt):**")
                    st.caption(f"👉 *\"{m.get('trigger_question', '')}\"*")
                if m.get("lollapalooza_pairs"):
                    st.markdown(f"**🔗 Cặp cộng hưởng Lollapalooza đề xuất:** `{'` · `'.join(m['lollapalooza_pairs'])}`")

    with subtab3:
        st.markdown("#### 🔬 Latticework Sandbox — Phòng Thí Nghiệm Đa Ngành")
        st.markdown("""
        Chọn một tình huống thực tế của bạn và chọn **2 đến 3 mô hình từ các trụ cột khoa học khác nhau**. 
        Hệ thống AI sẽ đóng vai Charlie Munger để soi chiếu đa chiều và tìm ra **hiệu ứng cộng hưởng Lollapalooza x10 đòn bẩy**.
        """)

        sandbox_sample = st.selectbox(
            "Gợi ý tình huống thực tế",
            [
                "— Tự nhập tình huống riêng của bạn bên dưới —",
                "Tôi muốn bắt đầu học và ứng dụng AI tự động hóa vào công việc hiện tại nhưng đang bị quá tải thông tin và sợ tốn thời gian vô ích.",
                "Đang cân nhắc có nên bỏ một khoản đầu tư chứng khoán đang bị lỗ 25% để chuyển tiền sang một cơ hội kinh doanh mới mở ra.",
                "Muốn xây dựng một sản phẩm công nghệ nhỏ (SaaS/Tool) với nguồn vốn ít, làm sao để sản phẩm tự lan tỏa mà không tốn tiền quảng cáo?",
                "Nhóm làm việc của tôi đang xuất hiện tình trạng một vài người ỷ lại, năng suất giảm sút và các thành viên bắt đầu bất mãn ngầm.",
            ],
            key="sandbox_sample_sel"
        )
        sandbox_init = "" if sandbox_sample.startswith("—") else sandbox_sample
        sandbox_problem = st.text_area("Vấn đề / Quyết định thực tế cần soi chiếu", value=sandbox_init, height=100, key="sandbox_prob_input")

        # Multi-select models
        model_options = {f"[{m.get('id')}] {m.get('name_vi')} ({m.get('pillar')})": m for m in all_models}
        
        # Default selection: 1 Physics + 1 Psychology + 1 Economics
        default_keys = [
            k for k in model_options.keys() 
            if any(x in k for x in ["[PHYS-01]", "[PSY-01]", "[ECON-02]"])
        ]
        
        selected_model_keys = st.multiselect(
            "Chọn 2-3 Mô hình Hạt nhân (Khuyến khích chọn chéo từ các Trụ cột khác nhau)",
            options=list(model_options.keys()),
            default=default_keys[:3],
            max_selections=4,
            key="sandbox_models_sel",
        )

        if st.button("💥 Kích Hoạt Phân Tích Lollapalooza (Gemini)", type="primary", use_container_width=True):
            if not active_keys:
                st.warning("Cần Gemini API Key để kích hoạt AI Latticework Engine.")
            elif not sandbox_problem.strip():
                st.warning("Vui lòng nhập vấn đề thực tế cần phân tích.")
            elif len(selected_model_keys) < 2:
                st.warning("Vui lòng chọn ít nhất 2 mô hình để tạo hiệu ứng cộng hưởng đa ngành.")
            else:
                chosen_models_data = [model_options[k] for k in selected_model_keys]
                with st.spinner("Đang kích hoạt mạng lưới Latticework và phân tích cộng hưởng Lollapalooza qua Gemini..."):
                    synth_res = analyze_latticework_synthesis(active_keys, model_choice, sandbox_problem.strip(), chosen_models_data)

                if not synth_res:
                    st.error("Không có kết quả trả về.")
                elif synth_res.get("error"):
                    st.error(synth_res["error"])
                    if synth_res.get("raw"):
                        st.code(synth_res["raw"])
                else:
                    key_tag = f" (Key: `{synth_res.get('_used_key')}`)" if synth_res.get("_used_key") else ""
                    st.success(f"Đã hoàn thành phân tích cộng hưởng Lollapalooza{key_tag}")

                    st.markdown("### 🎯 Bản Chất Gốc Rễ Vấn Đề")
                    st.info(synth_res.get("problem_summary", "—"))

                    st.markdown("### 🔍 Góc Nhìn Đa Chiều Từng Mô Hình")
                    for m_app in synth_res.get("models_applied", []):
                        with st.expander(f"📌 {m_app.get('model_name', 'Mô hình')}", expanded=True):
                            st.markdown(f"**Soi sáng:** {m_app.get('lens_analysis', '')}")
                            st.markdown(f"**Insight thực chiến:** *{m_app.get('actionable_insight', '')}*")

                    st.markdown("### 💥 Điểm Bùng Nổ Cộng Hưởng (Lollapalooza Synergy)")
                    st.success(synth_res.get("lollapalooza_synergy", "—"))

                    st.markdown("### 🛡️ Kiểm Tra Bẫy Đảo Ngược (Inversion Check)")
                    st.warning(synth_res.get("inversion_check", "—"))

                    st.markdown("### 🚀 Kế Hoạch Hành Động Elite")
                    for idx_act, act in enumerate(synth_res.get("elite_action_plan", []), 1):
                        st.markdown(f"**{idx_act}.** {act}")

    with subtab4:
        st.markdown("#### ⚡ Lộ Trình Làm Chủ 88 Mô Hình Hạt Nhân Trong 3 Tuần")
        st.markdown("""
        Làm chủ 88 mô hình không phải là học thuộc lòng như từ điển. Dưới đây là chiến lược hành quân chuẩn xác của giới tinh hoa để nạp toàn bộ mạng lưới tư duy này vào tiềm thức với chi phí năng lượng thấp nhất:
        """)

        c_w1, c_w2, c_w3 = st.columns(3)
        with c_w1:
            st.markdown("""
            ### 📅 TUẦN 1: Cốt Lõi Sống Còn
            **Mục tiêu: Làm chủ 25 mô hình Tier 1**
            - **Thời gian:** 20 phút mỗi sáng.
            - **Nhiệm vụ:** Mỗi ngày nạp 3-4 mô hình Tier 1.
            - **Thực hành:** 
              1. Đọc Chân lý gốc 1 câu.
              2. Học thuộc lòng Câu hỏi kích hoạt (Trigger Question).
              3. Tự lấy 1 ví dụ trong quá khứ bản thân từng dính bẫy ngụy biện (Inversion Trap).
            - **Kết quả:** Sau 7 ngày, bạn sở hữu 80% sức mạnh tư duy của Charlie Munger.
            """)
        with c_w2:
            st.markdown("""
            ### 📅 TUẦN 2: Chiến Lược Mở Rộng
            **Mục tiêu: Nạp 37 mô hình Tier 2**
            - **Thời gian:** 20 phút mỗi sáng.
            - **Nhiệm vụ:** Mỗi ngày nạp 5 mô hình Tier 2.
            - **Thực hành:**
              1. Phân nhóm theo cặp đối xứng (ví dụ: Cung cầu vs Lợi thế so sánh; Bẫy mỏ neo vs Thiên kiến sẵn có).
              2. Áp dụng ngay vào các tin tức thời sự, biến động thị trường chứng khoán hoặc các quyết định tại cơ quan.
            - **Kết quả:** Nhìn thấu động cơ ngầm và cấu trúc vận hành của mọi tổ chức.
            """)
        with c_w3:
            st.markdown("""
            ### 📅 TUẦN 3: Luyện Phản Xạ Đa Ngành
            **Mục tiêu: Luyện tập Lollapalooza Synthesis**
            - **Thời gian:** 15 phút mỗi tối.
            - **Nhiệm vụ:** Không đọc thêm lý thuyết; đưa các vấn đề thực tế vào **Latticework Sandbox**.
            - **Thực hành:**
              1. Đặt mục tiêu mỗi quyết định quan trọng phải được soi qua ít nhất 3 lăng kính khác ngành.
              2. Tự thiết kế các cơ chế Win-Win dựa trên Lý thuyết trò chơi và Hệ sinh thái.
            - **Kết quả:** Hình thành trực giác tinh hoa, biến mạng lưới mô hình thành bản năng phản xạ tự nhiên.
            """)

    st.divider()
    st.info("🎯 **Sẵn sàng kiểm tra phản xạ của bạn?** Vào ngay **Tab [⚡ Đấu trường Luyện nhớ]** để làm trắc nghiệm tình huống 88 mô hình, lật Flashcards và thử thách Richard Feynman!")

# ========== TAB 4: Thư viện nguyên lý ==========
with tabs[4]:
    st.title("📚 Thư viện nguyên lý cốt lõi (dùng chung)")
    st.caption("Kho 100 nguyên lý khởi thủy từ Vật lý, Sinh học, Toán học, Triết học & Khoa học máy tính")
    domains = get_domains()
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        domain = st.selectbox("Lọc trụ cột", domains)
    with col_f2:
        q = st.text_input("Tìm kiếm nguyên lý", placeholder="Bayes, đòn bẩy, bảo toàn, entropy...")

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

    st.divider()
    st.info("🎯 **Muốn thử thách nhận diện 100 Nguyên lý khoa học?** Chuyển sang **Tab [⚡ Đấu trường Luyện nhớ]** để làm trắc nghiệm kiểm chứng điều kiện biên và tính khả bác!")

# ========== TAB 5: Đấu trường Luyện nhớ & Trắc nghiệm phản xạ ==========
with tabs[5]:
    st.title("⚡ Đấu Trường Luyện Nhớ & Trắc Nghiệm Phản Xạ")
    st.caption("Nắm trọn 9 Chế độ · 88 Mô hình Hạt nhân · 100 Nguyên lý Khởi thủy qua Active Recall & Case Quizzes")

    if QUIZ_IMPORT_ERROR:
        st.error(f"⚠️ **Thông báo hệ thống Quiz Engine:**\n\n```\n{QUIZ_IMPORT_ERROR}\n```")
        st.info("💡 Nếu bạn đang trên Streamlit Cloud, hãy thử bấm nút **Manage app** ở góc dưới bên phải màn hình và chọn **Reboot app** để nạp lại đầy đủ các module mới.")

    # Thống kê thành tích làm chủ
    mastery_data = get_user_mastery_summary(username)
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("🎯 Độ chính xác Trắc nghiệm", f"{mastery_data['accuracy']}%", f"{mastery_data['total_quizzes']} lượt test")
    with col_m2:
        st.metric("🟢 Đã làm chủ (Mastered)", f"{mastery_data['mastered_count']} / 88", f"{mastery_data['mastery_pct']}% tổng mô hình")
    with col_m3:
        st.metric("🟡 Đang ghi nhớ", f"{mastery_data['learning_count']} thẻ")
    with col_m4:
        st.metric("🔴 Cần ôn tập lại", f"{mastery_data['review_count']} thẻ")

    st.progress(mastery_data["mastery_pct"] / 100.0)

    arena_tab_diag, arena_tab_th, arena_tab1, arena_tab2, arena_tab3 = st.tabs([
        "🧭 Chẩn Đoán Điểm Mù Nhận Thức",
        "📖 Trắc Nghiệm Lý Thuyết Cốt Lõi",
        "🎯 Trắc Nghiệm Tình Huống Thực Chiến",
        "🗂️ Thẻ Flashcards Phản Xạ 5 Giây",
        "✨ AI Đấu Trí & Thử Thách Feynman"
    ])

    # -------------------------------------------------------------------------
    # Sub-tab 0: Chẩn Đoán Điểm Mù Nhận Thức (Cognitive Blindspot Diagnostic)
    # -------------------------------------------------------------------------
    with arena_tab_diag:
        st.markdown("### 🧭 Chẩn Đoán 6 Chiều Không Gian Nhận Thức & Điểm Mù Tinh Hoa")
        st.caption("Khám phá bản đồ nhận thức của bạn qua 12 tình huống bẫy thực tế. Định vị thế mạnh và vạch trần điểm mù trước khi bước vào các quyết định lớn của cuộc đời.")

        latest_diag = get_latest_diagnostic_result(username)

        retake_key = "retake_diagnostic_flag"
        show_test_form = (latest_diag is None) or st.session_state.get(retake_key, False)

        if latest_diag and not show_test_form:
            st.success(f"🏆 Kết quả chẩn đoán gần nhất của bạn ({latest_diag.get('timestamp')})")
            
            d_c1, d_c2, d_c3 = st.columns([1.5, 1.5, 2])
            with d_c1:
                st.metric("🎯 Chỉ Số Nhận Thức (Cognitive Index)", f"{latest_diag.get('overall_index')}%")
            with d_c2:
                st.markdown(f"**Danh hiệu:**  \n### 🎖️ {latest_diag.get('rank_title')}")
                st.caption(latest_diag.get('rank_desc', ''))
            with d_c3:
                ts = latest_diag.get('top_strength', {})
                cb = latest_diag.get('critical_blindspot', {})
                st.markdown(f"🟢 **Thế mạnh:** {ts.get('name', '')} ({ts.get('score', 0)}%)")
                st.markdown(f"🔴 **Điểm mù chí mạng:** {cb.get('name', '')} ({cb.get('score', 0)}%)")

            st.divider()
            st.markdown("#### 📊 Điểm Chi Tiết 6 Chiều Không Gian Nhận Thức")
            dim_scores = latest_diag.get("dimension_scores", {})
            dim_cols = st.columns(3)
            col_idx = 0
            for dim_key, dim_info in COGNITIVE_DIMENSIONS.items():
                sc = dim_scores.get(dim_key, 0)
                with dim_cols[col_idx % 3]:
                    st.markdown(f"**{dim_info['icon']} {dim_info['name']}**")
                    st.progress(sc / 100.0)
                    st.caption(f"Điểm số: **{sc}%** — *{dim_info['description']}*")
                col_idx += 1

            st.divider()
            st.markdown("#### 🗺️ Lộ Trình Hành Động Đề Xuất 3–6 Tháng Cho Bạn:")
            for rec in latest_diag.get("recommendations", []):
                st.info(f"💡 {rec}")

            if st.button("🔄 Làm lại bài test chẩn đoán (12 câu hỏi)", use_container_width=True):
                st.session_state[retake_key] = True
                st.rerun()

        else:
            st.info("📝 Hãy chọn phương án phản ánh **chính xác nhất phản xạ tự nhiên của bạn trong thực tế**, không chọn theo câu trả lời nghe có vẻ 'đẹp đẽ' nhất để có kết quả chẩn đoán trung thực nhất.")

            user_diag_answers = {}
            for idx, q in enumerate(DIAGNOSTIC_QUESTIONS, 1):
                dim_info = COGNITIVE_DIMENSIONS.get(q["dimension"], {})
                st.markdown(f"##### Câu {idx}: {dim_info.get('icon', '🔹')} {q['title']}")
                st.write(q["scenario"])
                
                options_text = [opt["text"] for opt in q["options"]]
                chosen_opt_text = st.radio(
                    f"Lựa chọn của bạn cho câu {idx}:",
                    options_text,
                    key=f"diag_q_{q['id']}",
                    index=None,
                )
                if chosen_opt_text:
                    chosen_idx = options_text.index(chosen_opt_text)
                    user_diag_answers[q["id"]] = chosen_idx

                st.markdown("---")

            if st.button("📊 Nộp Bài & Xuất Báo Cáo Chẩn Đoán Điểm Mù", type="primary", use_container_width=True):
                if len(user_diag_answers) < len(DIAGNOSTIC_QUESTIONS):
                    st.warning(f"Bạn mới trả lời {len(user_diag_answers)}/{len(DIAGNOSTIC_QUESTIONS)} câu. Vui lòng hoàn thành toàn bộ câu hỏi để có kết quả chính xác.")
                else:
                    eval_res = evaluate_diagnostic_submission(user_diag_answers)
                    save_user_diagnostic_result(username, eval_res)
                    st.session_state[retake_key] = False
                    st.success("✅ Đã hoàn tất chẩn đoán điểm mù nhận thức! Đang tải báo cáo...")
                    st.rerun()

    # -------------------------------------------------------------------------
    # Sub-tab 1: Trắc Nghiệm Lý Thuyết Cốt Lõi (Theory Foundation Quiz)
    # -------------------------------------------------------------------------
    with arena_tab_th:
        st.markdown("### 📖 Trắc Nghiệm Lý Thuyết Cốt Lõi & Ma Trận Phản Xạ Đa Chiều")
        st.caption("Muốn làm chủ tư duy đỉnh cao, bạn phải hiểu lý thuyết thật rành mạch: từ Chân lý gốc, Đòn bẩy tối thượng, Bẫy đảo ngược cho đến Ma trận phân biệt tương hỗ giữa các mô hình.")

        if "th_shuffle_seed" not in st.session_state:
            st.session_state["th_shuffle_seed"] = 42

        th_category = st.radio(
            "Chọn phân hệ trắc nghiệm lý thuyết",
            [
                "🧠 9 Chế độ Tư duy Tinh hoa (27 câu hỏi đa chiều)",
                "🕸️ 88 Mô hình Hạt nhân (Toàn bộ 88 mô hình · Ma trận 352 câu)",
                "🔬 100 Nguyên lý Khởi thủy (Toàn bộ 100 nguyên lý khoa học · Ma trận 352 câu)"
            ],
            horizontal=True,
            key="th_quiz_cat_radio"
        )

        th_selected_questions = []
        th_cat_key = ""

        if "9 Chế độ" in th_category:
            th_cat_key = "th_modes"
            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                th_mode_angle = st.selectbox(
                    "Góc độ khảo sát lý thuyết:",
                    [
                        "🌟 Tất cả 3 góc độ (27 câu hỏi chuyên sâu)",
                        "🔬 Bản chất & Định nghĩa cốt lõi (9 câu)",
                        "⚡ Quy trình & Kích hoạt vận hành (9 câu)",
                        "⚠️ Bẫy tư duy đối nghịch & Lỗi ngụy biện (9 câu)"
                    ],
                    key="th_mode_angle_sel"
                )
            with col_m2:
                if st.button("🎲 Xáo trộn câu hỏi", key="btn_shuf_modes", use_container_width=True):
                    st.session_state["th_shuffle_seed"] = random.randint(1, 999999)
                    st.rerun()

            angle_map = {
                "🌟 Tất cả 3 góc độ (27 câu hỏi chuyên sâu)": "all",
                "🔬 Bản chất & Định nghĩa cốt lõi (9 câu)": "concept",
                "⚡ Quy trình & Kích hoạt vận hành (9 câu)": "operation",
                "⚠️ Bẫy tư duy đối nghịch & Lỗi ngụy biện (9 câu)": "trap"
            }
            th_selected_questions = get_theory_questions_for_modes(angle=angle_map.get(th_mode_angle, "all"))
            st.info(f"📋 Khoang thi **9 Chế độ Tư duy Tinh hoa** đang hiển thị **{len(th_selected_questions)} câu hỏi lý thuyết**. Khắc sâu bản chất lý thuyết, quy trình vận hành và bẫy tư duy đối nghịch.")

        elif "88 Mô hình" in th_category:
            th_cat_key = "th_models"
            col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
            with col_f1:
                th_scope = st.selectbox(
                    "Phạm vi mô hình:",
                    [
                        "🌐 Toàn bộ 88 Mô hình (100% đầy đủ)",
                        "⭐ 25 Siêu mô hình Tier 1 Pareto (80/20)",
                        "🎯 37 Mô hình Chiến lược Tier 2",
                        "🔬 26 Mô hình Chuyên sâu Tier 3"
                    ],
                    key="th_scope_sel"
                )
            with col_f2:
                th_filter_pillar = st.selectbox("Lọc theo Trụ cột", ["Tất cả"] + get_pillars(), key="th_filter_pillar")
            with col_f3:
                th_model_angle = st.selectbox(
                    "Góc độ khảo sát:",
                    [
                        "🌟 Tất cả các góc độ (Ma trận hỗn hợp)",
                        "🔬 Chân lý gốc (First Principle)",
                        "⚡ Đòn bẩy tối thượng (Elite Leverage)",
                        "⚠️ Bẫy đảo ngược (Inversion Trap)",
                        "🔀 Ma trận Phân biệt Tương hỗ (Discriminative Matrix)"
                    ],
                    key="th_model_angle_sel"
                )

            tier_map = {
                "🌐 Toàn bộ 88 Mô hình (100% đầy đủ)": None,
                "⭐ 25 Siêu mô hình Tier 1 Pareto (80/20)": 1,
                "🎯 37 Mô hình Chiến lược Tier 2": 2,
                "🔬 26 Mô hình Chuyên sâu Tier 3": 3
            }
            angle_map = {
                "🌟 Tất cả các góc độ (Ma trận hỗn hợp)": "all",
                "🔬 Chân lý gốc (First Principle)": "first_principle",
                "⚡ Đòn bẩy tối thượng (Elite Leverage)": "leverage",
                "⚠️ Bẫy đảo ngược (Inversion Trap)": "inversion",
                "🔀 Ma trận Phân biệt Tương hỗ (Discriminative Matrix)": "matrix"
            }
            p_arg = th_filter_pillar if th_filter_pillar != "Tất cả" else None
            t_arg = tier_map.get(th_scope)
            a_arg = angle_map.get(th_model_angle, "all")

            col_btn, _ = st.columns([2, 4])
            with col_btn:
                if st.button("🎲 Xáo trộn phương án & đề mới", key="btn_shuf_models", use_container_width=True):
                    st.session_state["th_shuffle_seed"] = random.randint(1, 999999)
                    st.rerun()

            th_selected_questions = get_theory_questions_for_models(
                pillar=p_arg,
                tier=t_arg,
                angle=a_arg,
                seed=st.session_state["th_shuffle_seed"]
            )
            st.info(f"📋 Khoang thi **88 Mô hình Hạt nhân** tìm thấy **{len(th_selected_questions)} câu hỏi lý thuyết**. Khắc sâu Chân lý gốc, Đòn bẩy tối thượng, Bẫy đảo ngược và Ma trận phân biệt mô hình.")

        else:
            th_cat_key = "th_principles"
            col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
            with col_p1:
                th_domain = st.selectbox("Lọc Trụ cột khoa học", get_domains(), key="th_filter_domain")
            with col_p2:
                th_prin_angle = st.selectbox(
                    "Góc độ khảo sát:",
                    [
                        "🌟 Tất cả các góc độ (Ma trận hỗn hợp)",
                        "🔬 Định nghĩa hình thức & Trực giác",
                        "⚖️ Điều kiện biên nghiệm đúng",
                        "💥 Phép thử bác bỏ (Karl Popper Falsification)",
                        "🔀 Ma trận Phân biệt Nguyên lý"
                    ],
                    key="th_prin_angle_sel"
                )
            with col_p3:
                if st.button("🎲 Xáo trộn phương án & đề mới", key="btn_shuf_prin", use_container_width=True):
                    st.session_state["th_shuffle_seed"] = random.randint(1, 999999)
                    st.rerun()

            angle_p_map = {
                "🌟 Tất cả các góc độ (Ma trận hỗn hợp)": "all",
                "🔬 Định nghĩa hình thức & Trực giác": "definition",
                "⚖️ Điều kiện biên nghiệm đúng": "boundary",
                "💥 Phép thử bác bỏ (Karl Popper Falsification)": "falsification",
                "🔀 Ma trận Phân biệt Nguyên lý": "matrix"
            }
            d_arg = th_domain if th_domain != "Tất cả" else None
            a_p_arg = angle_p_map.get(th_prin_angle, "all")

            th_selected_questions = get_theory_questions_for_principles(
                domain=d_arg,
                angle=a_p_arg,
                seed=st.session_state["th_shuffle_seed"]
            )
            st.info(f"📋 Khoang thi **100 Nguyên lý Khởi thủy** tìm thấy **{len(th_selected_questions)} câu hỏi khoa học**. Khắc sâu định nghĩa hình thức, điều kiện biên, tính khả bác và ma trận nhận diện nguyên lý.")

        th_score = 0
        th_answered = 0

        # Slider to choose how many questions to display
        if len(th_selected_questions) > 10:
            default_lim = min(25, len(th_selected_questions))
            th_max_display = st.slider(
                "Số lượng câu hỏi kiểm tra đợt này:",
                min_value=5,
                max_value=len(th_selected_questions),
                value=default_lim,
                step=5 if len(th_selected_questions) <= 100 else 10,
                key=f"th_slider_limit_{th_cat_key}"
            )
            th_display_questions = th_selected_questions[:th_max_display]
        else:
            th_display_questions = th_selected_questions

        for i, q in enumerate(th_display_questions):
            q_title = q.get('concept') or q.get('model_name') or q.get('principle_name') or f"Câu {i+1}"
            q_angle_tag = q.get('angle_label', '')
            exp_header = f"Câu {i+1}: {q_title}"
            if q_angle_tag:
                exp_header += f" · [{q_angle_tag}]"

            with st.expander(exp_header, expanded=(i < 2)):
                st.markdown(f"**❓ Câu hỏi lý thuyết:** **{q.get('question')}**")

                th_state_key = f"th_ans_{th_cat_key}_{q.get('id')}_{st.session_state.get('th_shuffle_seed', 42)}"
                th_user_choice = st.radio(
                    "Chọn đáp án chính xác:",
                    q.get("options", []),
                    key=th_state_key,
                    index=None
                )

                if th_user_choice is not None:
                    th_answered += 1
                    th_chosen_idx = q["options"].index(th_user_choice)
                    th_is_correct = (th_chosen_idx == q["correct_index"])

                    if th_is_correct:
                        th_score += 1
                        st.success("🎉 **CHÍNH XÁC!** Bạn đã nắm rất rành mạch lý thuyết cốt lõi này.")
                    else:
                        st.error(f"❌ **CHƯA CHÍNH XÁC!** Đáp án chuẩn là: **{q['options'][q['correct_index']]}**")

                    st.markdown(f"💡 **Chân lý gốc / Định nghĩa cốt lõi:** {q.get('explanation')}")
                    st.markdown(f"⚠️ **Bẫy ngụy biện & Ranh giới điều kiện biên:** {q.get('trap_analysis')}")

        st.divider()
        c_thr1, c_thr2 = st.columns([2, 1])
        with c_thr1:
            if th_answered > 0:
                th_pct = round(th_score / th_answered * 100, 1)
                st.markdown(f"#### 📊 Kết quả trắc nghiệm lý thuyết: **{th_score}/{th_answered} câu đúng ({th_pct}%)**")
            else:
                st.caption("Hãy chọn đáp án cho các câu hỏi lý thuyết phía trên để kiểm tra kết quả.")
        with c_thr2:
            if th_answered > 0 and st.button("💾 Ghi nhận lượt thi lý thuyết vào Lịch sử", type="primary", use_container_width=True, key="btn_save_th_quiz"):
                record_quiz_completion(username, f"Lý thuyết: {th_category}", th_score, th_answered)
                st.success("🎉 Đã lưu kết quả thi lý thuyết vào Lịch sử cá nhân! Tăng cường điểm số Mastery.")
                st.rerun()

    # -------------------------------------------------------------------------
    # Sub-tab 2: Trắc Nghiệm Tình Huống Thực Chiến
    # -------------------------------------------------------------------------
    with arena_tab1:
        st.markdown("### 🎯 Trắc Nghiệm Tình Huống Phản Xạ (Case-Based Reflex Quiz)")
        st.caption("Mỗi câu hỏi là một tình huống thực tế hóc búa. Đọc tình huống, chọn mô hình chi phối và giải mã bẫy ngụy biện.")

        quiz_category = st.radio(
            "Chọn khoang bài thi trắc nghiệm",
            [
                "🧠 9 Chế độ Tư duy Tinh hoa (9 tình huống kinh điển)",
                "🕸️ 88 Mô hình Hạt nhân (Munger Latticework)",
                "🔬 100 Nguyên lý Khởi thủy (Quy luật khoa học nền tảng)"
            ],
            horizontal=True
        )

        selected_questions = []
        cat_key = ""
        if "9 Chế độ" in quiz_category:
            selected_questions = MODES_QUIZ
            cat_key = "modes"
        elif "88 Mô hình" in quiz_category:
            cat_key = "models"
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                filter_pillar = st.selectbox("Lọc theo Trụ cột", ["Tất cả"] + get_pillars())
            with col_q2:
                only_tier1 = st.checkbox("Chỉ luyện 25 Mô hình Siêu hạt nhân (Tier 1 Pareto)", value=True)

            filtered_q = MODELS_QUIZ
            if filter_pillar != "Tất cả":
                filtered_q = [q for q in filtered_q if q.get("pillar") == filter_pillar]
            if only_tier1:
                filtered_q = [q for q in filtered_q if q.get("tier") == 1]
            selected_questions = filtered_q if filtered_q else MODELS_QUIZ
        else:
            cat_key = "principles"
            selected_questions = PRINCIPLES_QUIZ

        st.info(f"📋 Khoang thi hiện có **{len(selected_questions)} câu hỏi tình huống**. Hãy đọc kỹ tình huống để tìm ra bản chất:")

        quiz_score = 0
        answered_count = 0

        for i, q in enumerate(selected_questions):
            with st.expander(f"Câu {i+1}: {q.get('concept', q.get('model_name', q.get('principle_name', 'Tình huống')))}", expanded=(i < 2)):
                st.markdown(f"**📖 Bối cảnh tình huống:**\n> *{q.get('scenario')}*")
                st.markdown(f"**❓ Câu hỏi:** **{q.get('question')}**")

                state_key = f"quiz_ans_{cat_key}_{q.get('id')}"
                user_choice = st.radio(
                    "Chọn phương án trả lời:",
                    q.get("options", []),
                    key=state_key,
                    index=None
                )

                if user_choice is not None:
                    answered_count += 1
                    chosen_idx = q["options"].index(user_choice)
                    is_correct = (chosen_idx == q["correct_index"])

                    if is_correct:
                        quiz_score += 1
                        st.success("🎉 **CHÍNH XÁC TUYỆT ĐỐI!** Bạn đã nhìn xuyên qua bề mặt để chạm vào bản chất gốc.")
                    else:
                        st.error(f"❌ **CHƯA CHÍNH XÁC!** Đáp án đúng là: **{q['options'][q['correct_index']]}**")

                    st.markdown(f"💡 **Chân lý gốc (First Principles):** {q.get('explanation')}")
                    st.markdown(f"⚠️ **Phân tích Bẫy ngụy biện:** {q.get('trap_analysis')}")

        st.divider()
        col_res1, col_res2 = st.columns([2, 1])
        with col_res1:
            if answered_count > 0:
                pct = round(quiz_score / answered_count * 100, 1)
                st.markdown(f"#### 📊 Kết quả tạm tính: **{quiz_score}/{answered_count} câu đúng ({pct}%)**")
            else:
                st.caption("Hãy chọn đáp án cho các câu hỏi phía trên để tính điểm.")
        with col_res2:
            if answered_count > 0 and st.button("💾 Ghi nhận lượt thi vào Lịch sử cá nhân", type="primary", use_container_width=True):
                record_quiz_completion(username, quiz_category, quiz_score, answered_count)
                st.success("🎉 Đã lưu thành tích vào Lịch sử của bạn! Cập nhật lại chỉ số Mastery.")
                st.rerun()

    # -------------------------------------------------------------------------
    # Sub-tab 2: Thẻ Flashcards Phản Xạ 5 Giây (Active Recall)
    # -------------------------------------------------------------------------
    with arena_tab2:
        st.markdown("### 🗂️ Thẻ Flashcards Phản Xạ 5 Giây (Active Recall & Spaced Repetition)")
        st.caption("Phương pháp ghi nhớ đỉnh cao: Đọc câu hỏi kích hoạt 5 giây ➔ Lật thẻ đối chiếu ➔ Tự đánh giá để hệ thống vẽ biểu đồ trí nhớ.")

        fc_col1, fc_col2, fc_col3 = st.columns([2, 2, 1])
        with fc_col1:
            fc_cat = st.selectbox("Bộ thẻ", ["88 Mô hình Hạt nhân", "9 Chế độ Tư duy", "100 Nguyên lý Khởi thủy", "Tất cả thẻ"])
        with fc_col2:
            fc_filter_pillar = "Tất cả"
            if "88 Mô hình" in fc_cat:
                fc_filter_pillar = st.selectbox("Lọc Trụ cột", ["Tất cả"] + get_pillars())
        with fc_col3:
            fc_tier = None
            if "88 Mô hình" in fc_cat:
                if st.checkbox("Tier 1 Pareto", value=False):
                    fc_tier = 1

        filter_type_map = {
            "88 Mô hình Hạt nhân": "models",
            "9 Chế độ Tư duy": "modes",
            "100 Nguyên lý Khởi thủy": "principles",
            "Tất cả thẻ": "all"
        }
        raw_cards = get_all_flashcards(
            filter_type=filter_type_map.get(fc_cat, "models"),
            pillar=fc_filter_pillar if fc_filter_pillar != "Tất cả" else None,
            tier=fc_tier
        )

        if not raw_cards:
            st.warning("Không tìm thấy thẻ nào phù hợp với bộ lọc.")
        else:
            if "fc_card_idx" not in st.session_state:
                st.session_state["fc_card_idx"] = 0
            if "fc_is_flipped" not in st.session_state:
                st.session_state["fc_is_flipped"] = False

            total_c = len(raw_cards)
            curr_idx = st.session_state["fc_card_idx"] % total_c
            card = raw_cards[curr_idx]

            st.caption(f"Thẻ **{curr_idx + 1} / {total_c}** · {card.get('front_badge')}")

            # Giao diện Thẻ lật
            with st.container(border=True):
                if not st.session_state["fc_is_flipped"]:
                    st.markdown(f"## ❓ {card.get('name_vi')} *({card.get('name_en', '')})*")
                    st.markdown(f"### ⚡ Câu hỏi kích hoạt 5 giây:\n> **\"{card.get('front_trigger')}\"**")
                    st.caption("💭 Hãy nhắm mắt lại 5 giây: Bạn có định nghĩa được chân lý gốc, đòn bẩy và bẫy đảo ngược của mô hình này không?")
                    
                    if st.button("🔄 Lật thẻ xem Chân lý gốc & Đòn bẩy Elite", type="primary", use_container_width=True):
                        st.session_state["fc_is_flipped"] = True
                        st.rerun()
                else:
                    st.markdown(f"## 💡 {card.get('name_vi')} *({card.get('name_en', '')})*")
                    st.info(f"🔬 **Chân lý gốc (First Principle):**\n\n{card.get('back_principle')}")
                    st.success(f"⚡ **Đòn bẩy Elite:**\n\n{card.get('back_leverage')}")
                    st.warning(f"⚠️ **Bẫy đảo ngược (Inversion Trap):**\n\n{card.get('back_trap')}")
                    if card.get("back_lollapalooza"):
                        st.caption(f"🔗 **Cặp cộng hưởng Lollapalooza:** {card.get('back_lollapalooza')}")

                    st.markdown("#### Tự đánh giá mức độ ghi nhớ:")
                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                    with btn_c1:
                        if st.button("🔴 Chưa nhớ (Cần ôn lại)", use_container_width=True):
                            update_flashcard_mastery(username, card.get("id"), "review_needed")
                            st.session_state["fc_is_flipped"] = False
                            st.session_state["fc_card_idx"] = (curr_idx + 1) % total_c
                            st.rerun()
                    with btn_c2:
                        if st.button("🟡 Nhớ mang máng", use_container_width=True):
                            update_flashcard_mastery(username, card.get("id"), "learning")
                            st.session_state["fc_is_flipped"] = False
                            st.session_state["fc_card_idx"] = (curr_idx + 1) % total_c
                            st.rerun()
                    with btn_c3:
                        if st.button("🟢 Đã thuộc làu (Mastered)", type="primary", use_container_width=True):
                            update_flashcard_mastery(username, card.get("id"), "mastered")
                            st.session_state["fc_is_flipped"] = False
                            st.session_state["fc_card_idx"] = (curr_idx + 1) % total_c
                            st.rerun()

                    if st.button("🔄 Úp thẻ lại mặt trước", use_container_width=True):
                        st.session_state["fc_is_flipped"] = False
                        st.rerun()

            # Điều hướng thẻ
            nav_c1, nav_c2, nav_c3 = st.columns([1, 1, 1])
            with nav_c1:
                if st.button("⬅️ Thẻ trước", use_container_width=True):
                    st.session_state["fc_is_flipped"] = False
                    st.session_state["fc_card_idx"] = (curr_idx - 1) % total_c
                    st.rerun()
            with nav_c2:
                if st.button("🎲 Thẻ ngẫu nhiên", use_container_width=True):
                    st.session_state["fc_is_flipped"] = False
                    st.session_state["fc_card_idx"] = random.randint(0, total_c - 1)
                    st.rerun()
            with nav_c3:
                if st.button("Thẻ tiếp theo ➡️", use_container_width=True):
                    st.session_state["fc_is_flipped"] = False
                    st.session_state["fc_card_idx"] = (curr_idx + 1) % total_c
                    st.rerun()

    # -------------------------------------------------------------------------
    # Sub-tab 3: AI Đấu Trí & Thử Thách Feynman
    # -------------------------------------------------------------------------
    with arena_tab3:
        st.markdown("### ✨ AI Đấu Trí & Thử Thách Feynman")
        st.caption("Khắc sâu bản chất bằng cách giải thích cho đứa trẻ 10 tuổi hiểu hoặc yêu cầu AI tạo đề thi tình huống mới toanh.")

        ai_sec1, ai_sec2 = st.tabs(["✨ AI Tạo Đề Trắc Nghiệm Động", "🔬 Thử Thách Feynman (Socratic Arena)"])

        with ai_sec1:
            st.markdown("#### 🎲 AI Tự Động Sinh Đề Trắc Nghiệm Tình Huống Mới Toanh")
            st.caption("Không bị gò bó bởi các câu hỏi có sẵn; AI Gemini sẽ tạo câu hỏi theo tình huống đời thực bạn đưa vào.")

            ai_col1, ai_col2 = st.columns(2)
            with ai_col1:
                ai_quiz_cat = st.selectbox(
                    "Loại mô hình cần kiểm tra",
                    ["88 Mô hình Hạt nhân (Charlie Munger)", "9 Chế độ Tư duy Tinh hoa", "100 Nguyên lý Khởi thủy"]
                )
                ai_quiz_num = st.slider("Số lượng câu hỏi", 2, 5, 3)
            with ai_col2:
                ai_quiz_topic = st.text_input(
                    "Chủ đề / Bối cảnh thực tế mong muốn",
                    value="Thị trường chứng khoán Việt Nam, Bắt đáy cổ phiếu & FOMO đám đông",
                    help="Gõ bất kỳ chủ đề nào: Khởi nghiệp SaaS, Học sinh Wellspring giải quyết bài tập, Quản trị sa thải..."
                )

            if st.button("🚀 AI Tạo Đề Thi Tình Huống Ngay", type="primary", use_container_width=True):
                if not active_keys:
                    st.warning("Cần cấu hình Gemini API Key.")
                else:
                    with st.spinner("AI đang thiết kế các tình huống thực tế hóc búa..."):
                        generated_quiz = generate_ai_quiz(
                            active_keys,
                            model_choice,
                            category=ai_quiz_cat,
                            topic=ai_quiz_topic.strip(),
                            num_questions=ai_quiz_num
                        )
                    if generated_quiz:
                        st.session_state["current_ai_quiz"] = generated_quiz
                        st.success(f"🎉 Đã sinh thành công {len(generated_quiz)} câu hỏi tình huống mới toanh!")
                    else:
                        st.error("Không thể sinh câu hỏi bằng AI lúc này. Vui lòng kiểm tra lại API Key.")

            if "current_ai_quiz" in st.session_state and st.session_state["current_ai_quiz"]:
                st.markdown("---")
                st.markdown("#### 📝 Đề Thi Tình Huống Do AI Thiết Kế:")
                for idx, q_ai in enumerate(st.session_state["current_ai_quiz"]):
                    with st.expander(f"Tình huống {idx+1}: {q_ai.get('concept')}", expanded=True):
                        st.markdown(f"**📖 Bối cảnh:**\n> *{q_ai.get('scenario')}*")
                        st.markdown(f"**❓ Câu hỏi:** **{q_ai.get('question')}**")

                        choice = st.radio("Lựa chọn của bạn:", q_ai.get("options", []), key=f"ai_q_{idx}", index=None)
                        if choice is not None:
                            c_idx = q_ai["options"].index(choice)
                            if c_idx == q_ai.get("correct_index"):
                                st.success("🎉 **CHÍNH XÁC!** Bạn đã nhận diện chuẩn xác mô hình.")
                            else:
                                st.error(f"❌ **CHƯA ĐÚNG!** Đáp án chuẩn: {q_ai['options'][q_ai.get('correct_index')]}")
                            st.info(f"💡 **First Principles:** {q_ai.get('explanation')}")
                            st.warning(f"⚠️ **Bẫy ngụy biện:** {q_ai.get('trap_analysis')}")

        with ai_sec2:
            st.markdown("#### 🔬 Thử Thách Kỹ Thuật Feynman: 'Giải thích cho học sinh lớp 6 hiểu'")
            st.markdown("""
            > *"Bạn không thực sự hiểu điều gì cho đến khi bạn có thể giải thích nó bằng ngôn ngữ đơn giản nhất cho một đứa trẻ 10 tuổi mà không dùng bất kỳ từ ngữ cao siêu nào."* — **Richard Feynman**
            """)

            fey_col1, fey_col2 = st.columns([1, 2])
            with fey_col1:
                concept_source = st.radio("Khái niệm từ nguồn", ["88 Mô hình Hạt nhân", "9 Chế độ Tư duy"])
                if "88 Mô hình" in concept_source:
                    all_m = get_all_models()
                    m_names = [f"{m['name_vi']} ({m['name_en']})" for m in all_m]
                    chosen_concept = st.selectbox("Chọn mô hình", m_names)
                    c_type = "Mô hình Hạt nhân"
                else:
                    mode_names = [q["concept"] for q in MODES_QUIZ]
                    chosen_concept = st.selectbox("Chọn chế độ", mode_names)
                    c_type = "Chế độ Tư duy Elite"

            with fey_col2:
                user_feynman_exp = st.text_area(
                    f"Lời giải thích của bạn về '{chosen_concept}' cho một đứa trẻ:",
                    height=130,
                    placeholder="Hãy dùng một ví dụ trong đồ chơi, đời sống gia đình, trường học... Tuyệt đối không dùng các thuật ngữ chuyên môn."
                )

                if st.button("🎯 Nộp bài cho Giám khảo Feynman chấm điểm", type="primary", use_container_width=True):
                    if not active_keys:
                        st.warning("Cần cấu hình Gemini API Key.")
                    elif not user_feynman_exp.strip():
                        st.warning("Hãy nhập lời giải thích của bạn.")
                    else:
                        with st.spinner("Richard Feynman AI đang lắng nghe và phản biện..."):
                            fey_res = evaluate_feynman_challenge(
                                active_keys,
                                model_choice,
                                concept_name=chosen_concept,
                                concept_type=c_type,
                                user_explanation=user_feynman_exp.strip()
                            )
                        if fey_res:
                            score = fey_res.get("feynman_score", 5)
                            verdict = fey_res.get("verdict", "")
                            st.metric("🏆 Điểm Thấu Suốt Feynman", f"{score} / 10", verdict)

                            st.success(f"✨ **Điểm sáng:** {fey_res.get('praise')}")
                            st.warning(f"🔍 **Điểm mù / Lỗ hổng:** {fey_res.get('blind_spots')}")
                            st.info(f"💡 **Phiên bản Richard Feynman giải thích:**\n\n> *\"{fey_res.get('feynman_refinement')}\"*")
                        else:
                            st.error("Không thể kết nối với AI. Vui lòng thử lại.")

# ========== TAB 6: Đào tạo tư duy ==========
with tabs[6]:
    st.title("🎓 Đào tạo tư duy theo lộ trình đa tầng")
    st.caption("Hệ thống rèn luyện phản xạ 15 phút mỗi ngày kèm lộ trình 3 cấp độ cho K12 Wellspring & Người lớn.")

    tab6_subtabs = st.tabs([
        "🔥 Elite Daily Workout (15 Phút Hàng Ngày & Streak)",
        "📚 Lộ Trình Đào Tạo Theo Cấp Độ (K12 & Người Lớn)",
    ])

    # -------------------------------------------------------------------------
    # Sub-tab 0: Elite Daily Workout
    # -------------------------------------------------------------------------
    with tab6_subtabs[0]:
        st.markdown("### 🔥 Elite Daily Workout — Rèn Luyện Phản Xạ 15 Phút Mỗi Ngày")
        st.caption("Nguyên lý Chuỗi Hạt (Seinfeld Streak): Mỗi ngày 1 tình huống thực chiến · 3 bước phân rã chuẩn Elite · Cài đặt tư duy vào tầng tiềm thức sau 90 ngày.")

        u_streak = get_user_streak_info(username)
        s_count = u_streak["current_streak"]
        s_status = "⚡ Đang khởi động" if s_count < 7 else ("🔥 Thói quen thép" if s_count < 30 else "🏆 Phản xạ vô thức")

        w_col1, w_col2, w_col3, w_col4 = st.columns(4)
        with w_col1:
            st.metric("🔥 Chuỗi Streak", f"{s_count} ngày", s_status)
        with w_col2:
            st.metric("🏆 Kỷ lục chuỗi", f"{u_streak['longest_streak']} ngày")
        with w_col3:
            st.metric("📝 Đã hoàn thành", f"{u_streak['total_completed']} bài")
        with w_col4:
            if u_streak["is_done_today"]:
                st.success("✅ Hôm nay: Đã xong!")
            else:
                st.warning("⏳ Hôm nay: Chưa làm")

        st.divider()

        w_track = st.radio(
            "Chọn chủ đề bài tập hôm nay:",
            ["all", "k12", "adult"],
            format_func=lambda x: "🌐 Đa Lĩnh Vực / Tổng Hợp" if x == "all" else ("🎒 Học Sinh Wellspring (K12)" if x == "k12" else "💼 Chuyên Sâu Người Lớn"),
            horizontal=True,
            key="dw_track_filter",
        )

        today_workout = get_today_workout(track=w_track)

        st.markdown(f"#### 🎯 Bài Tập Hôm Nay: {today_workout['title']}")
        st.info(f"**Tình huống thực tế:**\n\n{today_workout['scenario']}")
        st.caption("Các nguyên lý / mô hình định hướng: " + " · ".join([f"`{p}`" for p in today_workout.get('guiding_principles', [])]))

        with st.form(key=f"form_dw_{today_workout['id']}"):
            st.markdown(f"##### 1️⃣ {today_workout['step1_prompt']}")
            dw_ans_step1 = st.text_area(
                "Phân tích Sự thật vs Ý kiến:",
                height=90,
                placeholder="Chỉ ra rõ: Sự thật đo lường được là gì? Điều gì chỉ là ý kiến, phỏng đoán hoặc cảm xúc đám đông?",
                key="dw_step1_input",
            )

            st.markdown(f"##### 2️⃣ {today_workout['step2_prompt']}")
            dw_ans_step2 = st.text_area(
                "Chiếu lăng kính mô hình hạt nhân:",
                height=90,
                placeholder="Gọi tên chính xác mô hình hạt nhân (Tâm lý, Vật lý, Kinh tế) đang chi phối tình huống này và cơ chế của nó...",
                key="dw_step2_input",
            )

            st.markdown(f"##### 3️⃣ {today_workout['step3_prompt']}")
            dw_ans_step3 = st.text_area(
                "Đề xuất hành động bất đối xứng:",
                height=90,
                placeholder="Nếu ở vị thế người trong cuộc, nước cờ tối ưu nào giúp hạn chế tối đa rủi ro tổn thất và đón đầu thặng dư lớn nhất?",
                key="dw_step3_input",
            )

            submit_dw = st.form_submit_button("🔥 Hoàn Tất 15 Phút & Nhận Phản Hồi AI Mentor", type="primary", use_container_width=True)

        if submit_dw:
            if not dw_ans_step1.strip() or not dw_ans_step2.strip() or not dw_ans_step3.strip():
                st.warning("Vui lòng hoàn thành đủ cả 3 bước để bài tập đạt hiệu quả rèn luyện tối đa.")
            else:
                with st.spinner("AI Mentor đang đánh giá bài tập 15 phút của bạn..."):
                    ai_dw_feedback = evaluate_daily_workout(
                        active_keys,
                        model_choice,
                        today_workout,
                        dw_ans_step1.strip(),
                        dw_ans_step2.strip(),
                        dw_ans_step3.strip(),
                    )
                
                rec_res = record_daily_workout_answer(
                    username=username,
                    workout_id=today_workout["id"],
                    workout_title=today_workout["title"],
                    step1_ans=dw_ans_step1.strip(),
                    step2_ans=dw_ans_step2.strip(),
                    step3_ans=dw_ans_step3.strip(),
                    ai_feedback=ai_dw_feedback,
                )

                st.balloons()
                st.success(f"🎉 Xuất sắc! Bạn đã duy trì chuỗi Streak lên **{rec_res['current_streak']} ngày liên tục**!")
                
                st.markdown("#### 🌟 Nhận Xét Phản Biện Từ AI Mentor:")
                st.info(ai_dw_feedback)

                with st.expander("💡 Xem Gợi Ý Tinh Hoa của Bậc Thầy (Elite Hint)", expanded=True):
                    st.write(today_workout.get("elite_hint", ""))

        history_dw = u_streak.get("history", [])
        if history_dw:
            with st.expander(f"📜 Xem Lịch Sử {len(history_dw)} Bài Tập Daily Workout Đã Hoàn Thành"):
                for h_item in history_dw[:10]:
                    st.markdown(f"**🗓️ {h_item.get('date')} — {h_item.get('title')}**")
                    st.caption(f"Bước 1: {h_item.get('step1')[:100]}...")
                    if h_item.get("ai_feedback"):
                        st.caption(f"AI Mentor: {h_item.get('ai_feedback')[:150]}...")
                    st.markdown("---")

    # -------------------------------------------------------------------------
    # Sub-tab 1: Lộ Trình Đào Tạo Theo Cấp Độ
    # -------------------------------------------------------------------------
    with tab6_subtabs[1]:
        user_group = st.radio(
            "Chọn nhóm đối tượng đào tạo",
            ["🎒 Học sinh Wellspring (Lớp 6, 9, 10)", "💼 Chuyên sâu Người lớn (Trading, CKVN, Não bộ, Phật giáo, AI)"],
            horizontal=True,
        )

        tracks_meta = get_tracks_meta()

        if "Học sinh Wellspring" in user_group:
            track_options = {
                "grade_6": "Lớp 6 (Wellspring) — Khởi đầu tự chủ & AI cơ bản",
                "grade_9": "Lớp 9 (Wellspring) — Tư duy phản biện & Chọn hướng đi",
                "grade_10": "Lớp 10 (Wellspring) — Chiến lược dự án & Đòn bẩy AI",
            }
        else:
            track_options = {
                "trading": "Trading Vàng, FX, Crypto/BTC — Xác suất & Quản trị rủi ro",
                "ckvn": "Đầu tư Chứng khoán VN — Chu kỳ & Dòng tiền Smart Money",
                "neuroscience": "Khoa học Não bộ & Nhận thức — Dopamine & Khắc phục thiên kiến",
                "buddhism": "Phật giáo & Tâm thức — Vô thường & Chánh niệm ra quyết định",
                "ai_tech": "Công nghệ AI & Tương lai — Đòn bẩy không cần xin phép",
            }
    
        c_sel1, c_sel2 = st.columns([3, 2])
        with c_sel1:
            sel_track_id = st.selectbox(
                "Khóa học / Chủ đề đào tạo",
                options=list(track_options.keys()),
                format_func=lambda x: track_options.get(x, x),
            )
        with c_sel2:
            level_choice = st.selectbox(
                "Trình độ rèn luyện",
                ["🌱 Cấp 1: Nền tảng (Foundation)", "🔥 Cấp 2: Thực hành (Practice)", "👑 Cấp 3: Nhuần nhuyễn (Mastery)"],
                index=0,
            )
    
        track_info = tracks_meta.get(sel_track_id, {})
        if track_info.get("desc"):
            st.caption(f"💡 *Mục tiêu khóa:* {track_info['desc']}")
    
        level_map = {
            "🌱 Cấp 1: Nền tảng (Foundation)": ("level_1", "Cơ bản"),
            "🔥 Cấp 2: Thực hành (Practice)": ("level_2", "Thực hành"),
            "👑 Cấp 3: Nhuần nhuyễn (Mastery)": ("level_3", "Nâng cao"),
        }
        sel_level_code, sel_level_name = level_map[level_choice]
    
        # Lấy danh sách bài học thuộc track và level đã chọn
        lessons = get_lessons_by_track(sel_track_id, sel_level_code)
    
        hist = load_user_history(username)
        user_training = hist.get("training", {})
        done_count = sum(1 for l in lessons if l["id"] in user_training)
        total_count = len(lessons)
    
        # Thanh trạng thái tiến độ cấp độ
        c_p1, c_p2 = st.columns([3, 1])
        with c_p1:
            st.progress(done_count / max(total_count, 1))
        with c_p2:
            st.caption(f"Tiến độ cấp độ: **{done_count}/{total_count}** bài")
    
        # Sub-tabs tách bạch rõ ràng giữa Lộ trình bài tập và AI Mentor sinh bài tập
        sub_train_labels = [
            f"📖 Lộ trình Bài tập ({total_count} bài)",
            "✨ AI Mentor: Tự động tạo bài tập mở rộng",
        ]
        sub_train_tabs = st.tabs(sub_train_labels)
    
        with sub_train_tabs[0]:
            if not lessons:
                st.warning(f"Chưa có bài tập nào trong `{track_options[sel_track_id]}` ({sel_level_name}).")
                st.info("👉 Hãy bấm sang tab **'✨ AI Mentor: Tự động tạo bài tập mở rộng'** bên cạnh để AI tạo bài tập đầu tiên cho bạn!")
            else:
                def format_lesson_title(l: dict) -> str:
                    done_icon = "✅" if l["id"] in user_training else "📖"
                    is_ai = " [✨ AI]" if l.get("created_by") == "AI" or "_ai_" in l.get("id", "") else ""
                    return f"{done_icon} {l.get('title', l['id'])} — ({l.get('mode', '')}){is_ai}"
    
                # Tự động chọn bài vừa tạo nếu có trong session
                target_id = st.session_state.get(f"target_lesson_{sel_track_id}_{sel_level_code}")
                default_index = 0
                if target_id:
                    for idx, l in enumerate(lessons):
                        if l.get("id") == target_id:
                            default_index = idx
                            break
    
                choice = st.selectbox(
                    f"📚 Danh sách bài tập khả dụng ({len(lessons)} bài)",
                    options=lessons,
                    index=default_index,
                    format_func=format_lesson_title,
                    key=f"sel_lesson_{sel_track_id}_{sel_level_code}",
                )
                lesson = choice
    
                st.subheader(lesson["title"])
                st.caption(f"Chế độ: **{lesson.get('mode')}** · Mức: **{lesson.get('level')}** · ID: `{lesson.get('id')}`")
                if lesson.get("related_principle"):
                    st.caption(f"Nguyên lý cốt lõi: **{lesson['related_principle']}**")
    
                st.markdown(f"**Mục tiêu:** {lesson.get('objective')}")
                st.markdown("#### Tình huống thực tế")
                st.info(lesson.get("situation", ""))
    
                st.markdown("#### Các bước hướng dẫn tư duy")
                for i, step in enumerate(lesson.get("guide_steps", []), 1):
                    st.markdown(f"{i}. {step}")
    
                with st.expander("💡 Gợi ý định hướng (mở khi cần)"):
                    st.write(lesson.get("hint", ""))
    
                st.markdown("#### Thử thách của bạn")
                st.write(lesson.get("exercise_prompt", ""))
    
                # Load previous answer if any
                prev = user_training.get(lesson["id"], {})
                prev_answer = prev.get("answer", "")
                prev_feedback = prev.get("feedback", "")
    
                answer = st.text_area("Câu trả lời của bạn", value=prev_answer, height=150, key=f"ans_{lesson['id']}")
    
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Lưu câu trả lời", use_container_width=True, key=f"save_{lesson['id']}"):
                        save_training_answer(username, lesson["id"], answer.strip())
                        st.success("Đã lưu vào tiến độ cá nhân của bạn.")
                        st.rerun()
                with col_b:
                    if st.button("🤖 Xin feedback AI", type="primary", use_container_width=True, key=f"fb_{lesson['id']}"):
                        if not answer.strip():
                            st.warning("Hãy viết câu trả lời trước khi xin feedback.")
                        elif not active_keys:
                            st.warning("Cần API Key để nhận feedback.")
                        else:
                            with st.spinner("AI Gia sư đang nhận xét và hiệu chỉnh tư duy (tự động xoay tua key)..."):
                                fb = feedback_on_answer(active_keys, model_choice, lesson, answer.strip())
                            save_training_answer(username, lesson["id"], answer.strip(), fb)
                            st.rerun()
    
                if prev_feedback:
                    st.markdown("#### Feedback từ AI Mentor")
                    st.success(prev_feedback)
    
                st.divider()
                st.info("💡 **Muốn rèn luyện thêm?** Bạn có thể bấm sang tab **'✨ AI Mentor: Tự động tạo bài tập mở rộng'** ở trên để yêu cầu thêm các tình huống thực tế khác không giới hạn!")
    
        with sub_train_tabs[1]:
            st.subheader(f"✨ AI Mentor: Tự Động Thiết Kế Bài Tập Thực Chiến")
            st.markdown(f"Tạo đề bài độc bản cho: **{track_options[sel_track_id]}** · Cấp độ: **{sel_level_name}**")
    
            quick_suggestions = {
                "grade_6": [
                    "Lập kế hoạch tự học tại nhà không bị xao nhãng",
                    "Xung đột ý kiến khi làm bài tập nhóm môn Khoa học",
                    "Bị phân tâm vì xem video ngắn TikTok/Reels quá nhiều",
                    "Phân biệt tin tức thật và tin giả trên mạng xã hội",
                ],
                "grade_9": [
                    "Chọn trường cấp 3 công lập hay quốc tế dựa trên năng lực và tài chính",
                    "Quản lý áp lực thi cử và kỳ vọng điểm số từ gia đình",
                    "Tư duy xác suất và tỷ lệ cơ sở khi giải bài thi trắc nghiệm",
                    "Từ chối lời rủ rê trốn học của bạn bè mà không làm mất lòng",
                ],
                "grade_10": [
                    "Thiết kế dự án CLB trường học tạo tác động xã hội với ngân sách 0 đồng",
                    "Xây dựng hồ sơ ngoại khóa săn học bổng du học bằng First Principles",
                    "Ứng dụng AI vào học tập hiệu quả mà không bị thụ động tư duy",
                    "Cân bằng giữa ôn luyện IELTS 8.0 và làm trưởng ban tổ chức sự kiện",
                ],
                "trading": [
                    "Quản trị tâm lý và lệnh khi Vàng biến động 50 giá trong phiên Mỹ",
                    "Chiến lược bất đối xứng (Asymmetry) khi giao dịch BTC/Crypto",
                    "Cắt lỗ dứt khoát khi phân tích sai và tránh bẫy Revenge Trading",
                    "Quản lý vốn theo tiêu chuẩn Kelly khi hệ thống có Winrate 45%",
                ],
                "ckvn": [
                    "Nhận diện dấu chân dòng tiền Smart Money (VSA) ở vùng đáy gom hàng",
                    "Phân tích chu kỳ nhóm ngành Chứng khoán - Thép - Bất động sản",
                    "Quản trị rủi ro khi thị trường phân phối đỉnh với thanh khoản kỷ lục",
                    "Định giá thực chất doanh nghiệp dựa trên dòng tiền tự do FCF",
                ],
                "neuroscience": [
                    "Cơ chế Dopamine và cách cai nghiện dopamine rẻ tiền (Cheap Dopamine)",
                    "Thực hành Deep Work 90 phút vượt qua quán tính trì hoãn của não bộ",
                    "Tái cấu trúc nhận thức (Cognitive Reframing) khi gặp stress cực đại",
                    "Khắc phục thiên kiến xác nhận khi đánh giá một cơ hội đầu tư",
                ],
                "buddhism": [
                    "Ứng dụng tư duy Vô thường để không bị dính mắc vào thành công/thất bại",
                    "Quan sát cảm xúc bằng Chánh niệm trước khi bấm nút Enter vào lệnh",
                    "Bản chất Nhân - Quả trong các mối quan hệ gia đình và đối tác",
                    "Tâm bất biến giữa dòng đời vạn biến: Quản trị sự bất định của thị trường",
                ],
                "ai_tech": [
                    "Xây dựng Agentic Workflow tự động hóa quy trình phân tích dữ liệu",
                    "Tư duy đòn bẩy không cần xin phép (Permissionless Leverage) thời AI",
                    "Thiết kế Prompt First Principles để giải quyết bài toán kỹ thuật phức tạp",
                    "Định vị năng lực cạnh tranh cốt lõi của con người khi AI làm chủ ngôn ngữ",
                ]
            }
    
            curr_suggestions = quick_suggestions.get(sel_track_id, ["Tình huống thực tế tùy biến theo chuyên môn"])
            sel_suggest = st.selectbox(
                "💡 Gợi ý chủ đề nhanh (chọn hoặc tự nhập bên dưới):",
                ["— Tự nhập tình huống riêng của bạn —"] + curr_suggestions,
                key=f"sel_sug_{sel_track_id}_{sel_level_code}",
            )
            initial_topic = "" if sel_suggest.startswith("—") else sel_suggest
    
            custom_topic = st.text_input(
                "Chủ đề hoặc tình huống bạn muốn AI ra đề thử thách:",
                value=initial_topic,
                placeholder="vd: Bài tập nhóm STEM lớp 10, quản lý lệnh Vàng phiên Mỹ, kiềm chế cơn giận khi bị chỉ trích...",
                key=f"topic_input_{sel_track_id}_{sel_level_code}",
            )
    
            if st.button("🚀 Yêu Cầu AI Sinh Bài Tập Mới Ngay", key=f"btn_gen_{sel_track_id}_{sel_level_code}", type="primary", use_container_width=True):
                if not active_keys:
                    st.warning("Cần API Key để sinh bài tập.")
                else:
                    with st.spinner("AI Mentor đang thiết kế bài tập tình huống thực chiến độc bản (tự động xoay tua API key)..."):
                        new_lesson = generate_dynamic_lesson(
                            api_keys=active_keys,
                            model_name=model_choice,
                            track_title=track_options[sel_track_id],
                            level_code=sel_level_code,
                            level_name=sel_level_name,
                            custom_topic=custom_topic.strip(),
                        )
                    if new_lesson and not new_lesson.get("error"):
                        add_custom_lesson(sel_track_id, new_lesson, updated_by="AI")
                        st.session_state[f"target_lesson_{sel_track_id}_{sel_level_code}"] = new_lesson.get("id")
                        st.success(f"🎉 Đã tạo thành công bài tập mới: **{new_lesson.get('title')}**!")
                        st.rerun()
                    else:
                        st.error(new_lesson.get("error", "Lỗi khi sinh bài tập."))
    
            # Danh sách các bài đã do AI tạo trong cấp độ này
            ai_lessons = [l for l in lessons if l.get("created_by") == "AI" or "_ai_" in l.get("id", "")]
            if ai_lessons:
                st.markdown(f"#### 📚 Các bài tập do AI mở rộng trong cấp độ này ({len(ai_lessons)} bài)")
                for al in ai_lessons:
                    is_done = al["id"] in user_training
                    icon = "✅" if is_done else "📖"
                    st.markdown(f"- {icon} **{al.get('title')}** (Chế độ: `{al.get('mode')}`) — ID: `{al.get('id')}`")

# ========== TAB 7: Phân rã thực chiến ==========
with tabs[7]:
    st.title("🚀 Phân Rã Thực Chiến & Nhật Ký Quyết Định")
    st.caption("Bóc tách vấn đề qua 9 Lăng kính Tinh hoa & Lưu vết quyết định để tự hiệu chỉnh sai số nhận thức sau 30-90 ngày.")

    tab7_subtabs = st.tabs([
        "🚀 Phân Rã Vấn Đề Tức Thì (AI 9 Lenses)",
        "📓 Elite Decision Journal (Nhật Ký Quyết Định & Đo Sai Số)",
    ])

    with tab7_subtabs[0]:
        st.markdown("""
        Đưa bất kỳ vấn đề, quyết định, tình huống hóc búa hay dự án thực tế vào đây. 
        Hệ thống AI sẽ kích hoạt cùng lúc **9 Lăng kính Tinh hoa & Các Mô hình Hạt nhân** để bóc tách tận cùng First Principles, 
        nhận diện hệ quả bậc hai, lật ngược vấn đề và đề xuất hành động đòn bẩy cao nhất.
        """)

        sample = st.selectbox(
            "💡 Chọn ví dụ mẫu để thử nghiệm:",
            [
                "— Chọn ví dụ —",
                "Đầu tư CKVN: Thị trường giảm mạnh, tin tức xấu bủa vây, có nên bán tháo hay giải ngân tích sản?",
                "Quyết định nghề nghiệp: Nên ở lại công ty ổn định hay khởi nghiệp với rủi ro cao nhưng tiềm năng lớn?",
                "Học sinh Wellspring: Muốn tham gia nhiều CLB nhưng sợ tụt điểm số và áp lực thi cử, giải quyết ra sao?",
                "Thời gian: Cuối tuần nên cày phim xả stress hay dành 3 giờ rèn luyện tư duy và đọc sách?",
            ],
            key="tab7_sample_select",
        )
        initial = "" if sample.startswith("—") else sample

        problem = st.text_area("Nội dung vấn đề cần phân rã:", value=initial, height=120, placeholder="Mô tả cụ thể bối cảnh, mục tiêu, các ràng buộc và điều bạn đang băn khoăn...", key="tab7_problem_input")

        if st.button("🚀 Phân rã ngay", type="primary", use_container_width=True, key="tab7_btn_breakdown"):
            if not active_keys:
                st.warning("Cần Gemini API Key (cấu hình trong Secrets hoặc sidebar).")
            elif not problem.strip():
                st.warning("Hãy nhập nội dung.")
            else:
                with st.spinner("Đang chạy 9 lenses qua Gemini (tự động xoay tua nếu bận/hết quota)..."):
                    result = analyze_problem(active_keys, model_choice, problem.strip())

                if not result:
                    st.error("Không có kết quả.")
                elif result.get("error"):
                    st.error(result["error"])
                    if result.get("raw"):
                        st.code(result["raw"])
                else:
                    summary = result.get("first_principles_breakdown", "")[:300]
                    append_analysis(username, problem.strip(), summary, result)

                    key_info = f" (Key: `{result.get('_used_key')}`)" if result.get("_used_key") else ""
                    st.success(f"Đã phân rã xong{key_info} · Đã lưu vào lịch sử của bạn")

                    st.session_state["dj_pref_title"] = problem.strip()[:60]
                    st.session_state["dj_pref_hypo"] = result.get("first_principles_breakdown", "")[:300]
                    st.session_state["dj_pref_inv"] = result.get("elite_lenses", {}).get("inversion", "")[:200]
                    st.session_state["dj_pref_sec"] = result.get("elite_lenses", {}).get("second_order", "")[:200]
                    st.session_state["open_new_decision_form"] = True

                    st.info("💡 **Gợi ý:** Dữ liệu phân tích đã được nạp sẵn. Hãy bấm sang tab **'📓 Elite Decision Journal'** bên cạnh để lưu quyết định này và đặt lịch kiểm định sau 30/90 ngày!")

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

    with tab7_subtabs[1]:
        st.markdown("### 📓 Elite Decision Journal — Lưu Vết & Hiệu Chuẩn Quyết Định")
        st.caption("Phương pháp của Ray Dalio & Howard Marks: Không thể nâng cao chất lượng tư duy nếu không ghi chép giả định ban đầu và kiểm định lại kết quả thực tế sau 30-90 ngày để triệt tiêu Thiên kiến nhận thức muộn (Hindsight Bias).")

        d_stats = get_decision_summary_stats(username)

        dj_c1, dj_c2, dj_c3, dj_c4 = st.columns(4)
        with dj_c1:
            st.metric("📋 Tổng quyết định", f"{d_stats['total_logged']} mục")
        with dj_c2:
            st.metric("🕒 Đang chờ kiểm định", f"{d_stats['pending_count']} mục")
        with dj_c3:
            due_cnt = d_stats['due_count']
            st.metric("⏳ Đến hạn kiểm định", f"{due_cnt} mục", "Cần xem lại ngay!" if due_cnt > 0 else "Đúng tiến độ")
        with dj_c4:
            acc = d_stats['calibration_accuracy']
            st.metric("🎯 Điểm Hiệu Chuẩn", f"{acc}%" if d_stats['reviewed_count'] > 0 else "Chưa có", f"{d_stats['reviewed_count']} bài đã duyệt")

        st.divider()

        with st.expander("➕ Ghi Nhận Quyết Định Mới Vào Nhật Ký", expanded=(d_stats['total_logged'] == 0 or st.session_state.get("open_new_decision_form", False))):
            with st.form("form_create_decision"):
                pref_title = st.session_state.get("dj_pref_title", "")
                pref_hypo = st.session_state.get("dj_pref_hypo", "")
                pref_inv = st.session_state.get("dj_pref_inv", "")
                pref_sec = st.session_state.get("dj_pref_sec", "")

                dec_title = st.text_input("Tiêu đề quyết định:", value=pref_title, placeholder="Ví dụ: Đầu tư cổ phiếu FPT, Chọn chuyên ngành AI, Rời bỏ công ty X...")
                
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    dec_cat = st.selectbox("Lĩnh vực:", DECISION_CATEGORIES)
                with c_f2:
                    dec_interval_label = st.selectbox("Mốc hẹn kiểm định thực tế:", list(REVIEW_INTERVALS.keys()), index=1)
                    dec_interval_days = REVIEW_INTERVALS[dec_interval_label]

                dec_hypo = st.text_area(
                    "Giả định cốt lõi (Core Hypothesis):",
                    value=pref_hypo,
                    height=80,
                    placeholder="Tại sao bạn đưa ra quyết định này? Bạn tin rằng điều gì sẽ xảy ra và vì sao?",
                )

                dec_conf = st.slider(
                    "Mức độ tự tin / Xác suất Bayes chủ quan của bạn:",
                    min_value=10,
                    max_value=100,
                    value=75,
                    step=5,
                    format="%d%%",
                    help="Theo tư duy Bayes: Đừng bao giờ đặt 100% hay 0%. Hãy thành thật với mức độ không chắc chắn.",
                )

                c_ta1, c_ta2 = st.columns(2)
                with c_ta1:
                    dec_inv = st.text_area(
                        "Bẫy đảo ngược đã lường trước (Inversion):",
                        value=pref_inv,
                        height=80,
                        placeholder="Những điều gì có thể biến quyết định này thành thảm họa? Bạn phòng vệ thế nào?",
                    )
                with c_ta2:
                    dec_sec = st.text_area(
                        "Hệ quả bậc hai dự kiến (Second-Order Effects):",
                        value=pref_sec,
                        height=80,
                        placeholder="Sau khi quyết định này được thực thi, phản ứng tiếp theo của hệ thống sẽ là gì?",
                    )

                btn_save_dec = st.form_submit_button("💾 Lưu Quyết Định Vào Nhật Ký", type="primary", use_container_width=True)

            if btn_save_dec:
                if not dec_title.strip() or not dec_hypo.strip():
                    st.warning("Vui lòng nhập ít nhất Tiêu đề và Giả định cốt lõi của quyết định.")
                else:
                    new_dec = create_decision_entry(
                        username=username,
                        title=dec_title.strip(),
                        category=dec_cat,
                        hypothesis=dec_hypo.strip(),
                        confidence_pct=dec_conf,
                        inversion_traps=dec_inv.strip(),
                        second_order_consequences=dec_sec.strip(),
                        review_days=dec_interval_days,
                    )
                    st.session_state["open_new_decision_form"] = False
                    st.success(f"✅ Đã ghi nhận quyết định '{new_dec['title']}'! Hệ thống sẽ nhắc bạn kiểm định vào ngày {new_dec['review_date']}.")
                    st.rerun()

        st.markdown("#### 📋 Danh Sách Quyết Định Trong Nhật Ký")
        user_decs = d_stats["decisions"]

        if not user_decs:
            st.info("Nhật ký của bạn đang trống. Hãy bấm '➕ Ghi Nhận Quyết Định Mới Vào Nhật Ký' ở trên để bắt đầu lưu vết các quyết định quan trọng!")
        else:
            filter_status = st.radio(
                "Lọc theo trạng thái:",
                ["Tất cả", "⏳ Đến hạn kiểm định (Due)", "🕒 Đang chờ (Pending)", "✅ Đã kiểm định (Reviewed)"],
                horizontal=True,
                key="dj_filter_status",
            )

            status_map = {
                "⏳ Đến hạn kiểm định (Due)": "due",
                "🕒 Đang chờ (Pending)": "pending",
                "✅ Đã kiểm định (Reviewed)": "reviewed",
            }

            for d in user_decs:
                if filter_status != "Tất cả":
                    target_st = status_map[filter_status]
                    if d.get("status") != target_st:
                        continue

                st_icon = "⏳ CẦN KIỂM ĐỊNH" if d.get("status") == "due" else ("🕒 Đang chờ" if d.get("status") == "pending" else "✅ Đã kiểm định")
                expander_title = f"{st_icon} · [{d.get('category', '').split()[0]}] {d.get('title')} (Tạo: {d.get('created_at')} — Hẹn: {d.get('review_date')})"

                with st.expander(expander_title, expanded=(d.get("status") == "due")):
                    c_det1, c_det2 = st.columns(2)
                    with c_det1:
                        st.markdown(f"**📌 Giả định gốc:**  \n{d.get('hypothesis')}")
                        st.markdown(f"**🎯 Độ tự tin ban đầu:** `{d.get('confidence_pct')}%`")
                    with c_det2:
                        if d.get("inversion_traps"):
                            st.markdown(f"**⚠️ Bẫy đảo ngược lường trước:**  \n{d.get('inversion_traps')}")
                        if d.get("second_order_consequences"):
                            st.markdown(f"**🌊 Hệ quả bậc hai dự kiến:**  \n{d.get('second_order_consequences')}")

                    st.markdown("---")

                    if d.get("status") == "reviewed":
                        st.success(f"**Kết quả thực tế ({d.get('reviewed_at')}):**  \n{d.get('actual_outcome')}")
                        sc_c1, sc_c2 = st.columns(2)
                        with sc_c1:
                            st.metric("Đánh giá kết quả", f"{d.get('outcome_score')}%")
                        with sc_c2:
                            diff_val = d.get('calibration_diff', 0)
                            st.metric("Độ lệch nhận thức", f"{diff_val}%", "Khớp hoàn hảo!" if diff_val <= 10 else "Có sai lệch")
                        if d.get("lessons_learned"):
                            st.info(f"💡 **Bài học rút ra:** {d.get('lessons_learned')}")
                    else:
                        st.markdown("##### 🔍 Kiểm Định Thực Tế & Tự Đo Sai Số Nhận Thức")
                        with st.form(key=f"form_review_{d['id']}"):
                            actual_res = st.text_area(
                                "Thực tế diễn ra như thế nào?",
                                height=80,
                                placeholder="Ghi nhận khách quan: Điều gì đã xảy ra so với giả định ban đầu của bạn?",
                            )
                            rate_label = st.selectbox(
                                "Mức độ chính xác so với dự tính ban đầu:",
                                list(OUTCOME_RATINGS.keys()),
                                index=1,
                            )
                            outcome_num = OUTCOME_RATINGS[rate_label]

                            lessons = st.text_area(
                                "Bài học rút ra (Tư duy nào đã giúp ích hoặc mô hình nào bạn đã bỏ sót?):",
                                height=80,
                                placeholder="Ví dụ: Đã quá lạc quan về tiến độ, bỏ quên bẫy chi phí chìm...",
                            )

                            btn_submit_rev = st.form_submit_button("🎯 Hoàn Tất Kiểm Định & Ghi Nhận Sai Số", type="primary", use_container_width=True)

                        if btn_submit_rev:
                            if not actual_res.strip():
                                st.warning("Vui lòng ghi lại kết quả thực tế để hoàn tất kiểm định.")
                            else:
                                resolve_decision_review(
                                    username=username,
                                    decision_id=d["id"],
                                    actual_outcome=actual_res.strip(),
                                    outcome_score=outcome_num,
                                    lessons_learned=lessons.strip(),
                                )
                                st.success("✅ Đã hoàn tất kiểm định quyết định! Điểm hiệu chuẩn của bạn đã được cập nhật.")
                                st.rerun()


# ========== TAB 8: Lịch sử cá nhân ==========
with tabs[8]:
    st.title("📝 Lịch sử của tôi")
    hist = load_user_history(username)

    # Thống kê Bộ 3 Động Lực Tinh Hoa (Elite Trinity)
    st.markdown("#### 🔥 Chỉ Số Rèn Luyện & Hiệu Chuẩn Tinh Hoa")
    trin_c1, trin_c2, trin_c3 = st.columns(3)
    
    # 1. Streak
    u_streak_tab8 = get_user_streak_info(username)
    with trin_c1:
        s_val_t8 = u_streak_tab8["current_streak"]
        s_badge_t8 = "⚡ Khởi động" if s_val_t8 < 7 else ("🔥 Thói quen thép" if s_val_t8 < 30 else "🏆 Phản xạ vô thức")
        st.metric("🔥 Chuỗi Streak 15 Phút", f"{s_val_t8} ngày", f"Kỷ lục: {u_streak_tab8['longest_streak']} ngày ({s_badge_t8})")
    
    # 2. Diagnostic
    latest_diag_t8 = get_latest_diagnostic_result(username)
    with trin_c2:
        if latest_diag_t8:
            st.metric("🧭 Chỉ Số Nhận Thức (Radar)", f"{latest_diag_t8['overall_index']}%", latest_diag_t8['rank_title'].split()[0] + " " + latest_diag_t8['rank_title'].split()[1])
        else:
            st.metric("🧭 Điểm Mù Nhận Thức", "Chưa làm test", "Vào Tab 5 để test")

    # 3. Decision Calibration
    d_stats_t8 = get_decision_summary_stats(username)
    with trin_c3:
        if d_stats_t8["reviewed_count"] > 0:
            st.metric("📓 Điểm Hiệu Chuẩn Quyết Định", f"{d_stats_t8['calibration_accuracy']}%", f"{d_stats_t8['reviewed_count']} quyết định đã duyệt")
        else:
            st.metric("📓 Quyết Định Đang Lưu", f"{d_stats_t8['total_logged']} mục", f"{d_stats_t8['due_count']} đến hạn kiểm định")

    st.divider()

    # Thống kê thành tích Trắc nghiệm & Làm chủ
    m_info = get_user_mastery_summary(username)
    st.markdown("#### 🏆 Thành tích Trắc nghiệm & Làm chủ Mô hình")
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.metric("Độ chính xác Trắc nghiệm", f"{m_info['accuracy']}%", f"{m_info['total_quizzes']} bài test")
    with mc2:
        st.metric("Mô hình đã Mastered", f"{m_info['mastered_count']} / 88", f"{m_info['mastery_pct']}%")
    with mc3:
        st.metric("Đang học / Cần ôn", f"{m_info['learning_count']} học · {m_info['review_count']} ôn")

    recent_tests = m_info.get("recent_tests", [])
    if recent_tests:
        with st.expander(f"📜 Xem {len(recent_tests)} lượt làm bài trắc nghiệm gần nhất"):
            for t in recent_tests[:10]:
                st.markdown(f"- `{t.get('time')}` · **{t.get('category')}**: **{t.get('score')}/{t.get('total')}** đúng ({t.get('percentage')}%)")

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

# ========== TAB 9: Admin (Phat) ==========
if is_admin():
    with tabs[9]:
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

            all_available_tracks = list(tracks_meta.keys())
            g_edit = st.selectbox("Khóa học / Track cần sửa", all_available_tracks, format_func=lambda x: tracks_meta.get(x, {}).get("name", x))
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
            st.markdown("#### Thêm bài mới thủ công")
            with st.form("add_lesson"):
                add_grade = st.selectbox("Thêm vào track", all_available_tracks, format_func=lambda x: tracks_meta.get(x, {}).get("name", x))
                add_id = st.text_input("ID (vd: g6_c1_02, tr_c2_02)")
                add_title = st.text_input("Tiêu đề")
                add_level_choice = st.selectbox("Mức", ["Cơ bản (level_1)", "Thực hành (level_2)", "Nâng cao (level_3)"])
                add_mode = st.text_input("Chế độ tư duy", value="First Principles")
                add_obj = st.text_area("Mục tiêu")
                add_sit = st.text_area("Tình huống")
                add_ex = st.text_area("Bài tập")
                add_hint = st.text_area("Gợi ý")
                if st.form_submit_button("Thêm bài"):
                    if add_id and add_title:
                        l_code = "level_1" if "level_1" in add_level_choice else ("level_2" if "level_2" in add_level_choice else "level_3")
                        l_name = "Cơ bản" if "level_1" in add_level_choice else ("Thực hành" if "level_2" in add_level_choice else "Nâng cao")
                        data.setdefault(add_grade, []).append({
                            "id": add_id,
                            "title": add_title,
                            "level_code": l_code,
                            "level": l_name,
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
            **Kiến trúc nâng cấp (Multi-track & AI Generator)**
            - **Knowledge base**: `data/knowledge_base.json` (dùng chung)
            - **Bài học**: `data/lessons.json` (phân chia theo K12 Wellspring & Chuyên sâu người lớn)
            - **AI Generator**: Tự động sinh thêm bài tập không giới hạn bằng Gemini multi-key
            - **Lịch sử / tiến độ**: `data/histories/<user>.json` (riêng từng người)
            - **Đăng nhập**: `data/users.json`
            - **API Key**: Tích hợp sẵn 3 Key tự động xoay tua khi hết hạn mức
            """)
            st.code("Users: Phat (admin), Ha, xuka, bong, A1, A2\nPassword pattern: <Tên>@12345", language="text")

# Footer
st.divider()
st.caption(f"Elite Thinking Family · Đăng nhập: {display_name} · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
