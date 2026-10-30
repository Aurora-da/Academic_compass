from __future__ import annotations

import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_llm
from app.agent.prompts.extract import INTENT_PROMPT, IntentResult
from app.agent.prompts.system import SYSTEM_PROMPT
from app.agent.state import AgentState

SEMESTER_RE = re.compile(r"20\d{2}-20\d{2}-[12]")
COURSE_CODE_RE = re.compile(r"\bB\d{6}\b", re.IGNORECASE)
DIRECTIONS = {"人工智能": "M5-1", "嵌入式": "M5-2", "嵌入式系统": "M5-2", "算网融合": "M5-3", "算力网络": "M5-3"}


def rule_intent(query: str) -> IntentResult:
    q = query.strip()
    semester = SEMESTER_RE.search(q)
    code = COURSE_CODE_RE.search(q)
    direction = next((v for k, v in DIRECTIONS.items() if k in q), None)
    # 课程名交给 audit 节点按培养方案课程表解析，避免正则把“如果我”当成课程
    simulate = None

    if any(k in q for k in ("该选", "选什么", "选课建议", "怎么选", "推荐", "课表", "排课", "选哪门")):
        intent = "recommend"
    elif any(
        k in q
        for k in ("差多少", "缺口", "够不够", "还差", "审核", "挂科", "挂了", "第二课堂", "进度", "能不能毕业", "能毕业吗", "学业情况")
    ):
        intent = "audit"
    elif any(
        k in q
        for k in (
            "培养方案", "模块", "要求", "结构", "课程设置", "有哪些课", "指导性学期",
            "考核方式", "学分结构", "毕业条件", "多少学分", "学制",
        )
    ):
        intent = "plan"
    else:
        intent = "chat"

    return IntentResult(
        intent=intent,
        semester=semester.group(0) if semester else None,
        course_code=code.group(0).upper() if code else None,
        direction=direction,
        simulate_course=simulate if intent == "audit" else None,
        confidence=0.72 if intent != "chat" else 0.6,
    )


async def intake(state: AgentState) -> dict:
    messages = state.get("messages") or []
    query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            query = str(msg.content)
            break
    query = query or state.get("query") or ""

    result: IntentResult | None = None
    llm = get_llm()
    if llm is not None and query:
        try:
            structured = llm.with_structured_output(IntentResult)
            result = await structured.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT + "\n\n" + INTENT_PROMPT),
                    HumanMessage(content=query),
                ]
            )
        except Exception:
            result = None
    if result is None:
        result = rule_intent(query)

    intent = result.intent if result.intent in {"plan", "audit", "recommend", "chat"} else "chat"
    direction = result.direction
    if direction and direction.startswith("M5"):
        pass
    elif direction:
        direction = None
    if result.direction in DIRECTIONS:
        direction = DIRECTIONS[result.direction]

    update = {
        "query": query,
        "intent": intent,
        "semester": result.semester or state.get("semester"),
        "confidence": result.confidence,
        "simulate_course": result.simulate_course,
        "direction": direction,
        "errors": [],
        "verification_attempts": 0,
        "recompose_count": 0,
        "template_mode": False,
    }
    return update
