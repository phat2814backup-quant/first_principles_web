# -*- coding: utf-8 -*-
"""Curriculum & lesson management."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LESSONS_FILE = DATA_DIR / "lessons.json"


def load_lessons() -> Dict[str, Any]:
    if not LESSONS_FILE.exists():
        return {"version": "0", "grade_6": [], "grade_9": []}
    with open(LESSONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_lessons(data: Dict[str, Any], updated_by: str = "admin") -> None:
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["updated_by"] = updated_by
    with open(LESSONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_lessons_by_grade(grade: str) -> List[Dict[str, Any]]:
    data = load_lessons()
    if grade == "6":
        return data.get("grade_6", [])
    if grade == "9":
        return data.get("grade_9", [])
    return []


def get_lesson(lesson_id: str) -> Optional[Dict[str, Any]]:
    data = load_lessons()
    for g in ("grade_6", "grade_9"):
        for lesson in data.get(g, []):
            if lesson.get("id") == lesson_id:
                return lesson
    return None


def update_lesson(lesson_id: str, new_content: Dict[str, Any], updated_by: str) -> bool:
    data = load_lessons()
    for g in ("grade_6", "grade_9"):
        for i, lesson in enumerate(data.get(g, [])):
            if lesson.get("id") == lesson_id:
                data[g][i] = {**lesson, **new_content, "id": lesson_id}
                save_lessons(data, updated_by=updated_by)
                return True
    return False
