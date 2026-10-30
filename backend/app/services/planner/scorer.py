from __future__ import annotations

from app.services.audit.evaluator import AuditReport
from app.services.plan.compiler import RuntimePlan
from app.services.plan.terms import remaining_terms
from app.services.planner.filter import Candidate


def _node_gaps(report: AuditReport) -> dict[str, dict]:
    gaps: dict[str, dict] = {}

    def walk(node):
        gaps[node.key] = node
        for child in node.children:
            walk(child)

    for root in report.modules:
        walk(root)
    return gaps


def score_candidates(
    candidates: list[Candidate],
    plan: RuntimePlan,
    report: AuditReport,
    prerequisites: list[dict],
    *,
    current_term: str,
    entry_year: int,
    target_term: str,
    direction: str | None = None,
) -> list[Candidate]:
    nodes = _node_gaps(report)
    missing_codes = {
        c["code"]
        for root in report.modules
        for c in root.missing
    }
    dependent_count: dict[str, int] = {}
    for p in prerequisites:
        prereq_code = p.get("prereq_code") or p.get("prereq")
        if prereq_code in missing_codes:
            dependent_count[prereq_code] = dependent_count.get(prereq_code, 0) + 1

    terms_left = max(
        1,
        len(remaining_terms(current_term, target_term, entry_year, include_current=True)),
    )

    for cand in candidates:
        node = nodes.get(cand.module) or next(
            (n for key, n in nodes.items() if cand.module.startswith(key + "-")), None
        )
        gap = node.gap if node else 0.0
        urgency = min(30.0, (gap / terms_left) * 3.0)
        required = 40.0 if cand.nature == "必修" else 18.0
        key_path = min(15.0, dependent_count.get(cand.code, 0) * 6.0)
        structure = 12.0 if cand.required_child else 0.0
        direction_bonus = 8.0 if (direction and cand.module.startswith(direction)) else 0.0
        load = -4.0 if (cand.assessment == "考试" and cand.credit >= 3.5) else 0.0
        score = required + urgency + key_path + structure + direction_bonus + load
        cand.score = round(max(0.0, min(100.0, score)), 1)
        cand.score_breakdown = {
            "required": required,
            "urgency": urgency,
            "key_path": key_path,
            "structure": structure,
            "direction": direction_bonus,
            "load": load,
        }

        reasons: list[str] = []
        if gap <= 0:
            reasons.append("该模块已达标，作为兴趣或负载均衡选修，不增加毕业缺口")
        elif node:
            reasons.append(f"{node.name}缺口 {node.gap:.1f} 分，按剩余学期均摊每学期需 ≥ {gap / terms_left:.1f}")
        if cand.required_child:
            reasons.append("属于模块1（必选），优先补结构缺口，否则总量达标也不合格")
        if cand.module.startswith("M5"):
            reasons.append("专业方向课，同时影响 2 学分创新实践的选题")
        if dependent_count.get(cand.code):
            reasons.append(f"是 {dependent_count[cand.code]} 门未完成课程的先修课，属于关键路径")
        if cand.offering:
            reasons.append(
                f"本学期 {cand.offering.get('teacher', '')} {cand.offering.get('class_id', '')} 班，"
                f"余量 {cand.offering.get('capacity', 0) - cand.offering.get('enrolled', 0)}"
            )
        if cand.conflicts:
            reasons.append("存在时间冲突：" + "；".join(cand.conflicts))

        consequences: list[str] = []
        if cand.future_semesters:
            consequences.append(f"后续可修读学期：{', '.join(cand.future_semesters)}")
        if cand.assessment == "考试" and cand.credit >= 3.5:
            consequences.append("考试课且学分较重，建议不要与另外两门硬课同学期")
        if cand.difficulty:
            consequences.append(
                f"近 {cand.difficulty.get('years', 3)} 年平均分 {cand.difficulty.get('avg_score')}，"
                f"挂科率 {cand.difficulty.get('fail_rate', 0) * 100:.0f}%"
            )
        cand.reasons = reasons
        cand.consequences = consequences

    return sorted(candidates, key=lambda c: (-c.score, c.code))
