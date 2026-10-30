from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AssignCandidate:
    code: str
    credit: float
    modules: list[str]


def _priority(module: dict) -> float:
    gap = max(0.0, float(module.get("require", 0)) - float(module.get("earned", 0)))
    required = 2.0 if float(module.get("require", 0)) > 0 else 1.0
    return required + gap / max(1.0, float(module.get("require", 1)))


def solve_assignment(
    candidates: list[AssignCandidate],
    modules: list[dict],
    *,
    cap_at_require: bool = True,
) -> dict:
    """学分归属：一门课只能计入一个模块（0-1 规划）。

    优先 OR-Tools CP-SAT；不可用时退化为确定性贪心，结果可复现。
    返回 {"assignments": {code: module}, "unassigned": [...], "solver": "cp-sat"|"greedy"}
    """
    module_map = {m["key"]: m for m in modules}
    feasible = [
        AssignCandidate(c.code, c.credit, [m for m in c.modules if m in module_map])
        for c in candidates
        if any(m in module_map for m in c.modules)
    ]
    if not feasible:
        return {"assignments": {}, "unassigned": [c.code for c in candidates], "solver": "none"}

    priorities = {key: _priority(module) for key, module in module_map.items()}
    try:
        from ortools.sat.python import cp_model  # type: ignore

        model = cp_model.CpModel()
        x: dict[tuple[str, str], object] = {}
        for c in feasible:
            for m in c.modules:
                x[(c.code, m)] = model.NewBoolVar(f"x_{c.code}_{m}")
            model.Add(sum(x[(c.code, m)] for m in c.modules) <= 1)

        if cap_at_require:
            for key, module in module_map.items():
                variables = [(x[(c.code, key)], c.credit) for c in feasible if (c.code, key) in x]
                if not variables:
                    continue
                capacity = max(0.0, float(module.get("require", 0)) - float(module.get("earned", 0)))
                # 学分是 0.5 粒度，统一放大 2 倍做整数约束
                model.Add(
                    sum(int(round(credit * 2)) * var for var, credit in variables)
                    <= int(capacity * 2)
                )

        course_by_code = {c.code: c for c in feasible}
        objective = [
            int(round(course_by_code[code].credit * 10 * priorities[key])) * var
            for (code, key), var in x.items()
        ]
        model.Maximize(sum(objective))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 3.0
        status = solver.Solve(model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            assignments = {
                code: key
                for (code, key), var in x.items()
                if solver.Value(var)
            }
            unassigned = [c.code for c in candidates if c.code not in assignments]
            return {"assignments": assignments, "unassigned": unassigned, "solver": "cp-sat"}
    except Exception:  # pragma: no cover - 依赖缺失时走兜底
        pass

    # 贪心兜底：候选少的先分配，优先填缺口比例大的模块
    remaining = {k: max(0.0, float(m.get("require", 0)) - float(m.get("earned", 0))) for k, m in module_map.items()}
    order = sorted(feasible, key=lambda c: (len(c.modules), -c.credit, c.code))
    assignments: dict[str, str] = {}
    for c in order:
        choices = [m for m in c.modules if remaining[m] + 1e-9 >= c.credit]
        if not choices:
            continue
        target = max(choices, key=lambda m: (priorities[m], -remaining[m]))
        assignments[c.code] = target
        remaining[target] = round(remaining[target] - c.credit, 2)
    return {
        "assignments": assignments,
        "unassigned": [c.code for c in candidates if c.code not in assignments],
        "solver": "greedy",
    }
