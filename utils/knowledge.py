# -*- coding: utf-8 -*-
"""Shared knowledge base (JSON) + per-user history helpers."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KB_FILE = DATA_DIR / "knowledge_base.json"
HISTORIES_DIR = DATA_DIR / "histories"
HISTORIES_DIR.mkdir(parents=True, exist_ok=True)


def load_knowledge_base() -> Dict[str, Any]:
    if not KB_FILE.exists():
        return {"metadata": {}, "principles": []}
    with open(KB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_principles(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    kb = load_knowledge_base()
    principles = kb.get("principles", [])
    if domain and domain != "Tất cả":
        principles = [p for p in principles if p.get("domain") == domain]
    return principles


def get_domains() -> List[str]:
    principles = get_principles()
    domains = sorted({p.get("domain", "Khác") for p in principles})
    return ["Tất cả"] + domains


def search_principles(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    if not query.strip():
        return []
    q = query.lower().strip()
    results = []
    for p in get_principles():
        text = " ".join([
            str(p.get("principle_name", "")),
            str(p.get("domain", "")),
            str(p.get("description", "")),
            str(p.get("intuitive_summary", "")),
            str(p.get("formal_definition", "")),
        ]).lower()
        if q in text:
            results.append(p)
        if len(results) >= limit:
            break
    return results


# ---------- Per-user history (file + session) ----------

def _history_path(username: str) -> Path:
    safe = "".join(c for c in username if c.isalnum() or c in ("_", "-"))
    return HISTORIES_DIR / f"{safe}.json"


def load_user_history(username: str) -> Dict[str, Any]:
    path = _history_path(username)
    if not path.exists():
        return {
            "username": username,
            "analyses": [],
            "training": {},
            "updated_at": None,
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "username": username,
            "analyses": [],
            "training": {},
            "updated_at": None,
        }


def save_user_history(username: str, data: Dict[str, Any]) -> None:
    path = _history_path(username)
    data["username"] = username
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_analysis(username: str, problem: str, result_summary: str, full_result: Optional[Dict] = None) -> None:
    hist = load_user_history(username)
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "problem": problem[:500],
        "summary": result_summary[:1000],
    }
    if full_result:
        entry["is_valid"] = full_result.get("is_valid")
    hist.setdefault("analyses", []).insert(0, entry)
    # keep last 50
    hist["analyses"] = hist["analyses"][:50]
    save_user_history(username, hist)


def save_training_answer(username: str, lesson_id: str, answer: str, feedback: str = "") -> None:
    hist = load_user_history(username)
    hist.setdefault("training", {})[lesson_id] = {
        "answer": answer,
        "feedback": feedback,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_user_history(username, hist)


def list_all_user_histories() -> List[Dict[str, Any]]:
    """Admin only: load all history files."""
    results = []
    if not HISTORIES_DIR.exists():
        return results
    for path in sorted(HISTORIES_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                results.append(json.load(f))
        except Exception:
            continue
    return results
