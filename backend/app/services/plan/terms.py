from __future__ import annotations

import re
from datetime import date

TERM_RE = re.compile(r"^(\d)-(\d)$")
ACADEMIC_RE = re.compile(r"^(\d{4})-(\d{4})-([12])$")


def term_index(term: str) -> int:
    """把 1-1 … 4-2 转成 0..7 的序号。非法值抛 ValueError。"""
    m = TERM_RE.match(term.strip())
    if not m:
        raise ValueError(f"非法指导性学期：{term!r}（应为 1-1 … 4-2）")
    year, half = int(m.group(1)), int(m.group(2))
    if not (1 <= year <= 6 and half in (1, 2)):
        raise ValueError(f"指导性学期超出范围：{term!r}")
    return (year - 1) * 2 + (half - 1)


def term_label(term: str) -> str:
    names = ["大一秋", "大一春", "大二秋", "大二春", "大三秋", "大三春", "大四秋", "大四春"]
    try:
        idx = term_index(term)
        return f"{term}（{names[idx]}）" if idx < len(names) else term
    except ValueError:
        return term


def academic_to_index(academic_term: str, entry_year: int) -> int:
    """2025-2026-2 + 2023 级 → 5（3-2）。"""
    m = ACADEMIC_RE.match(academic_term.strip())
    if not m:
        raise ValueError(f"非法学年学期：{academic_term!r}")
    start_year, half = int(m.group(1)), int(m.group(3))
    return (start_year - entry_year) * 2 + (half - 1)


def index_to_academic(idx: int, entry_year: int) -> str:
    start = entry_year + idx // 2
    half = idx % 2 + 1
    return f"{start}-{start + 1}-{half}"


def index_to_term(idx: int) -> str:
    return f"{idx // 2 + 1}-{idx % 2 + 1}"


def current_index(student_entry_year: int, current_term: str) -> int:
    return academic_to_index(current_term, student_entry_year)


def academic_year_of(academic_term: str) -> str:
    m = ACADEMIC_RE.match(academic_term.strip())
    if not m:
        return ""
    return f"{m.group(1)}-{m.group(2)}"


def completed_academic_years(entry_year: int, current_term: str) -> list[str]:
    """已经结束的学年（不含当前学年），用于每学年 ≥N 次的周期检查。"""
    current_ay = academic_year_of(current_term)
    years: list[str] = []
    for y in range(entry_year, entry_year + 8):
        ay = f"{y}-{y + 1}"
        if current_ay and ay >= current_ay:
            break
        years.append(ay)
    return years


def remaining_terms(current_term: str, target_term: str, entry_year: int, include_current: bool = True) -> list[int]:
    start = academic_to_index(current_term, entry_year)
    end = academic_to_index(target_term, entry_year)
    if end < start:
        return []
    return list(range(start if include_current else start + 1, end + 1))


def graduation_term(entry_year: int, years: int) -> str:
    """3/4/5 年制对应的毕业学期（最后一学期）。"""
    return f"{entry_year + years - 1}-{entry_year + years}-2"


def semester_key(academic_term: str) -> tuple[int, int]:
    m = ACADEMIC_RE.match(academic_term.strip())
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(3)))


def today_str() -> str:
    return date.today().isoformat()
