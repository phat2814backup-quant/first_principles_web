# -*- coding: utf-8 -*-
"""
Module Elite Daily Workout (15 Phút Rèn Luyện Hằng Ngày & Chuỗi Streak).
Xây dựng phản xạ nhận thức vô thức thông qua bài toán thực chiến mỗi ngày:
- Quy trình 3 bước: Bóc tách Sự thật vs Ý kiến -> Chiếu lăng kính hạt nhân -> Hành động bất đối xứng
- Quản lý chuỗi ngày rèn luyện liên tục (Streak)
- Chấm điểm và phản hồi từ AI Mentor
"""

from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union

import streamlit as st
import google.generativeai as genai

from utils.knowledge import load_user_history, save_user_history
from utils.ai_engine import (
    _normalize_keys,
    _mask_key,
    _is_quota_or_auth_error,
    clean_json_response,
)

# -----------------------------------------------------------------------------
# 1. NGÂN HÀNG BÀI TẬP WORKOUT MẪU TINH HOA (30 NGÀY THỰC CHIẾN)
# -----------------------------------------------------------------------------
DAILY_WORKOUT_BANK: List[Dict[str, Any]] = [
    {
        "id": "DW-01",
        "day_num": 1,
        "title": "Cơn Sốt Công Nghệ Mới & Tâm Lý Đám Đông (FOMO)",
        "track": "all",
        "scenario": (
            "Một công nghệ mới xuất hiện và giá trị của các công ty liên quan tăng 500% trong 3 tháng. "
            "Mọi diễn đàn, mạng xã hội và bạn bè xung quanh đều bàn tán, khoe lãi và giục bạn: 'Không tham gia ngay là bỏ lỡ cơ hội đổi đời duy nhất trong thập kỷ!'. "
            "Bạn cảm thấy bồn chồn, sợ mình bị tụt hậu nếu đứng ngoài."
        ),
        "guiding_principles": ["Tâm lý bầy đàn", "First Principles", "Mr. Market & Biên an toàn"],
        "step1_prompt": "Bóc tách cội rễ: Đâu là SỰ THẬT khách quan đo lường được, và đâu chỉ là Ý KIẾN/CẢM XÚC/DỰ BÁO?",
        "step2_prompt": "Chiếu lăng kính: Mô hình hạt nhân nào (Tâm lý học, Kinh tế học) đang chi phối hiện tượng này?",
        "step3_prompt": "Hành động bất đối xứng: Nước cờ tối ưu nào giúp bạn vừa không dính rủi ro hủy diệt, vừa tận dụng được cơ hội nếu nó thực sự bùng nổ?",
        "elite_hint": "Phân biệt giữa công nghệ thực sự có giá trị và giá tài sản bị thổi phồng. Chiến lược Quả tạ (Barbell): Đừng all-in, hãy quan sát nút thắt khan hiếm liền kề.",
    },
    {
        "id": "DW-02",
        "day_num": 2,
        "title": "Áp Lực Đồng Trang Lứa & Dự Án Chung Nhóm (School/Workplace)",
        "track": "k12",
        "scenario": (
            "Trong một dự án nghiên cứu của trường/công ty gồm 4 người, bạn là nhóm trưởng. "
            "Có 2 thành viên liên tục trì hoãn, nộp bài sơ sài bằng AI xào nấu và nói: 'Thầy cô/Sếp cũng chỉ đọc lướt thôi, làm kỹ làm gì cho mệt'. "
            "Hạn chót còn 48 giờ. Nếu bạn làm thay hết thì kiệt sức, nếu để nguyên thì cả nhóm bị điểm kém."
        ),
        "guiding_principles": ["Lý thuyết trò chơi", "Động lực (Incentives)", "Chi phí cơ hội"],
        "step1_prompt": "Bóc tách cội rễ: Tách riêng hành vi thực tế của các thành viên khỏi cảm xúc bực bội của bạn.",
        "step2_prompt": "Chiếu lăng kính: Tại sao cơ chế nhóm hiện tại lại khuyến khích họ lười biếng (Bẫy kẻ ăn không - Free-rider Problem)?",
        "step3_prompt": "Hành động đòn bẩy: Thiết kế lại cơ chế bàn giao và trách nhiệm minh bạch ngay lập tức trong 48h tới.",
        "elite_hint": "Không dùng lời khuyên đạo đức; hãy dùng cơ chế minh bạch phần đóng góp (Public attribution) và chia nhỏ đầu ra.",
    },
    {
        "id": "DW-03",
        "day_num": 3,
        "title": "Bẫy Chi Phí Chìm (Sunk Cost) Trong Đầu Tư & Sự Nghiệp",
        "track": "adult",
        "scenario": (
            "Bạn đã dành 2 năm và 300 triệu đồng để theo đuổi một dự án kinh doanh/đầu tư. "
            "Hiện tại, số liệu thực tế cho thấy nhu cầu thị trường đã thay đổi hoàn toàn và mỗi tháng dự án tiếp tục lỗ 15 triệu. "
            "Tuy nhiên, bạn cảm thấy: 'Nếu dừng lại bây giờ thì toàn bộ công sức và tiền bạc 2 năm qua coi như mất trắng!'. Bạn định vay thêm 100 triệu để cố gượng."
        ),
        "guiding_principles": ["Chi phí chìm (Sunk Cost)", "Tư duy Đảo ngược (Inversion)", "Chi phí cơ hội"],
        "step1_prompt": "Bóc tách: Tiền và thời gian 2 năm qua có lấy lại được bằng cách cố thêm không? Hiện tại thực tế có gì?",
        "step2_prompt": "Chiếu lăng kính: Mô hình Chi phí chìm và Bẫy thiên kiến xác nhận đang đánh lừa não bộ của bạn như thế nào?",
        "step3_prompt": "Hành động dứt khoát: Hãy đóng vai một nhà đầu tư mới tiếp quản dự án hôm nay, bạn sẽ quyết định ra sao?",
        "elite_hint": "Quyết định tương lai chỉ phụ thuộc vào chi phí và lợi ích biên từ ngày mai trở đi. Quá khứ đã là sunk cost = 0.",
    },
    {
        "id": "DW-04",
        "day_num": 4,
        "title": "Ra Quyết Định Trong Sương Mù & Cập Nhật Xác Suất Bayes",
        "track": "all",
        "scenario": (
            "Bạn chuẩn bị thi vào một chương trình học bổng / nộp hồ sơ vào một vị trí công việc danh giá với tỷ lệ chọi 1/50 (2%). "
            "Bạn làm một bài thi thử và đạt điểm thuộc top 5%. Bạn bè bảo bạn 'chắc chắn 95% sẽ đỗ'. "
            "Bạn có nên chủ quan ngừng ôn luyện và ăn mừng sớm?"
        ),
        "guiding_principles": ["Xác suất Bayes", "Base Rate Fallacy (Bỏ quên tỷ lệ nền)", "Biên an toàn"],
        "step1_prompt": "Bóc tách: Tỷ lệ chọi chung (Base Rate) là bao nhiêu? Bài thi thử đo lường được mức độ nào so với kỳ thi thật?",
        "step2_prompt": "Chiếu lăng kính: Áp dụng công thức Bayes để nhận diện tại sao 'Top 5% thi thử' không đồng nghĩa với '95% đỗ thật'.",
        "step3_prompt": "Hành động: Chiến lược ôn tập và quản trị tâm lý để tối đa hóa xác suất thực tế.",
        "elite_hint": "Bẫy ảo tưởng xác suất: Khi tỷ lệ nền rất thấp, một tín hiệu tích cực chưa đủ để đảm bảo kết quả.",
    },
    {
        "id": "DW-05",
        "day_num": 5,
        "title": "Bẫy Hậu Quả Bậc Hai Trong Quản Lý Thời Gian & Năng Lượng",
        "track": "all",
        "scenario": (
            "Để hoàn thành khối lượng bài vở và công việc dồn ứ, bạn quyết định uống 3 lon nước tăng lực/cà phê đậm đặc mỗi ngày và chỉ ngủ 4 tiếng suốt 1 tuần. "
            "Kết quả Bậc 1: Bạn nộp bài đúng hạn và cảm thấy mình làm việc siêu năng suất. "
            "Nhưng điều gì đang âm thầm chờ bạn ở Bậc 2 và Bậc 3?"
        ),
        "guiding_principles": ["Tư duy Bậc hai", "Entropy sinh học", "Nợ kỹ thuật & Nợ sức khỏe"],
        "step1_prompt": "Bóc tách: Năng lượng bạn có được tuần này là do bạn tạo ra hay đang 'vay nặng lãi' từ tuần sau?",
        "step2_prompt": "Chiếu lăng kính: Hệ quả Bậc 2 (miễn dịch suy giảm, sương mù não) và Bậc 3 (mất 2 tuần kiệt sức, lỗi sai chí mạng) diễn ra thế nào?",
        "step3_prompt": "Hành động đòn bẩy: Tái thiết kế quy trình làm việc theo chu kỳ nhịp sinh học thay vì dùng chất kích thích cưỡng ép.",
        "elite_hint": "Giới tinh hoa tối ưu hóa năng lượng (Energy Management), không tối ưu hóa thời gian đơn thuần.",
    },
    {
        "id": "DW-06",
        "day_num": 6,
        "title": "Tư Duy Đảo Ngược: Lập Kế Hoạch Bằng Cách Tìm Đường Thất Bại Chắc Chắn",
        "track": "all",
        "scenario": (
            "Bạn chuẩn bị bước vào một kỳ thi quan trọng hoặc ra mắt một dự án kinh doanh mới sau 3 tháng nữa. "
            "Thay vì lập kế hoạch 'Làm sao để thành công rực rỡ', bạn được Charlie Munger thách thức: "
            "'Hãy chỉ ra 5 cách chắc chắn nhất sẽ biến kỳ thi/dự án này thành thảm họa bẽ bàng!'."
        ),
        "guiding_principles": ["Tư duy Đảo ngược (Inversion)", "Quản trị rủi ro chủ động", "Tính phản dễ vỡ"],
        "step1_prompt": "Bóc tách: Liệt kê 3-5 hành vi hoặc sai lầm cụ thể đảm bảo 100% bạn sẽ thất bại thảm hại.",
        "step2_prompt": "Chiếu lăng kính: Tại sao con người rất dở trong việc tìm ra điều vĩ đại, nhưng lại rất giỏi nhận biết điều ngu ngốc?",
        "step3_prompt": "Hành động: Xây dựng danh sách 'Checklist những việc TUYỆT ĐỐI KHÔNG LÀM' trong 3 tháng tới.",
        "elite_hint": "'Invert, always invert' — Tránh được mọi hành vi ngu ngốc sẽ tự động đưa bạn vào top 5% xuất sắc.",
    },
    {
        "id": "DW-07",
        "day_num": 7,
        "title": "Đòn Bẩy Không Cần Xin Phép (Permissionless) vs Bán Sức Lao Động",
        "track": "all",
        "scenario": (
            "Bạn có kỹ năng giỏi trong một lĩnh vực (Toán học, Lập trình, Ngoại ngữ hoặc Thiết kế). "
            "Cách truyền thống: Bạn đi làm gia sư hoặc làm thuê part-time với giá 150.000đ/giờ. Bạn chỉ có thể kiếm thêm tiền bằng cách cày thêm giờ. "
            "Làm thế nào để chuyển đổi kỹ năng này sang dạng Đòn bẩy không cần xin phép (Permissionless Leverage)?"
        ),
        "guiding_principles": ["Đòn bẩy Code & Media", "Chi phí biên = 0", "Cá nhân tự trị (Sovereign Individual)"],
        "step1_prompt": "Bóc tách: Bạn đang bán cái gì? Thời gian sinh học của bạn có giới hạn trần là bao nhiêu?",
        "step2_prompt": "Chiếu lăng kính: Sự khác biệt cốt lõi giữa đòn bẩy Lao động (cần người khác thuê) vs đòn bẩy Code/Media/AI (chạy 24/7).",
        "step3_prompt": "Hành động: Một dự án mẫu nhỏ bạn có thể xây dựng trong 2 tuần để phục vụ 1.000 người mà không cần có mặt bạn.",
        "elite_hint": "Đóng gói kiến thức thành sản phẩm số, tài liệu mở, video hướng dẫn hoặc công cụ AI tự động hóa.",
    },
]


# -----------------------------------------------------------------------------
# 2. LOGIC LẤY BÀI TẬP WORKOUT THEO NGÀY
# -----------------------------------------------------------------------------
def get_today_workout(track: str = "all", day_offset: int = 0) -> Dict[str, Any]:
    """Lấy bài tập hôm nay dựa trên ngày trong năm và bộ lọc đối tượng."""
    candidates = DAILY_WORKOUT_BANK
    if track != "all":
        filtered = [w for w in candidates if w.get("track") in [track, "all"]]
        if filtered:
            candidates = filtered

    day_of_year = datetime.now().timetuple().tm_yday + day_offset
    idx = day_of_year % len(candidates)
    return candidates[idx]


# -----------------------------------------------------------------------------
# 3. QUẢN LÝ CHUỖI STREAK & LỊCH SỬ NGƯỜI DÙNG
# -----------------------------------------------------------------------------
def get_user_streak_info(username: str) -> Dict[str, Any]:
    """Lấy thông tin chuỗi rèn luyện liên tục (Streak) của người dùng."""
    hist = load_user_history(username)
    dw_data = hist.setdefault("daily_workouts", {
        "current_streak": 0,
        "longest_streak": 0,
        "last_workout_date": None,
        "total_completed": 0,
        "history": []
    })

    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    last_date = dw_data.get("last_workout_date")

    is_done_today = (last_date == today_str)

    # Nếu ngày cuối làm bài trước hôm qua và chưa làm hôm nay -> chuỗi bị đứt (reset về 0)
    current_streak = dw_data.get("current_streak", 0)
    if last_date and last_date != today_str and last_date != yesterday_str:
        current_streak = 0
        dw_data["current_streak"] = 0
        save_user_history(username, hist)

    return {
        "current_streak": current_streak,
        "longest_streak": dw_data.get("longest_streak", current_streak),
        "is_done_today": is_done_today,
        "total_completed": dw_data.get("total_completed", 0),
        "last_workout_date": last_date,
        "history": dw_data.get("history", []),
    }


def record_daily_workout_answer(
    username: str,
    workout_id: str,
    workout_title: str,
    step1_ans: str,
    step2_ans: str,
    step3_ans: str,
    ai_feedback: str = "",
) -> Dict[str, Any]:
    """Ghi nhận bài làm 15 phút hôm nay và cập nhật chuỗi Streak."""
    hist = load_user_history(username)
    dw_data = hist.setdefault("daily_workouts", {
        "current_streak": 0,
        "longest_streak": 0,
        "last_workout_date": None,
        "total_completed": 0,
        "history": []
    })

    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    last_date = dw_data.get("last_workout_date")

    if last_date == today_str:
        # Đã hoàn thành hôm nay, chỉ cập nhật bài mới nhất
        pass
    elif last_date == yesterday_str:
        # Nối tiếp chuỗi từ hôm qua
        dw_data["current_streak"] = dw_data.get("current_streak", 0) + 1
        dw_data["total_completed"] = dw_data.get("total_completed", 0) + 1
    else:
        # Chuỗi mới bắt đầu
        dw_data["current_streak"] = 1
        dw_data["total_completed"] = dw_data.get("total_completed", 0) + 1

    if dw_data["current_streak"] > dw_data.get("longest_streak", 0):
        dw_data["longest_streak"] = dw_data["current_streak"]

    dw_data["last_workout_date"] = today_str

    entry = {
        "workout_id": workout_id,
        "title": workout_title,
        "date": today_str,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "step1": step1_ans,
        "step2": step2_ans,
        "step3": step3_ans,
        "ai_feedback": ai_feedback,
    }

    history_list = dw_data.setdefault("history", [])
    history_list.insert(0, entry)
    dw_data["history"] = history_list[:50]  # Giữ 50 bài gần nhất

    save_user_history(username, hist)
    return dw_data


# -----------------------------------------------------------------------------
# 4. AI MENTOR PHẢN HỒI BÀI TẬP WORKOUT
# -----------------------------------------------------------------------------
DAILY_WORKOUT_FEEDBACK_PROMPT = """Bạn là Elite Thinking Mentor (Gia sư Tư duy Tinh hoa).
Học viên vừa hoàn thành bài tập rèn luyện tư duy 15 phút theo quy trình 3 bước:
1. Bóc tách Sự thật vs Ý kiến
2. Chiếu lăng kính mô hình hạt nhân
3. Đề xuất hành động đòn bẩy bất đối xứng

Nhiệm vụ: Hãy đưa ra nhận xét sắc bén, sâu sắc, ngắn gọn (4-6 câu) bằng tiếng Việt.
Cấu trúc phản hồi:
- 🌟 Điểm sắc sảo nhất trong câu trả lời của học viên.
- 🔍 Một góc nhìn sâu hơn hoặc điểm mù họ còn bỏ sót (gợi ý thêm mô hình liên quan).
- ⚡ Lời khuyên hành động thực tế tiếp theo.
Văn phong: Đĩnh đạc, thông tuệ, khích lệ nhưng khắt khe chuẩn mực tinh hoa.
"""

def evaluate_daily_workout(
    api_keys: Union[str, List[str], tuple],
    model_name: str,
    workout: Dict[str, Any],
    step1_ans: str,
    step2_ans: str,
    step3_ans: str,
) -> str:
    """Gọi AI Mentor để phản biện bài tập 15 phút."""
    keys = _normalize_keys(api_keys)
    if not keys:
        return "Chưa có API key để sinh phản hồi AI. Hãy đối chiếu với Gợi ý tinh hoa của bài tập."

    prompt = f"""Tình huống: {workout.get('title')}
Bối cảnh: {workout.get('scenario')}
Nguyên lý định hướng: {', '.join(workout.get('guiding_principles', []))}

BÀI LÀM CỦA HỌC VIÊN:
Bước 1 (Sự thật vs Ý kiến):
{step1_ans}

Bước 2 (Chiếu lăng kính mô hình):
{step2_ans}

Bước 3 (Hành động bất đối xứng):
{step3_ans}
"""

    candidates = [model_name, "gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
    last_err = None

    for idx, current_key in enumerate(keys, 1):
        mask = _mask_key(current_key)
        try:
            genai.configure(api_key=current_key)
        except Exception as e:
            last_err = f"Lỗi cấu hình Key #{idx}: {e}"
            continue

        for candidate in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=candidate,
                    system_instruction=DAILY_WORKOUT_FEEDBACK_PROMPT,
                )
                resp = model.generate_content(prompt)
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                err_msg = str(e)
                last_err = f"Key #{idx} ({mask}) lỗi: {err_msg}"
                if _is_quota_or_auth_error(err_msg):
                    break
                continue

    return f"Không thể tạo phản hồi từ AI. Lỗi: {last_err}"
