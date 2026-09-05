# -*- coding: utf-8 -*-
"""
Module Elite Decision Journal (Nhật Ký Quyết Định & Tự Hiệu Chỉnh Sai Số).
Phương pháp của Ray Dalio, Howard Marks và Daniel Kahneman:
- Ghi nhận quyết định hôm nay: Giả định gốc, Tỷ lệ Bayes, Bẫy đảo ngược, Hệ quả bậc hai
- Đặt lịch tự động kiểm định sau 30, 90, 180 ngày
- Đo lường độ lệch nhận thức (Calibration Score) và diệt trừ Thiên kiến nhận thức muộn (Hindsight Bias)
"""

from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional

from utils.knowledge import load_user_history, save_user_history

DECISION_CATEGORIES = [
    "📈 Tài chính, Chứng khoán & Đầu tư",
    "💼 Sự nghiệp, Dự án & Kinh doanh",
    "🎒 Học tập, Học bổng & Chọn ngành",
    "🌱 Sức khỏe, Thói quen & Đời sống",
    "🤝 Mối quan hệ & Đàm phán",
]

REVIEW_INTERVALS = {
    "30 ngày (Ngắn hạn / Dự án nhanh)": 30,
    "90 ngày (Trung hạn / 1 Quý)": 90,
    "180 ngày (Dài hạn / Nửa năm)": 180,
    "365 ngày (Chiến lược 1 năm)": 365,
}

OUTCOME_RATINGS = {
    "🏆 Thành công vượt kỳ vọng (100%)": 100,
    "✅ Đúng như dự tính ban đầu (80%)": 80,
    "⚖️ Đúng một phần, có sai số (50%)": 50,
    "❌ Hoàn toàn sai lệch so với dự tính (0%)": 0,
}


def create_decision_entry(
    username: str,
    title: str,
    category: str,
    hypothesis: str,
    confidence_pct: int,
    inversion_traps: str,
    second_order_consequences: str,
    review_days: int = 90,
    source_analysis: str = "",
) -> Dict[str, Any]:
    """Tạo một bản ghi quyết định mới vào nhật ký của người dùng."""
    hist = load_user_history(username)
    journal = hist.setdefault("decision_journal", [])

    created_dt = date.today()
    review_dt = created_dt + timedelta(days=review_days)

    entry_id = f"DEC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    entry: Dict[str, Any] = {
        "id": entry_id,
        "title": title.strip(),
        "category": category,
        "created_at": created_dt.isoformat(),
        "review_date": review_dt.isoformat(),
        "review_days": review_days,
        "hypothesis": hypothesis.strip(),
        "confidence_pct": confidence_pct,
        "inversion_traps": inversion_traps.strip(),
        "second_order_consequences": second_order_consequences.strip(),
        "source_analysis": source_analysis[:500] if source_analysis else "",
        "status": "pending",  # 'pending', 'due', 'reviewed'
        "reviewed_at": None,
        "actual_outcome": "",
        "outcome_score": None,
        "calibration_diff": None,
        "lessons_learned": "",
    }

    journal.insert(0, entry)
    save_user_history(username, hist)
    return entry


def get_user_decisions(username: str) -> List[Dict[str, Any]]:
    """Lấy danh sách quyết định của người dùng, tự động cập nhật trạng thái 'due' nếu đã tới ngày hẹn."""
    hist = load_user_history(username)
    journal = hist.get("decision_journal", [])
    today_str = date.today().isoformat()

    has_changes = False
    for item in journal:
        if item.get("status") == "pending":
            rev_date = item.get("review_date", "")
            if rev_date and rev_date <= today_str:
                item["status"] = "due"
                has_changes = True

    if has_changes:
        save_user_history(username, hist)

    return journal


def resolve_decision_review(
    username: str,
    decision_id: str,
    actual_outcome: str,
    outcome_score: int,
    lessons_learned: str,
) -> Optional[Dict[str, Any]]:
    """Cập nhật kết quả thực tế cho một quyết định đã đến hạn kiểm định."""
    hist = load_user_history(username)
    journal = hist.setdefault("decision_journal", [])

    target = None
    for item in journal:
        if item.get("id") == decision_id:
            target = item
            break

    if not target:
        return None

    target["status"] = "reviewed"
    target["reviewed_at"] = date.today().isoformat()
    target["actual_outcome"] = actual_outcome.strip()
    target["outcome_score"] = outcome_score
    target["lessons_learned"] = lessons_learned.strip()

    # Đo lường độ lệch nhận thức: |Độ tự tin ban đầu - Điểm kết quả thực tế|
    conf = target.get("confidence_pct", 50)
    target["calibration_diff"] = abs(conf - outcome_score)

    save_user_history(username, hist)
    return target


def get_decision_summary_stats(username: str) -> Dict[str, Any]:
    """Thống kê tổng quan chỉ số hiệu chuẩn quyết định."""
    decisions = get_user_decisions(username)
    total = len(decisions)
    pending = sum(1 for d in decisions if d.get("status") == "pending")
    due = sum(1 for d in decisions if d.get("status") == "due")
    reviewed = [d for d in decisions if d.get("status") == "reviewed"]
    reviewed_count = len(reviewed)

    # Tính điểm hiệu chuẩn nhận thức (Calibration Accuracy: 100 - avg_diff)
    if reviewed:
        diffs = [d.get("calibration_diff", 0) for d in reviewed if d.get("calibration_diff") is not None]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        calibration_accuracy = max(0.0, round(100.0 - avg_diff, 1))
    else:
        calibration_accuracy = 0.0

    return {
        "total_logged": total,
        "pending_count": pending,
        "due_count": due,
        "reviewed_count": reviewed_count,
        "calibration_accuracy": calibration_accuracy,
        "decisions": decisions,
    }
