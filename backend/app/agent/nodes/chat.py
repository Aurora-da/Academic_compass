from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_llm
from app.agent.prompts.system import CHAT_PROMPT, SYSTEM_PROMPT
from app.agent.state import AgentState
from app.services.rag.knowledge import retrieve


def _offline_answer(query: str, contexts: list[dict], guard_reason: str | None) -> str:
    if guard_reason:
        return (
            f"我还不能读取你的完整学业数据：{guard_reason}。\n\n"
            "你可以：\n"
            "1. 在「导入」页上传成绩单 PDF / Excel；\n"
            "2. 使用浏览器插件同步教务系统页面；\n"
            "3. 导入完成后重新问我“我还差多少学分”。"
        )
    if not contexts:
        return (
            "培养方案未明确说明这一点，建议咨询教学秘书。\n\n"
            "我目前的知识库覆盖：毕业条件、七模块学分结构、综合素质选修、第二课堂、"
            "指导性学期、先修关系与审核口径。你可以换个问法，或直接问“我还差多少学分”。\n\n"
            "> 预演，以教务处终审为准。"
        )
    lines = ["根据培养方案与学业规章："]
    for item in contexts[:3]:
        content = item["content"].replace("\n", " ").strip()
        if len(content) > 260:
            content = content[:260].rstrip() + "…"
        lines.append(f"\n**{item['section']}**\n\n{content}")
    lines.append("\n\n> 依据：2024 版计算机科学与技术（拔尖班）培养方案；预演，以教务处终审为准。")
    return "\n".join(lines)


async def chat_node(state: AgentState) -> dict:
    query = state.get("query") or ""
    guard_reason = state.get("guard_reason")
    contexts = retrieve(query, k=4) if query and not guard_reason else []

    llm = get_llm()
    answer = None
    if llm is not None and query and not guard_reason:
        try:
            context_text = "\n\n".join(
                f"【{c['section']}】{c['content']}" for c in contexts
            )
            response = await llm.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(
                        content=CHAT_PROMPT.format(context=context_text or "（无相关资料）", question=query)
                    ),
                ]
            )
            answer = str(response.content).strip()
        except Exception:
            answer = None
    if not answer:
        answer = _offline_answer(query, contexts, guard_reason)

    return {
        "chat": {
            "answer": answer,
            "sources": [
                {"section": c["section"], "source": c["source"], "score": c["score"]}
                for c in contexts
            ],
            "mode": "llm" if llm is not None and answer and not guard_reason else "offline",
        }
    }
