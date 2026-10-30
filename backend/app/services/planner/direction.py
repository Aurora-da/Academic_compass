from __future__ import annotations

from app.services.audit.evaluator import AuditReport
from app.services.plan.compiler import RuntimePlan
from app.services.planner.filter import expand_slots


def compare_directions(
    plan: RuntimePlan,
    report: AuditReport,
    offerings: list[dict],
    *,
    current_term: str,
    locked_courses: list[dict] | None = None,
) -> dict:
    locked_slots: set[str] = set()
    for c in locked_courses or []:
        locked_slots |= expand_slots(c.get("slots") or [])

    module_key = report.direction.get("module")
    node = plan.node(module_key) if module_key else None
    if node is None:
        return {"options": [], "recommended": None, "note": "培养方案未配置方向课组"}

    passed = {c["code"] for c in report.passed_courses}
    offering_map: dict[str, list[dict]] = {}
    for o in offerings:
        offering_map.setdefault(o["course_code"], []).append(o)

    options = []
    for child in node.children:
        courses = child.all_courses()
        earned = sum(c.credit for c in courses if c.code in passed)
        remaining = [c for c in courses if c.code not in passed]
        course_rows = []
        conflicts = 0
        for c in remaining:
            offs = [o for o in offering_map.get(c.code, []) if o["semester"] >= current_term]
            offs.sort(key=lambda o: o["semester"])
            slots = offs[0].get("time_slots") if offs else []
            has_conflict = bool(expand_slots(slots) & locked_slots)
            if has_conflict:
                conflicts += 1
            course_rows.append(
                {
                    "code": c.code,
                    "name": c.name,
                    "credit": c.credit,
                    "plan_term": c.plan_term,
                    "earned": c.code in passed,
                    "next_offering": offs[0]["semester"] if offs else None,
                    "conflict": has_conflict,
                }
            )
        total = sum(c.credit for c in courses) or 1.0
        progress = round(earned / total, 3)
        # 衔接度：已修课程占方向的比例 + 剩余课程是否都在未来有开课
        availability = sum(1 for r in course_rows if r["next_offering"]) / max(1, len(course_rows))
        score = round(progress * 60 + availability * 30 - conflicts * 8, 1)
        option = {
            "id": child.key,
            "name": child.name,
            "earned": round(earned, 1),
            "require": child.require,
            "progress": progress,
            "remaining": course_rows,
            "conflicts": conflicts,
            "score": score,
            "recommended": False,
        }
        options.append(option)

    options.sort(key=lambda x: (-x["score"], -x["earned"]))
    if options:
        options[0]["recommended"] = True
        options[0]["reason"] = (
            f"已修 {options[0]['earned']:.1f}/{options[0]['require']:.0f}，"
            f"剩余 {len(options[0]['remaining'])} 门，衔接度最高"
        )
        for other in options[1:]:
            if other["conflicts"]:
                other["reason"] = f"有 {other['conflicts']} 门与已选课程时间冲突，负载偏重"
            elif other["earned"] == 0:
                other["reason"] = "尚未开始，需从方向第一门课修起"
            else:
                other["reason"] = f"已修 {other['earned']:.1f}/{other['require']:.0f}，剩余课程开课时间需核对"
    return {
        "module": node.key,
        "module_name": node.name,
        "locked": report.direction.get("locked", False),
        "selected": report.direction.get("selected"),
        "selected_name": report.direction.get("selected_name"),
        "options": options,
        "note": "方向一旦锁定即写入 plan_overlay，后续审核按锁定方向计算，并影响 2 学分创新实践内容",
    }
