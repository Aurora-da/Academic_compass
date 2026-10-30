from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.llm import get_llm
from app.agent.prompts.system import SYSTEM_PROMPT
from app.agent.state import AgentState

DISCLAIMER = "> 预演，以教务处终审为准。数字由约束引擎计算，模型只负责解释。"


def _f(value: float) -> str:
    return f"{value:.1f}"


def _module_status(module: dict) -> str:
    if module["ok"]:
        if module["over"] > 0:
            return f"✅ 达标（超修 {_f(module['over'])}）"
        return "✅ 达标"
    if module["mode"] == "any_of":
        return f"⚠️ 缺 {_f(module['gap'])}（方向未修完）"
    if module["own_ok"] and not module["child_ok"]:
        return "⚠️ 结构未达标"
    if not module["own_ok"] and not module["child_ok"]:
        return f"⚠️ 缺 {_f(module['gap'])}（结构也未达标）"
    return f"⚠️ 缺 {_f(module['gap'])}"


def _second_classroom_line(audit: dict) -> tuple[str, list[str]]:
    sc = audit.get("graduation", {}).get("second_classroom", {})
    items = sc.get("items", [])
    by_cat: dict[str, list[dict]] = {}
    for item in items:
        by_cat.setdefault(item["category"], []).append(item)
    parts = []
    blockers = []
    for cat, rows in by_cat.items():
        unmet = [r for r in rows if r["status"] == "unmet"]
        missing = [r for r in rows if r["status"] == "missing"]
        if unmet:
            msg = unmet[0]["message"]
            parts.append(f"{cat} ⚠️（{msg}）")
            blockers.append(f"{cat}：{msg}")
        elif missing:
            parts.append(f"{cat} ⬜ 待确认")
        else:
            latest = rows[-1]
            parts.append(f"{cat} ✅（{latest['message']}）")
    return " · ".join(parts) if parts else "未配置第二课堂要求", blockers


def _structure_notes(audit: dict) -> list[str]:
    notes = []

    def walk(nodes):
        for node in nodes:
            if node["mode"] != "any_of" and not node["child_ok"]:
                bad = [c for c in node["children"] if c["require"] > 0 and not c["ok"]]
                if bad:
                    child = max(bad, key=lambda c: c["gap"])
                    if node["own_ok"]:
                        notes.append(
                            f"{node['name']}总量已达标（{_f(node['earned'])}/{_f(node['require'])}），"
                            f"但「{child['name']}」还差 {_f(child['gap'])} 学分——总量达标不等于结构达标"
                        )
                    elif child["gap"] > node["gap"]:
                        notes.append(
                            f"{node['name']}总量差 {_f(node['gap'])} 分，但「{child['name']}」差 {_f(child['gap'])} 分"
                            f"——补课优先补{child['name']}"
                        )
            walk(node["children"])

    walk(audit.get("modules", []))
    return notes


def _render_audit(audit: dict, simulation: dict | None) -> str:
    summary = audit["summary"]
    grad = audit["graduation"]
    student = audit.get("student") or {}
    lines = [
        f"你目前累计已获 **{_f(summary['earned'])}** 学分，距离 {_f(summary['require'])} 还差 "
        f"**{_f(summary['gap'])}** 分（另有 {_f(summary['studying'])} 学分在修）。",
        "",
        "**毕业三条件**",
        f"- 学分：{_f(grad['credits']['earned'])}/{_f(grad['credits']['require'])} "
        f"{'✅' if grad['credits']['ok'] else '✗'}",
    ]
    sc_line, sc_blockers = _second_classroom_line(audit)
    sc_ok = grad.get("second_classroom", {}).get("ok")
    sc_mark = "✅" if sc_ok is True else ("⬜" if sc_ok is None else "✗")
    lines.append(f"- 第二课堂 {sc_mark}：{sc_line}")
    thesis = grad.get("thesis", {})
    lines.append(f"- 毕业答辩：{thesis.get('label', '未开始')} {'✅' if thesis.get('ok') else '✗'}")

    lines += ["", "**模块进度**", "", "| 模块 | 要求 | 已获 | 缺口 | 状态 |", "|---|---|---|---|---|"]
    for module in audit["modules"]:
        name = module["name"]
        if module.get("direction") or module.get("mode") == "any_of":
            if module.get("picked_name"):
                name += f"（{module['picked_name']}）"
        lines.append(
            f"| {name} | {_f(module['require'])} | {_f(module['earned'])} | "
            f"{_f(module['gap'])} | {_module_status(module)} |"
        )
    if summary["over"] > 0:
        lines.append("")
        lines.append(
            f"> 总学分按模块封顶：七个模块已获之和为 "
            f"{_f(summary['earned'] + summary['over'])}，其中超修 {_f(summary['over'])} 不计入 "
            f"{_f(summary['require'])} 的分子。"
        )

    structure = _structure_notes(audit)
    if structure:
        lines += ["", "**结构提示**"]
        lines += [f"- {note}" for note in structure]

    if audit.get("risks"):
        lines += ["", "**风险**"]
        for risk in audit["risks"][:6]:
            mark = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(risk["level"], "•")
            lines.append(f"- {mark} {risk['msg']}")

    # 本学期待完成：只取当前指导性学期或已在修的课程
    program_term = audit.get("program_term")
    pending = []
    for module in audit["modules"]:
        for miss in module["missing"]:
            if not (miss["nature"] == "必修" or miss.get("required_child") or miss["status"] == "studying"):
                continue
            if miss["status"] == "studying" or (program_term and miss["plan_term"] == program_term):
                pending.append(miss)
    if pending:
        seen = set()
        lines += ["", "**本学期待完成**"]
        for miss in pending[:6]:
            if miss["code"] in seen:
                continue
            seen.add(miss["code"])
            status = "在修" if miss["status"] == "studying" else "待修"
            lines.append(
                f"- [{status}] {miss['name']}（{_f(miss['credit'])} 学分，"
                f"指导性学期 {miss['plan_term']}，{miss['assessment']}）"
            )

    if simulation:
        lines += ["", "**情景模拟**", f"- {simulation['verdict']}"]
        for change in simulation.get("module_changes", [])[:3]:
            lines.append(
                f"- {change['name']}：缺口 {_f(change['gap_before'])} → {_f(change['gap_after'])}"
            )

    lines += ["", "**下一步**"]
    actions = []
    if not grad["credits"]["ok"]:
        actions.append("按模块缺口补课，优先补“结构未达标”的必选子模块")
    if sc_blockers:
        actions.append("登记第二课堂：截至当前仍有未达标项")
    direction = audit.get("direction") or {}
    if direction.get("options") and not direction.get("locked"):
        actions.append("锁定专业方向（三选一，同时决定创新实践选题）")
    if not thesis.get("ok"):
        actions.append("关注毕业设计（论文）开题与答辩时间")
    for action in actions[:3]:
        lines.append(f"- {action}")
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def _render_recommendation(rec: dict, query: str) -> str:
    plans = rec.get("plans") or []
    tier = "balanced"
    for key, words in (("steady", ("稳妥", "保底")), ("sprint", ("冲刺", "满负荷")), ("balanced", ("均衡",))):
        if any(w in query for w in words):
            tier = key
            break
    selected = next((p for p in plans if p["key"] == tier), plans[0] if plans else None)
    summary = rec.get("summary") or {}
    lines = [
        f"按 {rec['semester']} 的开课计划，你当前已获 {_f(summary.get('earned', 0))} 学分、"
        f"缺口 {_f(summary.get('gap', 0))}，另有 {_f(rec.get('current_credits', 0))} 学分在修。",
    ]

    direction = rec.get("direction_comparison") or {}
    if direction.get("options"):
        best = direction["options"][0]
        lines += ["", f"**方向决策：建议 {best['name']}**", f"{best.get('reason', '')}"]
        for opt in direction["options"][1:]:
            lines.append(f"- {opt['name']}：{opt.get('reason', '')}")

    if selected:
        lines += [
            "",
            f"**{selected['name']}方案（新增 {_f(selected['total_credits'])} 学分）**",
        ]
        for course in selected["courses"]:
            lines.append(
                f"- **{course['name']}**（{course['code']}，{_f(course['credit'])} 学分，"
                f"{course['nature']}，{course['module_name']}）"
            )
            for reason in course.get("reasons", [])[:2]:
                lines.append(f"  - 为什么现在选：{reason}")
            for consequence in course.get("consequences", [])[:2]:
                lines.append(f"  - 提示：{consequence}")
            if course.get("conflicts"):
                lines.append("  - 冲突：" + "；".join(course["conflicts"]))
        if selected.get("warnings"):
            lines.append("")
            lines += [f"> {w}" for w in selected["warnings"]]

    lines += ["", "**三档对比**", "", "| 方案 | 新增学分 | 含在修 | 课程数 | 说明 |", "|---|---|---|---|---|"]
    for plan in plans:
        lines.append(
            f"| {plan['name']} | {_f(plan['total_credits'])} | {_f(plan.get('total_with_locked', plan['total_credits']))} | "
            f"{len(plan['courses'])} | {plan['desc']} |"
        )

    feasibility = rec.get("feasibility") or {}
    if feasibility.get("scenarios"):
        lines += ["", "**毕业可行性（三情景）**"]
        for scenario in feasibility["scenarios"]:
            mark = "✅" if scenario["credits_feasible"] else "✗"
            lines.append(
                f"- {scenario['label']} {mark}：剩余 {scenario['remaining_terms']} 个学期，"
                f"每学期约 {_f(scenario['per_term'])} 学分"
            )
        lines.append("")
        lines.append(feasibility.get("summary", ""))
        blockers = feasibility.get("non_credit_blockers") or []
        if blockers:
            lines.append("")
            lines.append("非学分卡点：" + "；".join(blockers[:3]))

    blocked = [b for b in rec.get("blocked", []) if b["status"] == "prereq_missing"][:3]
    if blocked:
        lines += ["", "**先修未满足，暂不可选**"]
        for b in blocked:
            lines.append(f"- {b['name']}：先修 {', '.join(b['prereq_missing'])} 未通过")

    lines += ["", "**说明**", "推荐以当学期开课计划为硬约束；培养方案指导性学期只作先验。", DISCLAIMER]
    return "\n".join(lines)


def _render_plan(plan: dict) -> str:
    duration = plan.get("duration") or {}
    lines = [
        f"**{plan['name']}**",
        "",
        f"- 总学分：{_f(plan['total_credits'])}；标准学制 {duration.get('standard', 4)} 年，"
        f"弹性 {duration.get('min', 3)}–{duration.get('max', 6)} 年",
        f"- 授予学位：{plan.get('degree', '工学学士')}；方案状态：{plan.get('status')}",
        f"- 课程总数：{plan.get('course_count')} 门",
        "",
        "**七模块要求**",
        "",
        "| 模块 | 要求学分 | 模式 | 子项 |",
        "|---|---|---|---|",
    ]
    mode_label = {"all_of": "全部必修", "any_of": "任选其一", "free": "自由选修"}
    for module in plan["modules"]:
        lines.append(
            f"| {module['name']} | {_f(module['require'])} | {mode_label.get(module['mode'], module['mode'])} | "
            f"{len(module.get('children') or [])} 个子项 / {len(module.get('courses') or [])} 门课 |"
        )
    lines += ["", "**毕业条件**"]
    for cond in plan.get("graduation_conditions", []):
        lines.append(f"- {cond.get('label', cond.get('type'))}")
    if plan.get("second_classroom"):
        lines += ["", "**第二课堂（周期性非学分条件）**"]
        for req in plan["second_classroom"]:
            lines.append(f"- {req['category']}：{req.get('label', '')}")

    focus = plan.get("focus_course")
    if focus:
        lines += [
            "",
            f"**课程：{focus['name']}（{focus['code']}）**",
            f"- {_f(focus['credit'])} 学分，指导性学期 {focus['plan_term']}，"
            f"{focus['assessment']}，{focus['nature']}，所属 {focus['module']}",
        ]
        if focus.get("prerequisites"):
            lines.append(
                "- 先修/同修：" + "、".join(f"{p['code']}（{p['type']}）" for p in focus["prerequisites"])
            )
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


async def _llm_intro(audit: dict | None, rec: dict | None) -> str | None:
    """可选的共情开场白：禁止数字，出现数字则丢弃。"""
    llm = get_llm()
    if llm is None:
        return None
    facts = {}
    if audit:
        facts["earned"] = audit["summary"]["earned"]
        facts["gap"] = audit["summary"]["gap"]
        facts["risk_types"] = [r["type"] for r in audit.get("risks", [])]
    if rec:
        facts["feasibility"] = rec.get("feasibility", {}).get("summary", "")
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "根据以下事实，用一两句话给出一段温和、具体的开场白。"
                        "不要出现任何阿拉伯数字，不要列清单，不要下结论。事实："
                        f"{facts}"
                    )
                ),
            ]
        )
        text = str(response.content).strip()
        if text and not any(ch.isdigit() for ch in text):
            return text
    except Exception:
        return None
    return None


async def compose(state: AgentState) -> dict:
    intent = state.get("intent", "chat")
    query = state.get("query") or ""
    answer: str

    if intent == "audit" and state.get("audit"):
        answer = _render_audit(state["audit"], state.get("simulation"))
    elif intent == "recommend" and state.get("recommendation"):
        answer = _render_recommendation(state["recommendation"], query)
    elif intent == "plan" and state.get("plan"):
        answer = _render_plan(state["plan"])
    elif state.get("chat"):
        answer = state["chat"]["answer"]
    elif state.get("guard_reason"):
        answer = f"我还不能读取你的完整学业数据：{state['guard_reason']}。请先导入成绩单后重试。"
    else:
        answer = "我暂时没有足够数据回答这个问题。你可以问“我还差多少学分”或“这学期该选什么”。"

    intro = await _llm_intro(state.get("audit"), state.get("recommendation"))
    if intro and intent in {"audit", "recommend"}:
        answer = intro + "\n\n" + answer

    return {"answer": answer, "messages": [AIMessage(content=answer)]}
