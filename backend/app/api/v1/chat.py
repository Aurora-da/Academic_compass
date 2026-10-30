from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.agent.graph import NODE_LABELS
from app.api.deps import get_current_student
from app.models import Student
from app.schemas.api import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _config(student: Student, session_id: str) -> dict:
    return {"configurable": {"thread_id": f"{student.id}:{session_id}"}, "recursion_limit": 40}


def _summary(audit: dict | None) -> dict | None:
    if not audit:
        return None
    return {
        "earned": audit["summary"]["earned"],
        "require": audit["summary"]["require"],
        "gap": audit["summary"]["gap"],
        "studying": audit["summary"]["studying"],
        "percent": audit["summary"]["percent"],
        "graduation": audit["graduation"],
        "risks": audit.get("risks", [])[:4],
        "modules": [
            {
                "id": m["id"],
                "name": m["name"],
                "require": m["require"],
                "earned": m["earned"],
                "gap": m["gap"],
                "ok": m["ok"],
                "status": m["status"],
            }
            for m in audit.get("modules", [])
        ],
    }


def _done_payload(values: dict, session_id: str) -> dict:
    rec = values.get("recommendation")
    return {
        "type": "done",
        "session_id": session_id,
        "intent": values.get("intent"),
        "verification": values.get("verification"),
        "simulation": values.get("simulation"),
        "audit_summary": _summary(values.get("audit")),
        "recommendation_summary": (
            {
                "semester": rec.get("semester"),
                "plans": [
                    {
                        "key": p["key"],
                        "name": p["name"],
                        "total_credits": p["total_credits"],
                        "total_with_locked": p.get("total_with_locked"),
                        "course_count": len(p["courses"]),
                    }
                    for p in rec.get("plans", [])
                ],
                "feasibility": rec.get("feasibility", {}).get("summary"),
            }
            if rec
            else None
        ),
        "mode": "online" if values.get("verification") else "offline",
    }


@router.post("")
async def chat(
    payload: ChatRequest,
    request: Request,
    student: Student = Depends(get_current_student),
):
    graph = request.app.state.graph
    session_id = payload.session_id or uuid.uuid4().hex
    config = _config(student, session_id)
    if payload.resume:
        graph_input: dict | Command = Command(resume=payload.resume)
    else:
        graph_input = {
            "messages": [HumanMessage(content=payload.message)],
            "student_id": str(student.id),
            "session_id": session_id,
            "semester": payload.semester or student.current_term,
        }
    values = await graph.ainvoke(graph_input, config)
    return {
        "session_id": session_id,
        "intent": values.get("intent"),
        "answer": values.get("answer"),
        "verification": values.get("verification"),
        "simulation": values.get("simulation"),
        "audit": values.get("audit"),
        "recommendation": values.get("recommendation"),
        "pending_confirm": values.get("pending_confirm"),
    }


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    student: Student = Depends(get_current_student),
):
    graph = request.app.state.graph
    session_id = payload.session_id or uuid.uuid4().hex
    config = _config(student, session_id)
    if payload.resume:
        graph_input: dict | Command = Command(resume=payload.resume)
    else:
        graph_input = {
            "messages": [HumanMessage(content=payload.message)],
            "student_id": str(student.id),
            "session_id": session_id,
            "semester": payload.semester or student.current_term,
        }

    async def event_stream():
        yield _sse({"type": "meta", "session_id": session_id, "thread_id": config["configurable"]["thread_id"]})
        try:
            async for event in graph.astream_events(graph_input, config, version="v2"):
                name = event.get("name")
                kind = event.get("event")
                if name in NODE_LABELS and kind in {"on_chain_start", "on_chain_end"}:
                    yield _sse(
                        {
                            "type": "node",
                            "node": name,
                            "label": NODE_LABELS[name],
                            "status": "running" if kind == "on_chain_start" else "done",
                        }
                    )
            state = await graph.aget_state(config)
            values = state.values
            answer = values.get("answer") or ""
            for i in range(0, len(answer), 18):
                yield _sse({"type": "token", "content": answer[i : i + 18]})
                await asyncio.sleep(0.006)
            yield _sse({**_done_payload(values, session_id), "answer": answer})
            yield "data: [DONE]\n\n"
        except Exception as exc:  # pragma: no cover - 流式接口的兜底
            yield _sse({"type": "error", "message": f"生成失败：{exc}"})
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def history(
    session_id: str,
    request: Request,
    student: Student = Depends(get_current_student),
):
    graph = request.app.state.graph
    state = await graph.aget_state(_config(student, session_id))
    messages = state.values.get("messages") or []
    rows = []
    for message in messages:
        role = getattr(message, "type", "")
        content = getattr(message, "content", "")
        if isinstance(content, list):
            content = "".join(str(part) for part in content)
        rows.append({"role": "user" if role == "human" else "assistant", "content": str(content)})
    return {"session_id": session_id, "messages": rows}
