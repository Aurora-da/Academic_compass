from __future__ import annotations

from dataclasses import dataclass, field

from app.services.planner.filter import Candidate, expand_slots

TIERS = [
    {"key": "steady", "name": "稳妥型", "budget": 20.0, "desc": "必修 + 最紧迫缺口，约 20 学分"},
    {"key": "balanced", "name": "均衡型", "budget": 24.0, "desc": "必修 + 方向课 + 1 门兴趣，约 24 学分"},
    {"key": "sprint", "name": "冲刺型", "budget": 28.0, "desc": "满负荷 28 学分，仅在提前毕业目标下推荐"},
]


@dataclass
class PlanPackage:
    key: str
    name: str
    desc: str
    budget: float
    courses: list[Candidate] = field(default_factory=list)
    total_credits: float = 0.0
    total_with_locked: float = 0.0
    slots: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "desc": self.desc,
            "budget": self.budget,
            "total_credits": round(self.total_credits, 2),
            "total_with_locked": round(self.total_with_locked or self.total_credits, 2),
            "courses": [c.to_dict() for c in self.courses],
            "slots": self.slots,
            "warnings": self.warnings,
        }


def _eligible(cand: Candidate) -> bool:
    return cand.status == "available" and cand.offering is not None


def _add(package: PlanPackage, cand: Candidate, reserved_slots: set[str], current_credits: float) -> bool:
    slots = expand_slots(cand.slots)
    if slots & reserved_slots:
        return False
    if package.total_credits + current_credits + cand.credit > package.budget + 1e-9:
        return False
    package.courses.append(cand)
    package.total_credits = round(package.total_credits + cand.credit, 2)
    package.total_with_locked = round(package.total_credits + current_credits, 2)
    reserved_slots |= slots
    for slot in slots:
        package.slots[slot] = cand.name
    return True


def solve_plans(
    candidates: list[Candidate],
    *,
    locked_courses: list[dict] | None = None,
    current_credits: float = 0.0,
) -> list[PlanPackage]:
    """第三层：在学分上限 + 时间不冲突下生成三套方案。

    有 OR-Tools 时可替换为 CP-SAT；当前实现为确定性贪心，保证可复现、可测试。
    """
    locked_courses = locked_courses or []
    locked_slots: set[str] = set()
    for c in locked_courses:
        locked_slots |= expand_slots(c.get("slots") or [])

    eligible = [c for c in candidates if _eligible(c)]
    eligible.sort(key=lambda c: (-c.score, c.credit, c.code))

    packages: list[PlanPackage] = []
    for tier in TIERS:
        package = PlanPackage(**tier)
        reserved = set(locked_slots)
        selected_codes: set[str] = set()

        if tier["key"] == "steady":
            pool = [c for c in eligible if c.nature == "必修" or c.required_child]
        else:
            pool = list(eligible)

        elective_count = 0
        for cand in pool:
            if cand.code in selected_codes:
                continue
            if cand.status == "conflict":
                continue
            if tier["key"] == "balanced" and cand.nature != "必修" and not cand.required_child:
                if not cand.module.startswith("M5"):
                    if elective_count >= 1:
                        continue
                    if cand.credit > 2.5:
                        continue
            if _add(package, cand, reserved, current_credits):
                selected_codes.add(cand.code)
                if cand.nature != "必修" and not cand.required_child and not cand.module.startswith("M5"):
                    elective_count += 1

        package.total_with_locked = round(package.total_credits + current_credits, 2)
        if package.total_with_locked > tier["budget"]:
            package.warnings.append(
                f"含在修 {current_credits:.1f} 学分后共 {package.total_with_locked:.1f}，超出建议上限 {tier['budget']:.0f}"
            )
        if not package.courses:
            package.warnings.append("本学期没有满足硬约束的可选课程")
        packages.append(package)
    return packages
