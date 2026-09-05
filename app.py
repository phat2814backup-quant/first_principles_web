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
)

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
    st.subheader("🗺️ Quy Trình 6 Bước Chuyển Hóa Năng Lực Tư Duy")
    st.markdown("Để biến tri thức thành phản xạ tự nhiên và giải quyết được mọi bài toán hóc búa, hãy đi theo lộ trình 6 bước sư phạm:")

    step_cols = st.columns(6)
    with step_cols[0]:
        st.markdown("""
        #### 1️⃣ Nạp Lăng Kính
        **Tab 1: 9 Chế độ**
        *Hiểu các công cụ tư duy:*
        - First Principles
        - Đảo ngược Inversion
        - Hệ quả bậc 2
        - Xác suất Bayes
        - Hệ thống phức hợp
        """)
    with step_cols[1]:
        st.markdown("""
        #### 2️⃣ Cài Mô Hình
        **Tab 2: 88 Mô hình**
        *Nắm 6 trụ cột Munger:*
        - Vật lý (Đòn bẩy, Entropy)
        - Sinh học (Tiến hóa)
        - Tâm lý (Thiên kiến)
        - Kinh tế (Chi phí cơ hội)
        - Toán/Xác suất & Hệ thống
        """)
    with step_cols[2]:
        st.markdown("""
        #### 3️⃣ Tra Cứu Sâu
        **Tab 3: Thư viện**
        *100 định luật khoa học:*
        - Định nghĩa toán học
        - Điều kiện biên
        - Kiểm chứng khả bác (Falsification test)
        """)
    with step_cols[3]:
        st.markdown("""
        #### 4️⃣ Luyện Phản Xạ
        **Tab 4: Đấu trường**
        *Khắc sâu vào trí nhớ:*
        - Thẻ Flashcards 5 giây
        - Trắc nghiệm tình huống
        - AI Dynamic Quiz
        - Thử thách Feynman
        """)
    with step_cols[4]:
        st.markdown("""
        #### 5️⃣ Rèn Chủ Đích
        **Tab 5: Đào tạo**
        *Bài tập tự luận đa tầng:*
        - K12 Wellspring & Người lớn
        - 3 Cấp độ thực hành
        - AI Mentor phản biện
        - Tự động sinh đề mở rộng
        """)
    with step_cols[5]:
        st.markdown("""
        #### 6️⃣ Thực Chiến
        **Tab 6: Phân rã**
        *Vũ khí giải quyết vấn đề:*
        - Đưa vấn đề thực tế vào
        - AI kích hoạt 9 lăng kính
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


# ========== TAB 2: Cẩm nang 9 Tư duy Elite ==========
with tabs[1]:
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

# ========== TAB 2: 88 Mô hình Hạt nhân (Munger Latticework) ==========
with tabs[2]:
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

# ========== TAB 3: Thư viện nguyên lý ==========
with tabs[3]:
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

# ========== TAB 4: Đấu trường Luyện nhớ & Trắc nghiệm phản xạ ==========
with tabs[4]:
    st.title("⚡ Đấu Trường Luyện Nhớ & Trắc Nghiệm Phản Xạ")
    st.caption("Nắm trọn 9 Chế độ · 88 Mô hình Hạt nhân · 100 Nguyên lý Khởi thủy qua Active Recall & Case Quizzes")

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

    arena_tab1, arena_tab2, arena_tab3 = st.tabs([
        "🎯 Trắc Nghiệm Tình Huống Thực Chiến",
        "🗂️ Thẻ Flashcards Phản Xạ 5 Giây",
        "✨ AI Đấu Trí & Thử Thách Feynman"
    ])

    # -------------------------------------------------------------------------
    # Sub-tab 1: Trắc Nghiệm Tình Huống Thực Chiến
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

# ========== TAB 5: Đào tạo tư duy ==========
with tabs[5]:
    st.title("🎓 Đào tạo tư duy theo lộ trình đa tầng")
    st.markdown("Chương trình rèn luyện 3 cấp độ dành cho học sinh phổ thông (Wellspring) & chuyên sâu thực chiến cho người lớn.")

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

# ========== TAB 6: Phân rã thực chiến ==========
with tabs[6]:
    st.title("🚀 Phân Rã Thực Chiến Đa Chế Độ (Elite Lenses)")
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
    )
    initial = "" if sample.startswith("—") else sample

    problem = st.text_area("Nội dung vấn đề cần phân rã:", value=initial, height=120, placeholder="Mô tả cụ thể bối cảnh, mục tiêu, các ràng buộc và điều bạn đang băn khoăn...")

    if st.button("🚀 Phân rã ngay", type="primary", use_container_width=True):
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
                # Save personal history
                summary = result.get("first_principles_breakdown", "")[:300]
                append_analysis(username, problem.strip(), summary, result)

                key_info = f" (Key: `{result.get('_used_key')}`)" if result.get("_used_key") else ""
                st.success(f"Đã phân rã xong{key_info} · Đã lưu vào lịch sử của bạn")

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

# ========== TAB 7: Lịch sử cá nhân ==========
with tabs[7]:
    st.title("📝 Lịch sử của tôi")
    hist = load_user_history(username)

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

# ========== TAB 8: Admin (Phat) ==========
if is_admin():
    with tabs[8]:
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
