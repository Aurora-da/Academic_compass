from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.nodes.audit_node import audit_node
from app.agent.nodes.chat import chat_node
from app.agent.nodes.compose import compose
from app.agent.nodes.confirm import confirm_mapping
from app.agent.nodes.guard import guard
from app.agent.nodes.intake import intake
from app.agent.nodes.plan_node import plan_node
from app.agent.nodes.recommend_node import recommend_node
from app.agent.nodes.recompose import recompose
from app.agent.nodes.route import need_confirm, route, verify_ok
from app.agent.nodes.verify import verify
from app.agent.state import AgentState

NODE_LABELS = {
    "intake": "理解问题",
    "guard": "检查数据",
    "plan": "查询培养方案",
    "audit": "计算学分",
    "recommend": "生成选课建议",
    "verify": "校验数字",
    "recompose": "修正结果",
    "compose": "组织回答",
    "chat": "检索规章",
    "confirm_mapping": "等待确认",
}


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("intake", intake)
    graph.add_node("guard", guard)
    graph.add_node("plan", plan_node)
    graph.add_node("audit", audit_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("chat", chat_node)
    graph.add_node("verify", verify)
    graph.add_node("recompose", recompose)
    graph.add_node("confirm_mapping", confirm_mapping)
    graph.add_node("compose", compose)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "guard")
    graph.add_conditional_edges(
        "guard",
        route,
        {"plan": "plan", "audit": "audit", "recommend": "recommend", "chat": "chat"},
    )
    graph.add_conditional_edges(
        "audit", need_confirm, {"confirm": "confirm_mapping", "verify": "verify"}
    )
    graph.add_edge("confirm_mapping", "audit")  # 回边：确认后重算
    graph.add_edge("recommend", "verify")
    graph.add_conditional_edges("verify", verify_ok, {"ok": "compose", "fail": "recompose"})
    graph.add_edge("recompose", "verify")  # 重写后复检，最多 1 次
    graph.add_edge("plan", "compose")
    graph.add_edge("chat", "compose")
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer)


def graph_mermaid() -> str:
    return """graph TD
    START --> intake --> guard
    guard -->|plan| plan
    guard -->|audit| audit
    guard -->|recommend| recommend
    guard -->|chat| chat
    audit -->|低置信度| confirm_mapping
    confirm_mapping --> audit
    audit --> verify
    recommend --> verify
    verify -->|ok| compose
    verify -->|fail| recompose
    recompose --> verify
    plan --> compose
    chat --> compose
    compose --> END"""
