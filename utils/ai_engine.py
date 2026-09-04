# -*- coding: utf-8 -*-
"""Gemini analysis engine (simplified for Cloud + family use)."""

from __future__ import annotations

import json
import re
from typing import Dict, Any, Optional

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


def analyze_problem(api_key: str, model_name: str, problem_text: str) -> Optional[Dict[str, Any]]:
    if not api_key or not problem_text.strip():
        return None

    genai.configure(api_key=api_key)
    candidates = [model_name]
    for m in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]:
        if m not in candidates:
            candidates.append(m)

    response = None
    last_err = None
    for candidate in candidates:
        try:
            model = genai.GenerativeModel(
                model_name=candidate,
                system_instruction=SYSTEM_PROMPT,
                generation_config={"response_mime_type": "application/json"},
            )
            response = model.generate_content(problem_text)
            if response and response.text:
                break
        except Exception as e:
            last_err = e
            continue

    if response is None or not response.text:
        return {"error": str(last_err) if last_err else "Không nhận được phản hồi từ API"}

    try:
        cleaned = clean_json_response(response.text)
        return json.loads(cleaned)
    except Exception as e:
        return {"error": f"Lỗi parse JSON: {e}", "raw": response.text[:500]}


def feedback_on_answer(api_key: str, model_name: str, lesson: Dict[str, Any], student_answer: str) -> str:
    if not api_key:
        return "Chưa có API key nên không tạo được feedback AI. Hãy tự đối chiếu với gợi ý trong bài."

    genai.configure(api_key=api_key)
    prompt = f"""Bài học: {lesson.get('title')}
Mục tiêu: {lesson.get('objective')}
Tình huống: {lesson.get('situation')}
Câu hỏi bài tập: {lesson.get('exercise_prompt')}
Gợi ý: {lesson.get('hint')}

Câu trả lời của học sinh:
{student_answer}
"""
    try:
        model = genai.GenerativeModel(
            model_name=model_name or "gemini-2.5-flash",
            system_instruction=TRAINING_FEEDBACK_PROMPT,
        )
        resp = model.generate_content(prompt)
        return resp.text.strip() if resp and resp.text else "Không tạo được feedback."
    except Exception as e:
        return f"Lỗi khi tạo feedback: {e}"
