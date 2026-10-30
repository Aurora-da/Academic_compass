from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.planner.feasibility import assess_feasibility
from app.services.planner.filter import Candidate, build_candidates, expand_slots
from app.services.planner.solver import solve_plans


@pytest.fixture(scope="module")
def offerings():
    data = json.loads((Path(__file__).resolve().parents[1] / "data/seeds/offerings.json").read_text(encoding="utf-8"))
    return data["offerings"]


@pytest.fixture
def report(make_report):
    return make_report()


def test_expand_slots():
    assert expand_slots(["周三 3-4"]) == {"周三-3", "周三-4"}
    assert expand_slots(["周一 9-10", "周五 1-2"]) == {"周一-9", "周一-10", "周五-1", "周五-2"}
    assert expand_slots(["集中实践"]) == set()


def test_feasibility_three_scenarios(plan, report, offerings):
    result = assess_feasibility(
        plan, report, offerings, entry_year=2023, current_term="2025-2026-2", max_credits=28
    )
    scenarios = {s["years"]: s for s in result["scenarios"]}
    assert scenarios[3]["credits_feasible"] is False
    assert scenarios[4]["credits_feasible"] is True
    assert scenarios[5]["credits_feasible"] is True
    assert scenarios[3]["per_term"] == 45.0
    assert scenarios[4]["per_term"] == 15.0
    assert scenarios[5]["per_term"] == 9.0
    assert result["earliest_feasible_years"] == 4


def test_feasibility_three_year_has_blocked_courses(plan, report, offerings):
    result = assess_feasibility(plan, report, offerings, entry_year=2023, current_term="2025-2026-2")
    scenario = next(s for s in result["scenarios"] if s["years"] == 3)
    names = {c["name"] for c in scenario["blocked_courses"]}
    assert "毕业设计（论文）" in names or "综合实习" in names


def test_feasibility_non_credit_blockers(plan, report, offerings):
    result = assess_feasibility(plan, report, offerings, entry_year=2023, current_term="2025-2026-2")
    assert any("学科竞赛" in b for b in result["non_credit_blockers"])
    assert "三条件" in result["summary"]


def test_candidates_offerings_are_hard_constraint(plan, report, offerings, plan_spec):
    candidates, blocked = build_candidates(
        plan,
        report,
        offerings,
        plan_spec.prerequisites,
        current_term="2025-2026-2",
        grade=2023,
        direction="M5-1",
    )
    codes = {c.code for c in candidates}
    assert "B034910" in codes
    assert "B034913" in codes
    assert "B037022" not in codes  # 本学期不开课
    by_code = {c.code: c for c in candidates}
    # 编译原理 01 班与软件工程综合设计冲突，应自动选择 02 班
    assert by_code["B034913"].slots == ["周五 1-2"]
    assert by_code["B034913"].status == "available"


def test_candidates_required_child_flag(plan, report, offerings, plan_spec):
    candidates, _ = build_candidates(
        plan,
        report,
        offerings,
        plan_spec.prerequisites,
        current_term="2025-2026-2",
        grade=2023,
        direction="M5-1",
    )
    mobile = next(c for c in candidates if c.code == "B036034")
    assert mobile.required_child is True
    assert mobile.module == "M6-1"


def test_candidates_exclude_other_direction(plan, report, offerings, plan_spec):
    candidates, blocked = build_candidates(
        plan,
        report,
        offerings,
        plan_spec.prerequisites,
        current_term="2025-2026-2",
        grade=2023,
        direction="M5-1",
    )
    assert not any(c.module in {"M5-2", "M5-3"} for c in candidates)
    assert any(c.status == "other_direction" for c in blocked)


def _candidate(code, credit, slot, score, nature="必修", module="M4", status="available"):
    return Candidate(
        code=code,
        name=code,
        credit=credit,
        nature=nature,
        category="专业课",
        module=module,
        module_name=module,
        assessment="考试",
        plan_term="3-2",
        required_child=False,
        offering={"class_id": "01"},
        status=status,
        slots=slot,
        score=score,
    )


def test_solver_respects_total_budget():
    candidates = [
        _candidate("A", 3.0, ["周一 1-2"], 80),
        _candidate("B", 4.0, ["周一 3-4"], 70),
        _candidate("C", 5.0, ["周二 1-2"], 60),
        _candidate("D", 10.0, ["周三 1-2"], 50),
    ]
    plans = solve_plans(candidates, current_credits=4.0)
    assert [p.key for p in plans] == ["steady", "balanced", "sprint"]
    for package in plans:
        assert package.total_with_locked <= package.budget + 1e-9


def test_solver_avoids_time_conflicts():
    candidates = [
        _candidate("A", 3.0, ["周一 1-2"], 90),
        _candidate("B", 3.0, ["周一 1-2"], 80),
        _candidate("C", 3.0, ["周二 1-2"], 70),
    ]
    package = solve_plans(candidates, current_credits=0)[0]
    assert "A" in {c.code for c in package.courses}
    assert "B" not in {c.code for c in package.courses}
    assert "C" in {c.code for c in package.courses}


def test_solver_excludes_conflict_status():
    candidates = [
        _candidate("A", 3.0, ["周一 1-2"], 90, status="conflict"),
        _candidate("B", 3.0, ["周二 1-2"], 80),
    ]
    package = solve_plans(candidates, current_credits=0)[2]
    assert {c.code for c in package.courses} == {"B"}


def test_solver_respects_locked_slots():
    candidates = [_candidate("A", 3.0, ["周一 1-2"], 90)]
    plans = solve_plans(
        candidates,
        locked_courses=[{"code": "L", "name": "已选", "credit": 2, "slots": ["周一 1-2"]}],
        current_credits=2,
    )
    assert all(not p.courses for p in plans)
