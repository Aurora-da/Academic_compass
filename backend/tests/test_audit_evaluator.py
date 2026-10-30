from __future__ import annotations

import pytest

from app.services.audit.evaluator import build_enrollment_state


@pytest.fixture
def report(make_report):
    return make_report()


def test_plan_total_is_169(plan):
    assert plan.total_credits == 169.0
    assert round(sum(root.require for root in plan.roots), 2) == 169.0
    assert len(plan.roots) == 7


def test_summary_matches_real_transcript(report):
    assert report.summary["require"] == 169.0
    assert report.summary["earned"] == 124.0
    assert report.summary["gap"] == 45.0
    assert report.summary["studying"] == 4.0
    assert report.summary["over"] == 1.0
    assert report.summary["percent"] == 73.37


@pytest.mark.parametrize(
    "key,require,earned,gap,over,ok",
    [
        ("M1", 38.0, 35.0, 3.0, 0.0, False),
        ("M2", 10.0, 11.0, 0.0, 1.0, True),
        ("M3", 44.5, 44.5, 0.0, 0.0, True),
        ("M4", 22.5, 10.5, 12.0, 0.0, False),
        ("M5", 6.0, 2.0, 4.0, 0.0, False),
        ("M6", 17.0, 15.0, 2.0, 0.0, False),
        ("M7", 31.0, 7.0, 24.0, 0.0, False),
    ],
)
def test_module_numbers(report, key, require, earned, gap, over, ok):
    module = next(m for m in report.modules if m.key == key)
    assert module.require == require
    assert module.earned == earned
    assert module.gap == gap
    assert module.over == over
    assert module.ok is ok


@pytest.mark.parametrize(
    "key,total,passed",
    [("M1", 25, 21), ("M2", 11, 8), ("M3", 12, 12), ("M4", 8, 4), ("M5", 3, 1), ("M6", 27, 8), ("M7", 10, 6)],
)
def test_module_course_counts(report, key, total, passed):
    module = next(m for m in report.modules if m.key == key)
    assert module.courses_total == total
    assert module.courses_passed == passed


def test_earned_is_capped_per_module(report):
    module_sum = round(sum(m.earned for m in report.modules), 2)
    assert module_sum == 125.0
    assert report.summary["earned"] == 124.0
    assert module_sum - report.summary["earned"] == report.summary["over"] == 1.0


def test_studying_is_not_counted_as_earned(report):
    m7 = next(m for m in report.modules if m.key == "M7")
    assert m7.earned == 7.0
    assert m7.studying == 2.0
    assert m7.gap == 24.0
    assert [c["name"] for c in m7.studying_courses] == ["软件工程综合设计"]


def test_structure_gap_is_reported_for_free_module(report):
    m6 = next(m for m in report.modules if m.key == "M6")
    module1 = next(c for c in m6.children if c.key == "M6-1")
    assert m6.mode == "free"
    assert m6.earned == 15.0 and m6.gap == 3.0 - 1.0  # gap = 17 - 15
    assert module1.earned == 9.0 and module1.gap == 3.0
    assert m6.own_ok is False and m6.child_ok is False and m6.ok is False
    risk = next(r for r in report.risks if r["type"] in {"structure_priority", "structure_gap"})
    assert "模块1" in risk["msg"]


def test_any_of_picks_best_direction(report):
    m5 = next(m for m in report.modules if m.key == "M5")
    assert m5.picked == "M5-1"
    assert m5.picked_name == "人工智能"
    assert m5.earned == 2.0
    assert report.direction["options"][0]["id"] == "M5-1"


def test_any_of_locked_direction_changes_earned(make_report):
    report = make_report(direction="M5-2")
    m5 = next(m for m in report.modules if m.key == "M5")
    assert m5.picked == "M5-2"
    assert m5.earned == 0.0
    assert m5.gap == 6.0
    assert report.direction["locked"] is True


def test_any_of_counts_only_picked_group(make_report, enrollments):
    extra = list(enrollments) + [
        {"course_code": "B035016", "course_name": "FPGA设计", "term": "2025-2026-1", "status": "passed", "score": 90, "credit": 2.0}
    ]
    report = make_report(enrollments_override=extra, direction="M5-1")
    m5 = next(m for m in report.modules if m.key == "M5")
    assert m5.earned == 2.0  # 另一方向不计入
    assert m5.children[1].earned == 2.0  # 但仍然展示


def test_direction_unlocked_risk(make_report):
    report = make_report(direction=None)
    assert report.direction["locked"] is False
    assert any(r["type"] == "direction_undecided" for r in report.risks)


def test_all_of_gap_after_removing_course(make_report, enrollments):
    filtered = [e for e in enrollments if e["course_code"] != "B881209"]
    report = make_report(enrollments_override=filtered)
    m1 = next(m for m in report.modules if m.key == "M1")
    assert m1.earned == 32.0
    assert m1.gap == 6.0
    assert m1.ok is False


def test_free_module_can_have_parent_ok_child_not(make_report, enrollments):
    extra = list(enrollments) + [
        {"course_code": "B036017", "course_name": "Web应用开发", "term": "2025-2026-2", "status": "passed", "score": 88, "credit": 2.5}
    ]
    report = make_report(enrollments_override=extra)
    m6 = next(m for m in report.modules if m.key == "M6")
    module1 = next(c for c in m6.children if c.key == "M6-1")
    assert m6.earned == 17.5
    assert m6.own_ok is True
    assert module1.own_ok is False
    assert m6.child_ok is False
    assert m6.status == "structure_gap"
    assert any(r["type"] == "structure_gap" for r in report.risks)


def test_over_credit_does_not_inflate_total(make_report, enrollments):
    extra = list(enrollments) + [
        {"course_code": "B90A010", "course_name": "经济学导论", "term": "2025-2026-2", "status": "passed", "score": 90, "credit": 2.0}
    ]
    report = make_report(enrollments_override=extra)
    m2 = next(m for m in report.modules if m.key == "M2")
    assert m2.earned == 13.0
    assert m2.over == 3.0
    assert report.summary["earned"] == 124.0
    assert report.summary["over"] == 3.0


def test_studying_does_not_close_gap(make_report, enrollments):
    extra = list(enrollments) + [
        {"course_code": "B034913", "course_name": "编译原理", "term": "2025-2026-2", "status": "studying", "score": None, "credit": 3.0}
    ]
    report = make_report(enrollments_override=extra)
    m4 = next(m for m in report.modules if m.key == "M4")
    assert m4.earned == 10.5
    assert m4.studying == 3.0
    assert m4.gap == 12.0


def test_retake_passed_overrides_failed(make_report, enrollments):
    extra = list(enrollments) + [
        {"course_code": "B034913", "course_name": "编译原理", "term": "2025-2026-2", "status": "failed", "score": 40, "credit": 3.0},
        {"course_code": "B034913", "course_name": "编译原理", "term": "2026-2027-1", "status": "passed", "score": 70, "credit": 3.0},
    ]
    report = make_report(enrollments_override=extra)
    m4 = next(m for m in report.modules if m.key == "M4")
    assert m4.earned == 13.5
    assert "B034913" not in [c["code"] for c in m4.missing]


def test_failed_course_status_is_visible(make_report, enrollments):
    m1 = next(m for m in make_report().modules if m.key == "M1")
    failed = next(c for c in m1.missing if c["code"] == "B151104")
    assert failed["status"] == "failed"


def test_withdrawn_is_not_counted(plan, make_report):
    report = make_report(
        enrollments_override=[
            {"course_code": "B034913", "course_name": "编译原理", "term": "2025-2026-2", "status": "withdrawn", "credit": 3.0}
        ],
        records_override=[],
    )
    assert report.summary["studying"] == 0.0


def test_enrollment_state_priority():
    state = build_enrollment_state(
        [
            {"course_code": "B1", "status": "failed", "term": "2025-2026-1", "score": 40, "credit": 2},
            {"course_code": "B1", "status": "passed", "term": "2026-2027-1", "score": 80, "credit": 2},
            {"course_code": "B1", "status": "studying", "term": "2026-2027-2", "credit": 2},
        ]
    )
    assert state["B1"].status == "passed"
    assert state["B1"].score == 80


def test_graduation_three_conditions_false(report):
    assert report.graduation["credits"]["ok"] is False
    assert report.graduation["second_classroom"]["ok"] is False
    assert report.graduation["thesis"]["ok"] is False
    assert report.graduation["ok"] is False


def test_thesis_passed(make_report, enrollments):
    extra = list(enrollments) + [
        {"course_code": "B037022", "course_name": "毕业设计（论文）", "term": "2026-2027-2", "status": "passed", "score": 85, "credit": 10.0}
    ]
    report = make_report(enrollments_override=extra)
    assert report.graduation["thesis"]["ok"] is True
    assert report.graduation["credits"]["ok"] is False
    assert report.graduation["ok"] is False


def test_all_conditions_met(plan, make_report, records, zhang):
    all_courses = []
    for node in plan.walk():
        for course in node.courses:
            all_courses.append(
                {
                    "course_code": course.code,
                    "course_name": course.name,
                    "term": "2025-2026-1",
                    "status": "passed",
                    "score": 90,
                    "credit": course.credit,
                }
            )
    sc_records = [
        {"category": "主题社会实践", "term": f"{y}-{y + 1}-2", "status": "approved", "title": "x"}
        for y in (2023, 2024)
    ] + [
        {"category": "创新实践", "term": f"{y}-{y + 1}-2", "status": "approved", "title": "x"}
        for y in (2023, 2024)
    ] + [
        {"category": "学科竞赛与项目", "term": "2025-2026-1", "status": "approved", "title": "x"},
        {"category": "学术交流研讨", "term": "2025-2026-2", "status": "approved", "title": "x"},
        {"category": "学术交流研讨", "term": "2025-2026-2", "status": "approved", "title": "y"},
    ]
    report = make_report(enrollments_override=all_courses, records_override=sc_records)
    assert report.summary["earned"] == 169.0
    assert report.summary["gap"] == 0.0
    assert report.graduation["credits"]["ok"] is True
    assert report.graduation["second_classroom"]["ok"] is True
    assert report.graduation["thesis"]["ok"] is True
    assert report.graduation["ok"] is True


def test_no_negative_gap(report):
    for module in report.modules:
        assert module.gap >= 0
        assert module.over >= 0


def test_missing_prioritises_required_child(report):
    m6 = next(m for m in report.modules if m.key == "M6")
    first = m6.missing[0]
    assert first["required_child"] is True
    assert first["module"] == "M6-1"


def test_m2_tag_subtotals(report):
    m2 = next(m for m in report.modules if m.key == "M2")
    by_name = {c.name: c for c in m2.children}
    assert by_name["思想政治理论"].earned == 3.0
    assert by_name["安全教育"].earned == 2.0
    assert by_name["艺术体育"].earned == 2.0
    assert by_name["其他类"].earned == 4.0
    assert m2.window == {"from_term": 2}


def test_direction_options_expose_all_three(report):
    ids = [o["id"] for o in report.direction["options"]]
    assert ids == ["M5-2", "M5-3", "M5-1"] or set(ids) == {"M5-1", "M5-2", "M5-3"}
    assert len(ids) == 3


def test_risks_have_levels(report):
    levels = {r["level"] for r in report.risks}
    assert "high" in levels
    assert all(r["msg"] for r in report.risks)


def test_engine_version(report):
    assert report.engine_version.startswith("audit-engine/")


def test_evidence_points_to_plan(report):
    assert any(e["rule"] == "plan.total_credits" for e in report.evidence)
    assert report.evidence[0]["value"] == 169.0
