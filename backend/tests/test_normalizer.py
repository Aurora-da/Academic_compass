from __future__ import annotations

from app.services.ingestion.normalizer import (
    guess_status,
    normalize_row,
    normalize_status,
    normalize_term,
)


def test_negative_status_is_not_matched_as_passed():
    assert normalize_status("未通过") == "failed"
    assert normalize_status("未合格") == "failed"
    assert normalize_status("不合格") == "failed"
    assert normalize_status("不及格") == "failed"
    assert normalize_status("通过") == "passed"
    assert normalize_status("合格") == "passed"


def test_studying_status_is_trusted_even_with_score():
    assert guess_status(95, "在修") == "studying"
    assert guess_status(95, "修读中") == "studying"
    assert guess_status(95, "studying") == "studying"
    assert guess_status(95, "") == "passed"
    assert guess_status(95, "withdrawn") == "withdrawn"
    assert normalize_row({"name": "退课课程", "status": "not_started"})["raw_status"] == "withdrawn"


def test_course_code_accepts_six_to_eight_digits():
    assert normalize_row({"name": "编译原理", "code": "B034913"})["raw_code"] == "B034913"
    assert normalize_row({"name": "大学英语", "code": "B1113101"})["raw_code"] == "B1113101"
    assert normalize_row({"name": "无代码课程", "code": "not-a-code"})["raw_code"] == ""


def test_term_and_credit_normalization():
    assert normalize_term("2025-2026学年第二学期") == "2025-2026-2"
    assert normalize_term("2024-2025-1") == "2024-2025-1"
    row = normalize_row({"name": "编译原理", "credit": "3.0", "status": "未通过", "score": "55"})
    assert row["raw_credit"] == 3.0
    assert row["raw_status"] == "failed"
