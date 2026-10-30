from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.audit.evaluator import evaluate_plan
from app.services.plan.loader import compile_spec, load_plan_yaml

BACKEND = Path(__file__).resolve().parents[1]
PLAN_PATH = BACKEND / "data" / "plans" / "CS-BT-2024-v1.yaml"
STUDENTS_PATH = BACKEND / "data" / "seeds" / "students.json"


@pytest.fixture(scope="session")
def plan_spec():
    return load_plan_yaml(PLAN_PATH)


@pytest.fixture(scope="session")
def plan(plan_spec):
    return compile_spec(plan_spec)


@pytest.fixture(scope="session")
def seed_data():
    return json.loads(STUDENTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def zhang(seed_data):
    return seed_data["students"][0]


@pytest.fixture(scope="session")
def enrollments(plan, zhang):
    courses = plan.course_map()
    return [
        {
            "course_code": e["code"],
            "course_name": courses[e["code"]].name,
            "term": e["term"],
            "status": e["status"],
            "score": e.get("score"),
            "credit": courses[e["code"]].credit,
        }
        for e in zhang["enrollments"]
    ]


@pytest.fixture(scope="session")
def records(zhang):
    return zhang["second_classroom"]


@pytest.fixture
def make_report(plan, enrollments, records):
    def _make(enrollments_override=None, records_override=None, direction="M5-1", **kwargs):
        return evaluate_plan(
            plan,
            enrollments_override if enrollments_override is not None else enrollments,
            current_term=kwargs.pop("current_term", "2025-2026-2"),
            entry_year=kwargs.pop("entry_year", 2023),
            target_graduation_term=kwargs.pop("target_graduation_term", "2026-2027-2"),
            direction=direction,
            offerings=kwargs.pop("offerings", []),
            second_classroom_records=records_override if records_override is not None else records,
            student={"name": "张三", "student_no": "2023001"},
            **kwargs,
        )

    return _make
