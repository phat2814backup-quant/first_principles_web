# -*- coding: utf-8 -*-
"""Gemini analysis engine (simplified for Cloud + family use) with multi-key failover."""

from __future__ import annotations

import json
import re
from typing import Dict, Any, Optional, List, Union

import google.generativeai as genai

SYSTEM_PROMPT = """Bạn là Elite Multi-Mode Thinking Engine (phiên bản gia đình / giáo dục).

Nhiệm vụ: Phân rã vấn đề bằng First Principles + các chế độ tư duy elite.
Trả lời BẮT BUỘC bằng JSON hợp lệ, không markdown, không giải thích ngoài JSON.

Cấu trúc JSON:
{
  "is_valid": true/false,
  "core_principles_found": [{"name": "...", "domain": "...", "description": "..."}],
  "first_principles_breakdown": "phân rã ngắn gọn",
  "elite_lenses": {
    "inversion": "...",
    "second_order": "...",
    "bayesian": "...",
    "leverage": "...",
    "multi_timescale": "Ngắn hạn / Trung hạn / Dài hạn"
  },
  "actionable_insights": ["insight 1", "insight 2"],
  "human_decision_needed": ["câu hỏi cần người dùng quyết định"]
}

Quy tắc:
- Ép định nghĩa mục tiêu mơ hồ.
- Bayesian phải có base rate thô nếu liên quan xác suất.
- Ưu tiên đòn bẩy cao và ràng buộc thật.
- Ngôn ngữ rõ ràng, có thể hành động được.
- Nếu vấn đề không thuộc quy luật khách quan, is_valid = false và giải thích ngắn trong first_principles_breakdown.
"""

TRAINING_FEEDBACK_PROMPT = """Bạn là gia sư tư duy elite cho học sinh.
Học sinh vừa trả lời bài tập rèn tư duy. Hãy đưa feedback ngắn (3-6 câu), khích lệ, chỉ ra điểm tốt và 1 điểm cần cải thiện.
Không chấm điểm số. Không dài dòng. Trả lời bằng tiếng Việt, văn phong thân thiện với học sinh cấp 2.
"""


def clean_json_response(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _normalize_keys(api_keys: Union[str, List[str], tuple]) -> List[str]:
    """Chuẩn hóa danh sách API keys từ chuỗi hoặc mảng."""
    if isinstance(api_keys, str):
        raw = [k.strip() for k in api_keys.split(",") if k.strip()]
    elif isinstance(api_keys, (list, tuple)):
        raw = [str(k).strip() for k in api_keys if str(k).strip()]
    else:
        raw = []

    seen = set()
    unique = []
    for k in raw:
        if k and k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def _mask_key(key: str) -> str:
    """Ẩn bớt ký tự API key để hiển thị an toàn."""
    if not key or len(key) < 8:
        return "***"
    return f"...{key[-6:]}"


def _is_quota_or_auth_error(err_str: str) -> bool:
    """Kiểm tra xem lỗi có phải do hết hạn mức (quota/rate limit) hoặc lỗi key hay không."""
    lower = err_str.lower()
    quota_signals = [
        "429",
        "resourceexhausted",
        "resource_exhausted",
        "quota",
        "rate limit",
        "rate_limit",
        "exhausted",
        "capacity",
        "api key not valid",
        "permission_denied",
        "unauthenticated",
    ]
    return any(sig in lower for sig in quota_signals)


def analyze_problem(
    api_keys: Union[str, List[str], tuple],
    model_name: str,
    problem_text: str,
) -> Optional[Dict[str, Any]]:
    """Phân rã vấn đề với cơ chế tự động xoay tua API keys khi gặp lỗi hết hạn mức (Quota/Rate Limit)."""
    keys = _normalize_keys(api_keys)
    if not keys or not problem_text.strip():
        return None

    candidates = [model_name]
    for m in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]:
        if m not in candidates:
            candidates.append(m)

    response = None
    last_err = None
    used_key_mask = ""

    # Duyệt qua từng API Key để tự động fallback khi hết hạn mức
    for idx, current_key in enumerate(keys, 1):
        mask = _mask_key(current_key)
        try:
            genai.configure(api_key=current_key)
        except Exception as e:
            last_err = f"Lỗi cấu hình Key #{idx} ({mask}): {e}"
            continue

        key_success = False
        for candidate in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=candidate,
                    system_instruction=SYSTEM_PROMPT,
                    generation_config={"response_mime_type": "application/json"},
                )
                response = model.generate_content(problem_text)
                if response and response.text:
                    key_success = True
                    used_key_mask = mask
                    break
            except Exception as e:
                err_msg = str(e)
                last_err = f"Key #{idx} ({mask}) model [{candidate}] lỗi: {err_msg}"
                # Nếu hết hạn mức quota hoặc lỗi xác thực key, chuyển ngay sang Key tiếp theo
                if _is_quota_or_auth_error(err_msg):
                    break
                continue

        if key_success:
            break

    if response is None or not response.text:
        return {"error": f"Tất cả {len(keys)} API Key đều không khả dụng hoặc hết hạn mức. Lỗi gần nhất: {last_err}"}

    try:
        cleaned = clean_json_response(response.text)
        data = json.loads(cleaned)
        if isinstance(data, dict):
            data["_used_key"] = used_key_mask
        return data
    except Exception as e:
        return {"error": f"Lỗi parse JSON: {e}", "raw": response.text[:500]}


def feedback_on_answer(
    api_keys: Union[str, List[str], tuple],
    model_name: str,
    lesson: Dict[str, Any],
    student_answer: str,
) -> str:
    """Tạo nhận xét cho học sinh với cơ chế tự động xoay tua API keys khi gặp lỗi hết hạn mức."""
    keys = _normalize_keys(api_keys)
    if not keys:
        return "Chưa có API key nên không tạo được feedback AI. Hãy tự đối chiếu với gợi ý trong bài."

    prompt = f"""Bài học: {lesson.get('title')}
Mục tiêu: {lesson.get('objective')}
Tình huống: {lesson.get('situation')}
Câu hỏi bài tập: {lesson.get('exercise_prompt')}
Gợi ý: {lesson.get('hint')}

Câu trả lời của học sinh:
{student_answer}
"""
    candidates = [model_name or "gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
    last_err = None

    for idx, current_key in enumerate(keys, 1):
        mask = _mask_key(current_key)
        try:
            genai.configure(api_key=current_key)
        except Exception as e:
            last_err = f"Lỗi cấu hình Key #{idx} ({mask}): {e}"
            continue

        key_success = False
        for candidate in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=candidate,
                    system_instruction=TRAINING_FEEDBACK_PROMPT,
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

    return f"Lỗi khi tạo feedback (đã thử {len(keys)} key): {last_err}"


DYNAMIC_LESSON_PROMPT = """Bạn là Chuyên gia Thiết kế Chương trình Đào tạo Tư duy Đỉnh cao (Elite Thinking Mentor).

Nhiệm vụ: Dựa trên phân hệ đối tượng và Cấp độ yêu cầu, hãy tạo ra 01 bài tập tình huống rèn luyện tư duy thực chiến mới tinh, độc đáo, lôi cuốn và mang tính giáo dục sâu sắc.

BẮT BUỘC trả lời bằng JSON hợp lệ, không bọc code block markdown ngoài JSON.

Cấu trúc JSON yêu cầu:
{
  "title": "Tiêu đề bài học ngắn gọn, hấp dẫn",
  "mode": "Chế độ tư duy (chọn 1 trong 9: First Principles, Bayesian, Inversion, Second-order thinking, Optionality, Mental Models, Empirical, Game theory, Multi-timescale)",
  "objective": "Mục tiêu bài học (1-2 câu)",
  "situation": "Tình huống thực tế cụ thể, chi tiết, gần gũi với đối tượng",
  "guide_steps": [
    "Bước 1: Hướng dẫn phân tích...",
    "Bước 2: Hướng dẫn áp dụng nguyên lý...",
    "Bước 3: Hướng dẫn hành động hoặc quyết định..."
  ],
  "exercise_prompt": "Câu hỏi thử thách dành cho người học",
  "hint": "Gợi ý định hướng giải bài",
  "related_principle": "Tên nguyên lý tư duy cốt lõi liên quan"
}

Quy tắc:
1. Đối với học sinh Wellspring (Lớp 6, 9, 10): Tình huống gắn liền với trường học song ngữ, dự án STEM, thuyết trình, câu lạc bộ, bạn bè, quản lý thời gian, rèn thói quen và làm chủ công nghệ/AI tương lai.
2. Đối với người lớn (Trading Vàng/FX/Crypto, Đầu tư CKVN, Khoa học não bộ, Triết lý Phật giáo, Công nghệ AI): Tình huống thực chiến sắc bén, quản trị rủi ro, tâm lý học, chu kỳ, hoặc đòn bẩy tự động hóa.
3. Cấp độ:
   - Cơ bản (Level 1): Nhận diện khái niệm cốt lõi, bóc tách sự thật vs ý kiến, tránh sai lầm cơ bản.
   - Thực hành (Level 2): Xử lý tình huống đánh đổi (trade-offs), quản lý biến số, tính toán xác suất hoặc giải quyết xung đột.
   - Nâng cao (Level 3): Tích hợp đa mô hình (Latticework), bất đối xứng (Optionality), đa quy mô thời gian và sáng tạo đòn bẩy.
"""


def generate_dynamic_lesson(
    api_keys: Union[str, List[str], tuple],
    model_name: str,
    track_title: str,
    level_code: str,
    level_name: str,
    custom_topic: str = "",
    user_context: str = "",
) -> Optional[Dict[str, Any]]:
    """Tự động sinh bài tập tư duy mới bằng AI dựa trên đối tượng, cấp độ và lịch sử người dùng."""
    keys = _normalize_keys(api_keys)
    if not keys:
        return {"error": "Chưa có API key để sinh bài tập AI."}

    user_request_prompt = f"""Hãy tạo 01 bài tập tư duy mới cho:
- Phân hệ / Khối lớp: {track_title}
- Cấp độ rèn luyện: {level_name} ({level_code})
- Chủ đề ưu tiên (nếu có): {custom_topic if custom_topic else 'Tự động chọn chủ đề xuất sắc nhất'}
- Ngữ cảnh học viên / Điểm cần rèn thêm: {user_context if user_context else 'Học viên muốn rèn luyện tư duy thực chiến'}
"""
    candidates = [model_name or "gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
    last_err = None

    for idx, current_key in enumerate(keys, 1):
        mask = _mask_key(current_key)
        try:
            genai.configure(api_key=current_key)
        except Exception as e:
            last_err = f"Lỗi cấu hình Key #{idx} ({mask}): {e}"
            continue

        for candidate in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=candidate,
                    system_instruction=DYNAMIC_LESSON_PROMPT,
                    generation_config={"response_mime_type": "application/json"},
                )
                resp = model.generate_content(user_request_prompt)
                if resp and resp.text:
                    cleaned = clean_json_response(resp.text)
                    data = json.loads(cleaned)
                    if isinstance(data, dict):
                        data["level_code"] = level_code
                        data["level"] = level_name
                        data["_generated_by"] = f"Gemini ({candidate}) [Key {mask}]"
                        return data
            except Exception as e:
                err_msg = str(e)
                last_err = f"Key #{idx} ({mask}) lỗi [{candidate}]: {err_msg}"
                if _is_quota_or_auth_error(err_msg):
                    break
                continue

    return {"error": f"Không thể tự động sinh bài tập (đã thử {len(keys)} key). Lỗi: {last_err}"}

