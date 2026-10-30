from __future__ import annotations

import copy

from app.services.plan.validator import validate_spec


def test_plan_has_no_errors(plan_spec):
    issues = validate_spec(plan_spec)
    assert [i for i in issues if i.level == "error"] == []
    assert [i for i in issues if i.level == "warning"] == []


def test_detects_total_mismatch(plan_spec):
    spec = copy.deepcopy(plan_spec)
    spec.total_credits = 170
    issues = validate_spec(spec)
    assert any(i.code == "TOTAL_MISMATCH" for i in issues)


def test_detects_duplicate_course(plan_spec):
    spec = copy.deepcopy(plan_spec)
    spec.modules[0].courses.append(copy.deepcopy(spec.modules[0].courses[0]))
    issues = validate_spec(spec)
    assert any(i.code == "DUP_COURSE" for i in issues)


def test_detects_module_course_sum_mismatch(plan_spec):
    spec = copy.deepcopy(plan_spec)
    spec.modules[0].courses.pop()
    issues = validate_spec(spec)
    assert any(i.code == "MODULE_COURSE_SUM" for i in issues)


def test_detects_graduation_credit_mismatch(plan_spec):
    spec = copy.deepcopy(plan_spec)
    spec.graduation_conditions[0]["value"] = 168
    issues = validate_spec(spec)
    assert any(i.code == "GRADUATION_CREDIT_MISMATCH" for i in issues)


def test_detects_bad_term(plan_spec):
    spec = copy.deepcopy(plan_spec)
    spec.modules[0].courses[0].plan_term = "5-5"
    issues = validate_spec(spec)
    assert any(i.code == "COURSE_TERM" for i in issues)


def test_free_child_under_parent(plan_spec):
    m6 = next(m for m in plan_spec.modules if m.key == "M6")
    assert m6.require == 17.0
    assert sum(c.require for c in m6.children) == 12.0
