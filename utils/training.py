# -*- coding: utf-8 -*-
"""Curriculum & lesson management with multi-track and multi-level support."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LESSONS_FILE = DATA_DIR / "lessons.json"

DEFAULT_TRACKS_META = {
    "grade_6": {
      "name": "Lớp 6 (Wellspring)",
      "category": "k12",
      "desc": "Khởi đầu cấp 2: Tách biệt sự thật, thói quen học tập, tư duy khoa học và làm quen với AI"
    },
    "grade_9": {
      "name": "Lớp 9 (Wellspring)",
      "category": "k12",
      "desc": "Chuyển cấp & Định hướng: Tư duy phản biện, base rate xác suất, đòn bẩy 80/20 và chọn hướng đi"
    },
    "grade_10": {
      "name": "Lớp 10 (Wellspring)",
      "category": "k12",
      "desc": "Cấp 3 Chiến lược: Quản trị dự án, tư duy trò chơi, optionality nghề nghiệp và đòn bẩy AI"
    },
    "trading": {
      "name": "Trading Vàng, FX, Crypto/BTC",
      "category": "adult",
      "desc": "Tư duy xác suất, quản trị rủi ro bất đối xứng, kiểm soát tâm lý FOMO và kỳ vọng toán học"
    },
    "ckvn": {
      "name": "Đầu tư Chứng khoán Việt Nam",
      "category": "adult",
      "desc": "First Principles trong chu kỳ kinh tế, VSA dòng tiền Smart Money và định giá thực chất"
    },
    "neuroscience": {
      "name": "Khoa học Não bộ & Nhận thức",
      "category": "adult",
      "desc": "Cơ chế Dopamine, Hệ thống 1 & 2 (Kahneman), Neuroplasticity và khắc phục thiên kiến nhận thức"
    },
    "buddhism": {
      "name": "Phật giáo & Tâm thức Ra quyết định",
      "category": "adult",
      "desc": "Vô thường, Nhân - Duyên - Quả, Chánh niệm tĩnh lặng tâm trí để ra quyết định khách quan"
    },
    "ai_tech": {
      "name": "Công nghệ AI & Tương lai",
      "category": "adult",
      "desc": "First Principles về AI, Agentic Workflows, tư duy đòn bẩy công nghệ và năng lực cạnh tranh mới"
    }
}


def load_lessons() -> Dict[str, Any]:
    if not LESSONS_FILE.exists():
        return {"version": "2.0", "tracks_meta": DEFAULT_TRACKS_META}
    try:
        with open(LESSONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "2.0", "tracks_meta": DEFAULT_TRACKS_META}


def save_lessons(data: Dict[str, Any], updated_by: str = "admin") -> None:
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["updated_by"] = updated_by
    with open(LESSONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_tracks_meta() -> Dict[str, Any]:
    data = load_lessons()
    return data.get("tracks_meta", DEFAULT_TRACKS_META)


def get_all_tracks() -> List[str]:
    meta = get_tracks_meta()
    return list(meta.keys())


def get_lessons_by_track(track: str, level_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách bài học theo track và cấp độ (tùy chọn)."""
    data = load_lessons()
    lessons = data.get(track, [])
    if level_code and level_code != "all":
        return [l for l in lessons if l.get("level_code") == level_code]
    return lessons


def get_lessons_by_grade(grade: str) -> List[Dict[str, Any]]:
    """Tương thích ngược với các phiên bản cũ."""
    if grade in ("6", "grade_6"):
        return get_lessons_by_track("grade_6")
    if grade in ("9", "grade_9"):
        return get_lessons_by_track("grade_9")
    if grade in ("10", "grade_10"):
        return get_lessons_by_track("grade_10")
    return get_lessons_by_track(grade)


def get_lesson(lesson_id: str) -> Optional[Dict[str, Any]]:
    data = load_lessons()
    for key, val in data.items():
        if isinstance(val, list):
            for lesson in val:
                if isinstance(lesson, dict) and lesson.get("id") == lesson_id:
                    return lesson
    return None


def add_custom_lesson(track: str, lesson_dict: Dict[str, Any], updated_by: str = "AI") -> bool:
    """Thêm một bài học mới (ví dụ do AI sinh ra) vào kho lưu trữ."""
    data = load_lessons()
    track_lessons = data.setdefault(track, [])
    # Đảm bảo có ID duy nhất
    if not lesson_dict.get("id"):
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        lesson_dict["id"] = f"{track[:3]}_ai_{timestamp}"
    lesson_dict["track"] = track
    lesson_dict["created_by"] = updated_by
    track_lessons.append(lesson_dict)
    save_lessons(data, updated_by=updated_by)
    return True


def update_lesson(lesson_id: str, new_content: Dict[str, Any], updated_by: str) -> bool:
    data = load_lessons()
    for key, val in data.items():
        if isinstance(val, list):
            for i, lesson in enumerate(val):
                if isinstance(lesson, dict) and lesson.get("id") == lesson_id:
                    data[key][i] = {**lesson, **new_content, "id": lesson_id}
                    save_lessons(data, updated_by=updated_by)
                    return True
    return False
