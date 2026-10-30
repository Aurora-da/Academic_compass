from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    student_id: str
    session_id: str
    semester: str | None
    query: str
    intent: Literal["plan", "audit", "recommend", "import", "chat"]
    confidence: float
    profile: dict | None
    plan: dict | None
    audit: dict | None
    offerings: list | None
    recommendation: dict | None
    pending_confirm: dict | None
    confirmation: dict | None
    verification: dict | None
    verification_attempts: int
    recompose_count: int
    template_mode: bool
    chat: dict | None
    simulate_course: str | None
    simulation: dict | None
    answer: str | None
    errors: list[str]
    guard_ok: bool
    guard_reason: str | None


class AuditGraphState(TypedDict, total=False):
    student_id: str
    semester: str
    plan: Any
    student: dict
    enrollments: list[dict]
    offerings: list[dict]
    records: list[dict]
    entry_year: int
    current_term: str
    target_graduation_term: str
    direction: str | None
    matched: list[dict]
    assignments: dict[str, str]
    report: dict
    checks: list[dict]
    errors: list[str]
