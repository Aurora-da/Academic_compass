from __future__ import annotations

import pytest

from app.services.audit.second_classroom import check_second_classroom


@pytest.fixture(scope="module")
def reqs(plan):
    return plan.second_classroom


def test_sample_second_classroom_status(reqs, records):
    result = check_second_classroom(reqs, records, 2023, "2025-2026-2")
    assert result["ok"] is False
    assert result["status"] == "unmet"
    categories = {(i["category"], i["period_label"]): i for i in result["items"]}
    assert categories[("主题社会实践", "2023-2024 学年")]["status"] == "met"
    assert categories[("学科竞赛与项目", "累计")]["status"] == "unmet"
    assert categories[("学术交流研讨", "2025-2026-2 学期")]["done"] == 1


def test_current_academic_year_not_judged(reqs, records):
    result = check_second_classroom(reqs, records, 2023, "2025-2026-2")
    years = [i["period_label"] for i in result["items"] if i["period_type"] == "year"]
    assert "2025-2026 学年" not in years
    assert len([y for y in years if "学年" in y]) == 4  # 2 categories × 2 completed years


def test_data_missing_is_tri_state(reqs):
    result = check_second_classroom(reqs, [], 2023, "2025-2026-2")
    assert result["ok"] is None
    assert result["status"] == "missing"
    assert all(i["ok"] is None for i in result["items"])


def test_pending_records_not_counted(reqs):
    records = [
        {"category": "学科竞赛与项目", "term": "2025-2026-2", "status": "pending", "title": "x"}
    ]
    result = check_second_classroom(reqs, records, 2023, "2025-2026-2")
    competition = next(i for i in result["items"] if i["category"] == "学科竞赛与项目")
    assert competition["done"] == 0
    assert competition["status"] == "unmet"


def test_all_met(reqs):
    records = []
    for year in ("2023-2024", "2024-2025"):
        records.append({"category": "主题社会实践", "term": f"{year}-2", "status": "approved", "title": "x"})
        records.append({"category": "创新实践", "term": f"{year}-2", "status": "approved", "title": "x"})
    records.append({"category": "学科竞赛与项目", "term": "2025-2026-1", "status": "approved", "title": "x"})
    records.append({"category": "学术交流研讨", "term": "2025-2026-2", "status": "approved", "title": "x"})
    records.append({"category": "学术交流研讨", "term": "2025-2026-2", "status": "approved", "title": "y"})
    result = check_second_classroom(reqs, records, 2023, "2025-2026-2")
    assert result["ok"] is True
    assert result["status"] == "met"
    assert result["unmet_count"] == 0


def test_term_requirement_boundary(reqs):
    records = [
        {"category": "学术交流研讨", "term": "2025-2026-2", "status": "approved", "title": "x"},
        {"category": "学术交流研讨", "term": "2025-2026-2", "status": "approved", "title": "y"},
    ]
    result = check_second_classroom(reqs, records, 2023, "2025-2026-2")
    item = next(i for i in result["items"] if i["category"] == "学术交流研讨")
    assert item["done"] == 2
    assert item["ok"] is True
