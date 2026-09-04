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
    "🚀 Phân rã vấn đề",
    "📖 Cẩm nang 9 Tư duy Elite",
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

# ========== TAB 3: Thư viện ==========
with tabs[2]:
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

# ========== TAB 4: Đào tạo tư duy ==========
with tabs[3]:
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

    # ---------- AI Generator Expander ----------
    with st.expander("✨ AI Mentor: Tự động tạo thêm bài tập mới (Tạo 30-50+ bài không giới hạn)", expanded=False):
        st.markdown(f"**Sinh bài tập mới bằng AI cho:** `{track_options[sel_track_id]}` · Mức `{sel_level_name}`")
        custom_topic = st.text_input(
            "Gợi ý chủ đề / tình huống bạn muốn rèn luyện thêm (tùy chọn):",
            placeholder="vd: Bài tập nhóm STEM lớp 10, quản lý lệnh Vàng phiên Mỹ, giữ tĩnh lặng khi đối tác thất hứa...",
            key=f"topic_input_{sel_track_id}_{sel_level_code}",
        )
        if st.button("🚀 Bấm để AI tạo bài tập mới ngay", key=f"btn_gen_{sel_track_id}_{sel_level_code}", type="primary"):
            if not active_keys:
                st.warning("Cần API Key để sinh bài tập.")
            else:
                with st.spinner("AI Mentor đang thiết kế bài tập tình huống thực chiến độc bản..."):
                    new_lesson = generate_dynamic_lesson(
                        api_keys=active_keys,
                        model_name=model_choice,
                        track_title=track_options[sel_track_id],
                        level_code=sel_level_code,
                        level_name=sel_level_name,
                        custom_topic=custom_topic.strip(),
                    )
                if new_lesson and not new_lesson.get("error"):
                    add_custom_lesson(sel_track_id, new_lesson, updated_by=username)
                    st.success(f"🎉 Đã tạo thành công bài tập: **{new_lesson.get('title')}**!")
                    st.rerun()
                else:
                    st.error(new_lesson.get("error", "Lỗi khi sinh bài tập."))

    if not lessons:
        st.info("Chưa có bài tập nào trong cấp độ này. Hãy mở khung 'AI Mentor' ở trên và bấm tạo bài tập mới!")
    else:
        lesson_titles = [f"{l['id']} — {l['title']} ({l.get('mode', '')})" for l in lessons]
        choice = st.selectbox(
            f"Chọn bài tập ({len(lessons)} bài khả dụng trong cấp độ này)",
            lesson_titles,
            key=f"sel_lesson_{sel_track_id}_{sel_level_code}",
        )
        idx = lesson_titles.index(choice)
        lesson = lessons[idx]

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
        hist = load_user_history(username)
        prev = hist.get("training", {}).get(lesson["id"], {})
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

        # Progress overview
        st.divider()
        st.markdown(f"#### Tiến độ rèn luyện cấp độ này ({sel_level_name})")
        done = 0
        for l in lessons:
            done_flag = l["id"] in hist.get("training", {})
            icon = "✅" if done_flag else "⬜"
            st.markdown(f"{icon} {l['title']}")
            if done_flag:
                done += 1
        st.progress(done / max(len(lessons), 1))
        st.caption(f"Đã hoàn thành {done}/{len(lessons)} bài trong cấp độ này")

# ========== TAB 5: Lịch sử cá nhân ==========
with tabs[4]:
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

# ========== TAB 6: Admin (Phat) ==========
if is_admin():
    with tabs[5]:
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
