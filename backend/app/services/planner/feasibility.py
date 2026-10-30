from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.services.audit.evaluator import AuditReport
from app.services.plan.compiler import RuntimePlan
from app.services.plan.terms import graduation_term, remaining_terms, term_index


@dataclass
class Scenario:
    years: int
    label: str
    target_term: str
    remaining_terms: int
    gap: float
    per_term: float
    suggested_per_term: float
    credits_feasible: bool
    blocked_courses: list[dict] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    verdict: str = ""

    def to_dict(self) -> dict:
        return {
            "years": self.years,
            "label": self.label,
            "target_term": self.target_term,
            "remaining_terms": self.remaining_terms,
            "gap": round(self.gap, 2),
            "per_term": round(self.per_term, 2),
            "suggested_per_term": round(self.suggested_per_term, 2),
            "credits_feasible": self.credits_feasible,
            "blocked_courses": self.blocked_courses,
            "blockers": self.blockers,
            "verdict": self.verdict,
        }


def _ceil_half(value: float) -> float:
    return round(math.ceil(value * 2) / 2, 1)


def assess_feasibility(
    plan: RuntimePlan,
    report: AuditReport,
    offerings: list[dict],
    *,
    entry_year: int,
    current_term: str,
    max_credits: float = 28.0,
) -> dict:
    gap = report.summary["gap"]
    thesis = report.graduation["thesis"]
    sc = report.graduation["second_classroom"]
    sc_blockers = [
        f"第二课堂·{i['category']}：{i['message']}"
        for i in sc.get("items", [])
        if i.get("status") == "unmet"
    ]
    non_credit_blockers: list[str] = []
    if not thesis.get("ok"):
        non_credit_blockers.append(f"毕业设计（论文）：{thesis.get('label')}")
    non_credit_blockers.extend(sc_blockers)

    offering_semesters: dict[str, set[str]] = {}
    for o in offerings:
        offering_semesters.setdefault(o["course_code"], set()).add(o["semester"])

    missing = []
    seen: set[str] = set()
    for root in report.modules:
        for miss in root.missing:
            if miss["code"] in seen:
                continue
            seen.add(miss["code"])
            missing.append(miss)

    scenarios: list[Scenario] = []
    for years in (3, 4, 5):
        target = graduation_term(entry_year, years)
        terms = remaining_terms(current_term, target, entry_year, include_current=True)
        remaining = max(1, len(terms))
        per_term = gap / remaining
        target_idx = term_index(f"{years}-2") if years <= 6 else 8
        blocked = []
        for miss in missing:
            plan_idx = term_index(miss["plan_term"])
            all_semesters = offering_semesters.get(miss["code"], set())
            available = sorted(s for s in all_semesters if current_term <= s <= target)
            if plan_idx > target_idx:
                blocked.append(
                    {
                        "code": miss["code"],
                        "name": miss["name"],
                        "credit": miss["credit"],
                        "plan_term": miss["plan_term"],
                        "reason": "培养方案指导性学期晚于目标毕业学期",
                    }
                )
            elif all_semesters and not available:
                blocked.append(
                    {
                        "code": miss["code"],
                        "name": miss["name"],
                        "credit": miss["credit"],
                        "plan_term": miss["plan_term"],
                        "reason": "目标毕业前无开课记录",
                    }
                )
        credits_ok = per_term <= max_credits + 1e-9 and not blocked
        label = {3: "3 年（提前）", 4: "4 年（标准）", 5: "5 年（延毕）"}[years]
        if credits_ok:
            verdict = f"学分可行：剩余 {remaining} 个学期，每学期约 {per_term:.1f} 学分（上限 {max_credits:.0f}）"
        elif blocked:
            verdict = f"学分不可行：有 {len(blocked)} 门课在目标毕业前无法完成"
        else:
            verdict = f"学分不可行：剩余 {remaining} 个学期要修 {gap:.1f} 学分，需每学期 {per_term:.1f}，超过 {max_credits:.0f} 上限"
        if credits_ok and non_credit_blockers:
            verdict += "；但非学分条件仍有卡点"
        scenarios.append(
            Scenario(
                years=years,
                label=label,
                target_term=target,
                remaining_terms=remaining,
                gap=gap,
                per_term=per_term,
                suggested_per_term=_ceil_half(per_term),
                credits_feasible=credits_ok,
                blocked_courses=blocked[:6],
                blockers=non_credit_blockers,
                verdict=verdict,
            )
        )

    feasible_years = [s.years for s in scenarios if s.credits_feasible]
    recommended = min(feasible_years) if feasible_years else None
    return {
        "scenarios": [s.to_dict() for s in scenarios],
        "current_term": current_term,
        "gap": round(gap, 2),
        "max_credits": max_credits,
        "non_credit_blockers": non_credit_blockers,
        "earliest_feasible_years": recommended,
        "summary": _summary_text(scenarios, non_credit_blockers, recommended),
    }


def _summary_text(scenarios: list[Scenario], non_credit: list[str], recommended: int | None) -> str:
    by_year = {s.years: s for s in scenarios}
    parts = []
    for years in (3, 4, 5):
        s = by_year[years]
        parts.append(f"{years} 年{'可行' if s.credits_feasible else '不可行'}（每学期 {s.per_term:.1f} 分）")
    text = "；".join(parts) + "。"
    if non_credit:
        text += "毕业是三条件与逻辑，非学分卡点：" + "；".join(non_credit[:3]) + "。"
    if recommended:
        text += f"最早可按 {recommended} 年规划毕业。"
    else:
        text += "按当前进度，3–5 年内均无法同时满足学分与开课约束，需要人工介入。"
    return text
