from __future__ import annotations

from app.services.audit.assigner import AssignCandidate, solve_assignment


def test_assignment_respects_one_module_per_course():
    result = solve_assignment(
        [
            AssignCandidate("A", 3.0, ["M1", "M2"]),
            AssignCandidate("B", 2.0, ["M2"]),
            AssignCandidate("C", 1.0, ["M1"]),
        ],
        [
            {"key": "M1", "require": 4.0, "earned": 0.0},
            {"key": "M2", "require": 4.0, "earned": 0.0},
        ],
    )
    assert result["solver"] in {"cp-sat", "greedy"}
    assert len(result["assignments"]) <= 3
    assert len(set(result["assignments"].keys())) == len(result["assignments"])
    for module in result["assignments"].values():
        assert module in {"M1", "M2"}


def test_assignment_prefers_gap_and_caps():
    result = solve_assignment(
        [AssignCandidate("A", 3.0, ["M1", "M2"]), AssignCandidate("B", 3.0, ["M1", "M2"])],
        [
            {"key": "M1", "require": 3.0, "earned": 0.0},
            {"key": "M2", "require": 3.0, "earned": 0.0},
        ],
    )
    assert sorted(result["assignments"].values()) == ["M1", "M2"]


def test_assignment_empty():
    result = solve_assignment([], [{"key": "M1", "require": 3.0, "earned": 0.0}])
    assert result["assignments"] == {}
    assert result["solver"] == "none"
