# -*- coding: utf-8 -*-
"""Munger Latticework: 88 Nuclear Mental Models helper functions."""

from __future__ import annotations

import json
import csv
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import streamlit as st
import pandas as pd
import google.generativeai as genai

from utils.ai_engine import _normalize_keys, _mask_key, _is_quota_or_auth_error, clean_json_response

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODELS_FILE = DATA_DIR / "core_mental_models.json"

TIER_LABELS = {
    "Tất cả": None,
    "⭐ Tier 1: Siêu hạt nhân 80/20 (25 mô hình)": 1,
    "🎯 Tier 2: Chiến lược nâng cao (37 mô hình)": 2,
    "🔬 Tier 3: Chuyên sâu hệ thống (26 mô hình)": 3,
}

PILLAR_ICONS = {
    "Vật lý học": "⚡",
    "Sinh học": "🧬",
    "Tâm lý học": "🧠",
    "Kinh tế học": "📈",
    "Toán học & Xác suất": "🎲",
    "Kỹ thuật & Hệ thống": "⚙️",
}


@st.cache_data(show_spinner=False)
def load_mental_models_data() -> Dict[str, Any]:
    """Tải toàn bộ bộ dữ liệu 88 mô hình hạt nhân với bộ đệm cache."""
    if not MODELS_FILE.exists():
        return {"metadata": {}, "models": []}
    try:
        with open(MODELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"metadata": {}, "models": []}


def get_all_models() -> List[Dict[str, Any]]:
    data = load_mental_models_data()
    return data.get("models", [])


def get_pillars() -> List[str]:
    return [
        "Tất cả",
        "Vật lý học",
        "Sinh học",
        "Tâm lý học",
        "Kinh tế học",
        "Toán học & Xác suất",
        "Kỹ thuật & Hệ thống",
    ]


def filter_models(
    models: List[Dict[str, Any]],
    pillar: Optional[str] = None,
    tier: Optional[int] = None,
    query: str = "",
) -> List[Dict[str, Any]]:
    res = models
    if pillar and pillar != "Tất cả":
        res = [m for m in res if m.get("pillar") == pillar]
    if tier is not None:
        res = [m for m in res if m.get("tier") == tier]
    if query.strip():
        q = query.lower().strip()
        filtered = []
        for m in res:
            searchable = " ".join([
                str(m.get("id", "")),
                str(m.get("name_vi", "")),
                str(m.get("name_en", "")),
                str(m.get("pillar", "")),
                str(m.get("first_principle", "")),
                str(m.get("elite_leverage", "")),
                str(m.get("trigger_question", "")),
                str(m.get("inversion_trap", "")),
            ]).lower()
            if q in searchable:
                filtered.append(m)
        res = filtered
    return res


def models_to_dataframe(models: List[Dict[str, Any]]) -> pd.DataFrame:
    """Chuyển đổi danh sách mô hình sang DataFrame hiển thị đẹp trên Streamlit."""
    rows = []
    for m in models:
        tier_text = {1: "Tier 1 (80/20)", 2: "Tier 2 (Chiến lược)", 3: "Tier 3 (Hệ thống)"}.get(m.get("tier"), f"Tier {m.get('tier')}")
        icon = PILLAR_ICONS.get(m.get("pillar", ""), "📌")
        rows.append({
            "Mã": m.get("id", ""),
            "Tên Mô Hình": f"{m.get('name_vi', '')} ({m.get('name_en', '')})",
            "Trụ Cột": f"{icon} {m.get('pillar', '')}",
            "Cấp Độ Đòn Bẩy": tier_text,
            "Chân Lý Gốc (First Principle)": m.get("first_principle", ""),
            "Đòn Bẩy Elite": m.get("elite_leverage", ""),
            "Bẫy Ngụy Biện (Inversion)": m.get("inversion_trap", ""),
            "Câu Hỏi Kích Hoạt (5s)": m.get("trigger_question", ""),
        })
    return pd.DataFrame(rows)


def export_models_to_csv(models: List[Dict[str, Any]]) -> bytes:
    """Xuất danh sách mô hình ra định dạng bytes CSV kèm UTF-8 BOM (b'\\xef\\xbb\\xbf') để Excel tự động nhận diện và hiển thị tiếng Việt chuẩn 100%."""
    df = models_to_dataframe(models)
    return df.to_csv(index=False).encode("utf-8-sig")


LATTIICEWORK_SYNTHESIS_PROMPT = """Bạn là Charlie Munger AI Master.
Nhiệm vụ của bạn là soi chiếu một vấn đề thực tế thông qua mạng lưới các mô hình tư duy (Latticework of Mental Models), tạo ra hiệu ứng cộng hưởng Lollapalooza đỉnh cao.

Bạn được cung cấp:
- Vấn đề thực tế của người dùng.
- 2 hoặc 3 mô hình hạt nhân được chọn từ các ngành khoa học khác nhau.

YÊU CẦU ĐẦU RA:
BẮT BUỘC trả về định dạng JSON hợp lệ duy nhất, không markdown bao bọc ngoài JSON:
{
  "problem_summary": "Tóm tắt bản chất gốc rễ của vấn đề trong 1-2 câu",
  "models_applied": [
    {
      "model_name": "Tên mô hình",
      "lens_analysis": "Cách mô hình này soi sáng một góc khuất đặc biệt của bài toán",
      "actionable_insight": "Insight hành động cụ thể rút ra từ mô hình này"
    }
  ],
  "lollapalooza_synergy": "Phân tích hiệu ứng cộng hưởng khi các mô hình này kết hợp cùng nhau. Đâu là bước ngoặt x10 sức mạnh đòn bẩy?",
  "inversion_check": "Nếu làm ngược lại hoặc mắc phải bẫy sai lầm của các mô hình này, thảm họa nào chắc chắn xảy ra?",
  "elite_action_plan": [
    "Hành động 1 (Tối ưu đòn bẩy)",
    "Hành động 2 (Phòng ngự biên an toàn)",
    "Hành động 3 (Thực nghiệm nhanh với chi phí thấp nhất)"
  ]
}

Quy tắc:
- Sâu sắc, triệt để theo First Principles, không sáo rỗng.
- Thực chiến cao, chỉ ra rõ chi phí cơ hội và cách tối đa hóa đòn bẩy với nguồn lực tối thiểu.
"""


def analyze_latticework_synthesis(
    api_keys: Union[str, List[str], tuple],
    model_name: str,
    problem_text: str,
    selected_models: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Phân tích cộng hưởng đa ngành Lollapalooza qua Gemini với cơ chế tự động xoay tua key."""
    keys = _normalize_keys(api_keys)
    if not keys or not problem_text.strip() or not selected_models:
        return None

    models_info = "\n".join([
        f"- Mô hình {idx+1}: {m.get('name_vi')} ({m.get('name_en')}) thuộc {m.get('pillar')}\n"
        f"  + Chân lý gốc: {m.get('first_principle')}\n"
        f"  + Đòn bẩy: {m.get('elite_leverage')}\n"
        f"  + Bẫy sai lầm: {m.get('inversion_trap')}"
        for idx, m in enumerate(selected_models)
    ])

    user_prompt = f"""VẤN ĐỀ CẦN GIẢI QUYẾT:
{problem_text.strip()}

CÁC MÔ HÌNH HẠT NHÂN ĐƯỢC CHỌN ĐỂ SOI CHIẾU:
{models_info}

Hãy tổng hợp phân tích đa ngành Lollapalooza sâu sắc theo đúng định dạng JSON yêu cầu."""

    candidates = [model_name]
    for m in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]:
        if m not in candidates:
            candidates.append(m)

    response = None
    last_err = None
    used_key_mask = ""

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
                    system_instruction=LATTIICEWORK_SYNTHESIS_PROMPT,
                    generation_config={"response_mime_type": "application/json"},
                )
                response = model.generate_content(user_prompt)
                if response and response.text:
                    key_success = True
                    used_key_mask = mask
                    break
            except Exception as e:
                err_msg = str(e)
                last_err = f"Key #{idx} ({mask}) lỗi với model '{candidate}': {err_msg}"
                if _is_quota_or_auth_error(err_msg):
                    break

        if key_success:
            break

    if not response or not response.text:
        return {"error": last_err or "Không nhận được phản hồi từ AI Engine."}

    raw = clean_json_response(response.text)
    try:
        data = json.loads(raw)
        data["_used_key"] = used_key_mask
        return data
    except Exception:
        return {"error": "Lỗi định dạng JSON", "raw": response.text, "_used_key": used_key_mask}
