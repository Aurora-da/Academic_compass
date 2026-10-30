from __future__ import annotations

from dataclasses import dataclass, field

from app.services.audit.evaluator import AuditReport
from app.services.plan.compiler import RuntimePlan
from app.services.plan.terms import remaining_terms, term_index

DAY_ORDER = {"周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6, "周日": 7}


def expand_slots(slots: list[str]) -> set[str]:
    tokens: set[str] = set()
    for raw in slots or []:
        parts = str(raw).strip().split()
        if len(parts) != 2:
            continue
        day, periods = parts
        if day not in DAY_ORDER:
            continue
        if "-" in periods:
            a, _, b = periods.partition("-")
            try:
                for p in range(int(a), int(b) + 1):
                    tokens.add(f"{day}-{p}")
            except ValueError:
                continue
        else:
            tokens.add(f"{day}-{periods}")
    return tokens


@dataclass
class Candidate:
    code: str
    name: str
    credit: float
    nature: str
    category: str
    module: str
    module_name: str
    assessment: str
    plan_term: str
    required_child: bool
    offering: dict | None = None
    status: str = "available"  # available / conflict / prereq_missing / not_offered / studying / grade_blocked / full
    conflicts: list[str] = field(default_factory=list)
    prereq_missing: list[str] = field(default_factory=list)
    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    difficulty: dict = field(default_factory=dict)
    slots: list[str] = field(default_factory=list)
    future_semesters: list[str] = field(default_factory=list)
    offering_count: int = 0

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "credit": self.credit,
            "nature": self.nature,
            "category": self.category,
            "module": self.module,
            "module_name": self.module_name,
            "assessment": self.assessment,
            "plan_term": self.plan_term,
            "required_child": self.required_child,
            "offering": self.offering,
            "status": self.status,
            "conflicts": self.conflicts,
            "prereq_missing": self.prereq_missing,
            "score": round(self.score, 1),
            "score_breakdown": {k: round(v, 1) for k, v in self.score_breakdown.items()},
            "reasons": self.reasons,
            "consequences": self.consequences,
            "difficulty": self.difficulty,
            "slots": self.slots,
            "future_semesters": self.future_semesters,
            "offering_count": self.offering_count,
        }


def _flatten_missing(report: AuditReport, plan: RuntimePlan) -> dict[str, dict]:
    module_names = {m.key: m.name for m in plan.walk()}
    required_modules = {
        child.key
        for root in plan.roots
        if root.mode == "free"
        for child in root.children
        if child.require > 0
    }
    result: dict[str, dict] = {}
    for root in report.modules:
        for child in root.children:
            for miss in child.missing:
                result.setdefault(
                    miss["code"],
                    {
                        **miss,
                        "module_name": child.name,
                        "root": root.key,
                        "required_child": bool(miss.get("required_child")) or child.key in required_modules,
                    },
                )
        for miss in root.missing:
            result.setdefault(
                miss["code"],
                {**miss, "module_name": module_names.get(root.key, root.name), "root": root.key},
            )
    return result


def build_candidates(
    plan: RuntimePlan,
    report: AuditReport,
    offerings: list[dict],
    prerequisites: list[dict],
    *,
    current_term: str,
    grade: int,
    locked_codes: set[str] | None = None,
    direction: str | None = None,
) -> tuple[list[Candidate], list[Candidate]]:
    """第一层硬约束过滤。返回 (可用候选, 被硬约束挡掉的候选)。"""
    locked_codes = locked_codes or set()
    passed = {c["code"] for c in report.passed_courses}
    studying = {c["code"] for m in report.modules for c in m.studying_courses}
    studying |= locked_codes
    missing = _flatten_missing(report, plan)
    current_offerings: dict[str, list[dict]] = {}
    for o in offerings:
        if o["semester"] == current_term:
            current_offerings.setdefault(o["course_code"], []).append(o)

    prereq_map: dict[str, list[dict]] = {}
    for p in prerequisites:
        course_key = p.get("course") or p.get("course_code")
        prereq_key = p.get("prereq_code") or p.get("prereq")
        if not course_key or not prereq_key:
            continue
        prereq_map.setdefault(str(course_key), []).append({**p, "prereq_code": str(prereq_key)})

    locked_slots: dict[str, str] = {}
    for code in studying:
        for o in current_offerings.get(code, []):
            for slot in expand_slots(o.get("time_slots") or []):
                locked_slots[slot] = code

    courses = plan.course_map()
    module_names = {m.key: m.name for m in plan.walk()}
    candidates: list[Candidate] = []
    blocked: list[Candidate] = []

    for code, miss in missing.items():
        course = courses.get(code)
        if not course or code in passed:
            continue
        offering_list = sorted(
            current_offerings.get(code, []),
            key=lambda o: (o.get("enrolled", 0) >= o.get("capacity", 0), o.get("class_id", "")),
        )
        cand = Candidate(
            code=code,
            name=course.name,
            credit=course.credit,
            nature=course.nature,
            category=course.category,
            module=course.module_key,
            module_name=module_names.get(course.module_key, course.module_key),
            assessment=course.assessment,
            plan_term=course.plan_term,
            required_child=bool(miss.get("required_child")),
            difficulty={},
            slots=[],
        )
        if code in studying:
            continue
        if course.module_key.startswith("M5-") and direction and not course.module_key.startswith(direction):
            cand.status = "other_direction"
            blocked.append(cand)
            continue
        if not offering_list:
            cand.status = "not_offered"
            blocked.append(cand)
            continue
        offering = offering_list[0]
        cand.offering = offering
        cand.slots = list(offering.get("time_slots") or [])
        allowed = offering.get("allowed_grades") or []
        if allowed and grade not in allowed:
            cand.status = "grade_blocked"
            blocked.append(cand)
            continue

        prereqs = prereq_map.get(code, [])
        missing_prereq = []
        for p in prereqs:
            if p["prereq_code"] in passed:
                continue
            if p.get("type") == "同修" and p["prereq_code"] in studying:
                continue
            missing_prereq.append(p["prereq_code"])
        if missing_prereq:
            cand.prereq_missing = missing_prereq
            cand.status = "prereq_missing"
            blocked.append(cand)
            continue

        # 同课程多个班级：选一个与已锁定课程不冲突、容量更充足的班
        best = offering
        conflict_slots = []
        for o in offering_list:
            slots = expand_slots(o.get("time_slots") or [])
            conflict = sorted(slot for slot in slots if slot in locked_slots)
            if not conflict:
                best = o
                conflict_slots = []
                break
            conflict_slots = conflict
        if conflict_slots:
            best = next(
                (o for o in offering_list if not (expand_slots(o.get("time_slots") or []) & set(locked_slots))),
                offering_list[0],
            )
        cand.offering = best
        cand.slots = list(best.get("time_slots") or [])
        remaining_capacity = best.get("capacity", 0) - best.get("enrolled", 0)
        if remaining_capacity <= 0:
            cand.status = "full"
        for slot in expand_slots(cand.slots):
            if slot in locked_slots:
                cand.status = "conflict"
                other = locked_slots[slot]
                cand.conflicts.append(f"{slot} 与已选课程 {courses.get(other).name if courses.get(other) else other} 冲突")
        candidates.append(cand)

    return candidates, blocked
