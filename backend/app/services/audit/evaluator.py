from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.audit.second_classroom import check_second_classroom
from app.services.plan.compiler import RuntimeCourse, RuntimeNode, RuntimePlan
from app.services.plan.terms import (
    academic_to_index,
    index_to_term,
    remaining_terms,
    term_index,
)

THESIS_CODE = "B037022"


@dataclass
class EnrollmentState:
    status: str = "not_started"  # passed / studying / failed / withdrawn / not_started
    score: float | None = None
    term: str = ""
    credit: float = 0.0


def build_enrollment_state(enrollments: list[dict]) -> dict[str, EnrollmentState]:
    grouped: dict[str, list[dict]] = {}
    for e in enrollments:
        grouped.setdefault(e["course_code"], []).append(e)

    state: dict[str, EnrollmentState] = {}
    for code, items in grouped.items():
        passed = [e for e in items if e.get("status") == "passed"]
        if passed:
            best = sorted(passed, key=lambda e: (e.get("term", ""), e.get("score") or 0))[0]
            state[code] = EnrollmentState("passed", best.get("score"), best.get("term", ""), best.get("credit", 0.0))
            continue
        studying = [e for e in items if e.get("status") == "studying"]
        if studying:
            best = sorted(studying, key=lambda e: e.get("term", ""))[-1]
            state[code] = EnrollmentState("studying", None, best.get("term", ""), best.get("credit", 0.0))
            continue
        failed = [e for e in items if e.get("status") == "failed"]
        if failed:
            best = sorted(failed, key=lambda e: e.get("term", ""))[-1]
            state[code] = EnrollmentState("failed", best.get("score"), best.get("term", ""), best.get("credit", 0.0))
            continue
        withdrawn = [e for e in items if e.get("status") == "withdrawn"]
        if withdrawn:
            state[code] = EnrollmentState("withdrawn", None, withdrawn[-1].get("term", ""), 0.0)
    return state


@dataclass
class EvaluationOptions:
    current_term: str = ""
    entry_year: int = 2023
    target_graduation_term: str = ""
    direction: str | None = None
    offerings: list[dict] = field(default_factory=list)
    second_classroom_records: list[dict] = field(default_factory=list)
    thesis_passed: bool | None = None


@dataclass
class NodeResult:
    key: str
    name: str
    mode: str
    require: float
    earned: float = 0.0
    studying: float = 0.0
    gap: float = 0.0
    over: float = 0.0
    own_ok: bool = False
    child_ok: bool = True
    ok: bool = False
    status: str = "gap"
    picked: str | None = None
    picked_name: str | None = None
    direction: bool = False
    window: dict | None = None
    tag: str | None = None
    tags: list[str] = field(default_factory=list)
    courses_total: int = 0
    courses_passed: int = 0
    missing: list[dict] = field(default_factory=list)
    studying_courses: list[dict] = field(default_factory=list)
    children: list[NodeResult] = field(default_factory=list)
    _courses: list[RuntimeCourse] = field(default_factory=list, repr=False)

    def to_dict(self, include_children: bool = True) -> dict[str, Any]:
        data = {
            "id": self.key,
            "name": self.name,
            "mode": self.mode,
            "require": round(self.require, 2),
            "earned": round(self.earned, 2),
            "studying": round(self.studying, 2),
            "gap": round(self.gap, 2),
            "over": round(self.over, 2),
            "own_ok": self.own_ok,
            "child_ok": self.child_ok,
            "ok": self.ok,
            "status": self.status,
            "picked": self.picked,
            "picked_name": self.picked_name,
            "direction": self.direction,
            "window": self.window,
            "tag": self.tag,
            "tags": self.tags,
            "courses_total": self.courses_total,
            "courses_passed": self.courses_passed,
            "missing": self.missing,
            "studying_courses": self.studying_courses,
        }
        if include_children:
            data["children"] = [c.to_dict() for c in self.children]
        return data


@dataclass
class AuditReport:
    student: dict[str, Any]
    plan: dict[str, Any]
    as_of: str
    program_term: str
    summary: dict[str, Any]
    graduation: dict[str, Any]
    modules: list[NodeResult]
    risks: list[dict]
    direction: dict[str, Any]
    passed_courses: list[dict]
    evidence: list[dict]
    engine_version: str
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "student": self.student,
            "plan": self.plan,
            "as_of": self.as_of,
            "program_term": self.program_term,
            "summary": self.summary,
            "graduation": self.graduation,
            "modules": [m.to_dict() for m in self.modules],
            "risks": self.risks,
            "direction": self.direction,
            "passed_courses": self.passed_courses,
            "evidence": self.evidence,
            "engine_version": self.engine_version,
            "generated_at": self.generated_at,
        }


def _effective_courses(node: RuntimeNode, results: dict[str, NodeResult], opts: EvaluationOptions) -> tuple[list[RuntimeCourse], NodeResult | None]:
    if node.mode == "any_of" and node.children:
        if opts.direction and opts.direction in {c.key for c in node.children}:
            picked = results[opts.direction]
        else:
            picked = max((results[c.key] for c in node.children), key=lambda r: (r.earned, r.courses_passed))
        courses = list(node.courses) + list(picked._courses)
        return courses, picked
    courses = list(node.courses)
    for child in node.children:
        courses.extend(results[child.key]._courses)
    seen: set[str] = set()
    unique: list[RuntimeCourse] = []
    for course in courses:
        if course.code in seen:
            continue
        seen.add(course.code)
        unique.append(course)
    return unique, None


def _evaluate_node(
    node: RuntimeNode,
    state: dict[str, EnrollmentState],
    opts: EvaluationOptions,
    child_results: dict[str, NodeResult],
) -> NodeResult:
    children = [_evaluate_node(c, state, opts, child_results) for c in node.children]
    for child in children:
        child_results[child.key] = child

    courses, picked = _effective_courses(node, child_results, opts)
    passed = [c for c in courses if state.get(c.code, EnrollmentState()).status == "passed"]
    studying = [c for c in courses if state.get(c.code, EnrollmentState()).status == "studying"]
    earned = round(sum(c.credit for c in passed), 2)
    studying_credit = round(sum(c.credit for c in studying), 2)

    own_ok = earned + 1e-9 >= node.require
    if node.mode == "any_of":
        if opts.direction and opts.direction in {c.key for c in node.children}:
            child_ok = bool(picked and picked.ok)
        else:
            child_ok = any(c.ok for c in children)
    elif node.mode == "free":
        required_children = [c for c in children if c.require > 0]
        child_ok = all(c.ok for c in required_children)
    else:
        child_ok = all(c.ok for c in children)

    ok = own_ok and child_ok
    if not own_ok:
        status = "gap"
    elif not child_ok:
        status = "structure_gap"
    else:
        status = "ok"

    # 结构优先：有下限的子模块课程排在缺课列表最前
    required_codes: set[str] = set()
    for child in node.children:
        if child.require > 0:
            for c in child.all_courses():
                required_codes.add(c.code)

    missing = [
        {
            "code": c.code,
            "name": c.name,
            "credit": c.credit,
            "status": state.get(c.code, EnrollmentState()).status,
            "plan_term": c.plan_term,
            "assessment": c.assessment,
            "nature": c.nature,
            "module": c.module_key,
            "required_child": c.code in required_codes,
        }
        for c in courses
        if state.get(c.code, EnrollmentState()).status != "passed"
    ]
    missing.sort(key=lambda x: (0 if x["required_child"] else 1, term_index(x["plan_term"]), -x["credit"]))

    studying_courses = [
        {
            "code": c.code,
            "name": c.name,
            "credit": c.credit,
            "term": state.get(c.code, EnrollmentState()).term,
        }
        for c in studying
    ]

    return NodeResult(
        key=node.key,
        name=node.name,
        mode=node.mode,
        require=node.require,
        earned=earned,
        studying=studying_credit,
        gap=round(max(0.0, node.require - earned), 2),
        over=round(max(0.0, earned - node.require), 2),
        own_ok=own_ok,
        child_ok=child_ok,
        ok=ok,
        status=status,
        picked=picked.key if picked else None,
        picked_name=picked.name if picked else None,
        direction=node.direction,
        window=node.window,
        tag=node.tag,
        tags=node.tags,
        courses_total=len(courses),
        courses_passed=len(passed),
        missing=missing,
        studying_courses=studying_courses,
        children=children,
        _courses=courses,
    )


def evaluate_plan(
    plan: RuntimePlan,
    enrollments: list[dict],
    *,
    current_term: str = "",
    entry_year: int = 2023,
    target_graduation_term: str = "",
    direction: str | None = None,
    offerings: list[dict] | None = None,
    second_classroom_records: list[dict] | None = None,
    thesis_passed: bool | None = None,
    student: dict | None = None,
) -> AuditReport:
    opts = EvaluationOptions(
        current_term=current_term or settings.current_term,
        entry_year=entry_year,
        target_graduation_term=target_graduation_term,
        direction=direction,
        offerings=offerings or [],
        second_classroom_records=second_classroom_records or [],
        thesis_passed=thesis_passed,
    )
    state = build_enrollment_state(enrollments)
    child_results: dict[str, NodeResult] = {}
    modules = [_evaluate_node(root, state, opts, child_results) for root in plan.roots]

    total_require = round(sum(m.require for m in modules), 2) or plan.total_credits
    capped_earned = round(sum(min(m.earned, m.require) for m in modules), 2)
    studying_total = round(sum(m.studying for m in modules), 2)
    over_total = round(sum(m.over for m in modules), 2)
    gap_total = round(max(0.0, total_require - capped_earned), 2)
    percent = round(capped_earned / total_require * 100, 2) if total_require else 0.0

    summary = {
        "require": total_require,
        "earned": capped_earned,
        "studying": studying_total,
        "gap": gap_total,
        "over": over_total,
        "percent": percent,
        "capped": True,
    }

    sc = check_second_classroom(
        plan.second_classroom, opts.second_classroom_records, entry_year, opts.current_term
    )
    thesis_state = state.get(THESIS_CODE, EnrollmentState())
    if opts.thesis_passed is not None:
        thesis_ok = opts.thesis_passed
        thesis_status = "passed" if thesis_ok else "not_started"
    else:
        thesis_ok = thesis_state.status == "passed"
        thesis_status = thesis_state.status
    credits_ok = gap_total <= 1e-9
    graduation_ok = bool(credits_ok and sc["ok"] is True and thesis_ok)

    graduation = {
        "credits": {"require": total_require, "earned": capped_earned, "gap": gap_total, "ok": credits_ok},
        "second_classroom": sc,
        "thesis": {
            "status": thesis_status,
            "ok": thesis_ok,
            "label": {
                "not_started": "未开始",
                "studying": "进行中",
                "passed": "答辩通过",
                "failed": "未通过",
            }.get(thesis_status, thesis_status),
        },
        "ok": graduation_ok,
    }

    direction_info = _direction_info(plan, modules, opts)
    passed_courses = [
        {
            "code": code,
            "name": plan.course_map().get(code).name if plan.course_map().get(code) else "",
            "credit": plan.course_map().get(code).credit if plan.course_map().get(code) else st.credit,
            "term": st.term,
            "score": st.score,
        }
        for code, st in sorted(state.items(), key=lambda kv: kv[1].term)
        if st.status == "passed" and code in plan.course_map()
    ]
    risks = _build_risks(plan, modules, summary, graduation, direction_info, sc, opts)
    evidence = _evidence(plan, modules)
    student_info = student or {}
    program_term = index_to_term(academic_to_index(opts.current_term, opts.entry_year))

    return AuditReport(
        student=student_info,
        plan={
            "id": plan.plan_id,
            "name": plan.name,
            "major": plan.major,
            "grade": plan.grade,
            "degree": plan.degree,
            "total_credits": plan.total_credits,
            "duration": plan.duration,
            "status": plan.status,
            "version": plan.plan_id,
        },
        as_of=opts.current_term,
        program_term=program_term,
        summary=summary,
        graduation=graduation,
        modules=modules,
        risks=risks,
        direction=direction_info,
        passed_courses=passed_courses,
        evidence=evidence,
        engine_version=settings.engine_version,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _direction_info(plan: RuntimePlan, modules: list[NodeResult], opts: EvaluationOptions) -> dict:
    m5 = next((m for m in modules if m.direction or m.mode == "any_of"), None)
    if not m5:
        return {"selected": None, "locked": False, "options": []}
    selected = m5.picked
    locked = bool(opts.direction)
    options = []
    for child in m5.children:
        options.append(
            {
                "id": child.key,
                "name": child.name,
                "require": child.require,
                "earned": child.earned,
                "gap": child.gap,
                "ok": child.ok,
                "courses_total": child.courses_total,
                "courses_passed": child.courses_passed,
                "missing": [{"code": c["code"], "name": c["name"], "credit": c["credit"]} for c in child.missing],
            }
        )
    return {
        "selected": selected,
        "selected_name": m5.picked_name,
        "locked": locked,
        "module": m5.key,
        "require": m5.require,
        "gap": m5.gap,
        "options": options,
    }


def _build_risks(
    plan: RuntimePlan,
    modules: list[NodeResult],
    summary: dict,
    graduation: dict,
    direction: dict,
    sc: dict,
    opts: EvaluationOptions,
) -> list[dict]:
    risks: list[dict] = []
    after = remaining_terms(
        opts.current_term, opts.target_graduation_term, opts.entry_year, include_current=False
    ) or remaining_terms(opts.current_term, opts.target_graduation_term, opts.entry_year)
    n = max(1, len(after))

    for m in modules:
        if m.gap > 1e-9:
            rate = m.gap / n
            level = "high" if (m.gap >= 15 or rate >= 5.5) else "medium"
            risks.append(
                {
                    "level": level,
                    "type": "credit_gap",
                    "module": m.key,
                    "msg": f"{m.name}缺口 {m.gap:.1f} 学分，剩余 {n} 个学期，需每学期 ≥ {rate:.1f}",
                }
            )

    def walk(nodes: list[NodeResult]):
        for node in nodes:
            yield node
            yield from walk(node.children)

    for node in walk(modules):
        if node.mode == "any_of":
            # any_of 只认被选中的方向；其他方向组的下限不参与结构判定
            continue
        if node.own_ok and not node.child_ok:
            bad = [c for c in node.children if c.require > 0 and not c.ok]
            if bad:
                child = bad[0]
                risks.append(
                    {
                        "level": "high",
                        "type": "structure_gap",
                        "module": node.key,
                        "msg": (
                            f"{node.name}总量已达标（{node.earned:.1f}/{node.require:.1f}），"
                            f"但「{child.name}」还差 {child.gap:.1f} 学分——总量达标不等于结构达标"
                        ),
                    }
                )
        elif not node.own_ok and not node.child_ok:
            # 父项本身有缺口，但子项缺口更大：补课必须优先补子项，否则总量补满结构仍不达标
            bad = [c for c in node.children if c.require > 0 and c.gap > node.gap + 1e-9]
            if bad:
                child = max(bad, key=lambda c: c.gap)
                risks.append(
                    {
                        "level": "high",
                        "type": "structure_priority",
                        "module": node.key,
                        "msg": (
                            f"{node.name}总量差 {node.gap:.1f} 分，但「{child.name}」差 {child.gap:.1f} 分"
                            f"——补课优先补{child.name}，否则总量补满、结构仍不达标"
                        ),
                    }
                )

    if direction.get("options") and not direction.get("locked"):
        risks.append(
            {
                "level": "medium",
                "type": "direction_undecided",
                "module": direction.get("module"),
                "msg": "专业方向尚未锁定：三组方向各 6 学分，方向同时决定 2 学分创新实践的内容",
            }
        )

    if sc["ok"] is False:
        for item in sc["items"]:
            if item["status"] == "unmet":
                level = "high" if item["period_type"] == "total" else "medium"
                risks.append(
                    {
                        "level": level,
                        "type": "second_classroom",
                        "msg": f"第二课堂·{item['category']}：{item['message']}",
                    }
                )

    if not graduation["thesis"]["ok"]:
        target_idx = academic_to_index(opts.target_graduation_term, opts.entry_year) if opts.target_graduation_term else 0
        current_idx = academic_to_index(opts.current_term, opts.entry_year)
        if target_idx - current_idx <= 2:
            risks.append(
                {
                    "level": "medium",
                    "type": "thesis",
                    "msg": f"毕业设计（论文）尚未通过（当前：{graduation['thesis']['label']}）",
                }
            )

    # 最后一次开课提醒：剩余开课次数 ≤ 1 的必修课
    offering_index: dict[str, list[str]] = {}
    for o in opts.offerings:
        offering_index.setdefault(o["course_code"], []).append(o["semester"])
    last_calls = []
    for m in modules:
        for miss in m.missing:
            if miss["nature"] != "必修" or miss["status"] == "passed":
                continue
            future = sorted(
                {s for s in offering_index.get(miss["code"], []) if opts.current_term < s <= opts.target_graduation_term}
            )
            if len(future) == 0:
                continue
            if len(future) == 1 and future[0]:
                last_calls.append((miss, future[0]))
    for miss, semester in last_calls[:2]:
        risks.append(
            {
                "level": "medium",
                "type": "last_offering",
                "module": miss["module"],
                "msg": f"{miss['name']}（{miss['credit']:.1f}）未修，{semester} 仅剩 1 次开课，错过将影响按期毕业",
            }
        )

    order = {"high": 0, "medium": 1, "low": 2}
    risks.sort(key=lambda r: (order.get(r["level"], 3), r["type"]))
    return risks[:8]


def _evidence(plan: RuntimePlan, modules: list[NodeResult]) -> list[dict]:
    evidence = [
        {
            "rule": "plan.total_credits",
            "source": f"{plan.source}#七、毕业学分要求",
            "value": plan.total_credits,
        }
    ]
    for m in modules:
        evidence.append(
            {
                "rule": f"{m.key}.require",
                "source": f"{plan.source}#{m.name}",
                "value": m.require,
            }
        )
    evidence.append(
        {
            "rule": "graduation.conditions",
            "source": f"{plan.source}#七、修业年限、授予学位及毕业学分要求",
            "value": plan.graduation_conditions,
        }
    )
    return evidence


def simulate_failure(report: AuditReport, plan: RuntimePlan, course_code: str) -> dict:
    """What-if：假设某门课从 passed 变为 failed，返回缺口变化。"""
    target = plan.course_map().get(course_code)
    if not target:
        return {"error": f"课程 {course_code} 不在培养方案中"}
    before_module = next(
        (m for m in report.modules if any(c["code"] == course_code for c in m.missing) or _contains(plan.node(m.key), course_code)),
        None,
    )
    before_gap = report.summary["gap"]
    new_gap = round(before_gap + target.credit, 2)
    modules = []
    for m in report.modules:
        if _contains(plan.node(m.key), course_code):
            modules.append(
                {
                    "id": m.key,
                    "name": m.name,
                    "gap_before": m.gap,
                    "gap_after": round(m.gap + target.credit, 2),
                    "ok_after": False,
                }
            )
    return {
        "course": {"code": target.code, "name": target.name, "credit": target.credit},
        "summary_before": {"gap": before_gap, "earned": report.summary["earned"]},
        "summary_after": {
            "gap": new_gap,
            "earned": round(report.summary["earned"] - target.credit, 2),
        },
        "modules": modules,
        "verdict": "挂科后总缺口将扩大，且该模块由达标转为不达标" if modules else "挂科后总缺口将扩大",
    }


def _contains(node: RuntimeNode | None, code: str) -> bool:
    if node is None:
        return False
    return any(c.code == code for c in node.all_courses())
