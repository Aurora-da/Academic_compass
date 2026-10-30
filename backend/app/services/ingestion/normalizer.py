from __future__ import annotations

import re
from typing import Any

TERM_PATTERNS = [
    re.compile(r"(\d{4})\s*[-–—/]\s*(\d{4})\s*[-–—/]\s*([12])"),
    re.compile(r"(\d{4})\s*[-–—/]\s*(\d{4})\s*学年\s*第?\s*([一二1]|[二2])\s*学期"),
    re.compile(r"(\d{4})\s*[-–—/]\s*(\d{4})\s*([12])"),
]

STATUS_MAP = {
    # 否定/退课语义必须先判断，否则「未通过」会被「通过」抢先匹配
    "未通过": "failed",
    "未合格": "failed",
    "未及格": "failed",
    "不及格": "failed",
    "不合格": "failed",
    "挂科": "failed",
    "退课": "withdrawn",
    "退选": "withdrawn",
    "withdrawn": "withdrawn",
    "not_started": "not_started",
    "未修": "not_started",
    "在修": "studying",
    "修读中": "studying",
    "在读": "studying",
    "studying": "studying",
    "通过": "passed",
    "合格": "passed",
    "已通过": "passed",
    "pass": "passed",
    "fail": "failed",
}


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(m.group(0)) if m else None


def normalize_term(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    for pattern in TERM_PATTERNS:
        m = pattern.search(text)
        if m:
            half = m.group(3)
            half = {"一": "1", "二": "2"}.get(half, half)
            if half not in {"1", "2"}:
                continue
            return f"{m.group(1)}-{m.group(2)}-{half}"
    return fallback


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    for key, status in STATUS_MAP.items():
        if key in text:
            return status
    return "passed" if not text else "studying"


def guess_status(score: float | None, raw_status: Any = None) -> str:
    if raw_status:
        status = normalize_status(raw_status)
        text = str(raw_status)
        if status != "studying" or any(
            k in text.lower() for k in ("在修", "修读中", "在读", "studying")
        ):
            return status
    if score is None:
        return "studying"
    return "passed" if score >= 60 else "failed"


def normalize_row(raw: dict, fallback_term: str = "") -> dict:
    name = str(raw.get("name") or raw.get("course_name") or "").strip()
    code = str(raw.get("code") or raw.get("course_code") or "").strip().upper()
    credit = parse_float(raw.get("credit"))
    score = parse_float(raw.get("score"))
    term = normalize_term(raw.get("term"), fallback_term)
    status = raw.get("status")
    status = guess_status(score, status) if not status else normalize_status(status)
    if status == "not_started":
        status = "withdrawn"
    return {
        "raw_name": name,
        "raw_code": code if re.fullmatch(r"[A-Z]{1,2}\d{5,8}", code) else "",
        "raw_credit": credit,
        "raw_term": term,
        "raw_status": status,
        "raw_score": score,
        "evidence": raw.get("evidence") or {},
    }
