from __future__ import annotations

import mimetypes
import time

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.graph import build_graph, graph_mermaid
from app.api.v1 import admin, audit, auth, chat, documents, plans, recommend, students
from app.core.config import settings
from app.core.db import SessionLocal, create_all
from app.core.logging import logger, setup_logging
from app.seed import seed_all

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("font/woff2", ".woff2")

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.debug)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    await create_all()
    async with SessionLocal() as session:
        await seed_all(session)
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_path) as saver:
        app.state.graph = build_graph(saver)
        logger.info("LangGraph compiled (checkpointer=AsyncSqliteSaver)")
        logger.info("LLM: %s", f"online · {settings.llm_model}" if settings.llm_enabled else "offline template mode")
        logger.info("Server ready: http://%s:%s", settings.host, settings.port)
        yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="学分账本 + 选课参谋 + 毕业审核预演。数字由 Python 约束引擎计算，LLM 只负责理解与表达。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    students.router,
    plans.router,
    audit.router,
    recommend.router,
    documents.router,
    chat.router,
    admin.router,
):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "uptime": round(time.time() - START_TIME, 1),
        "version": settings.app_version,
        "engine_version": settings.engine_version,
        "llm": "online" if settings.llm_enabled else "offline",
    }


@app.get("/api/v1/meta")
async def meta():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "engine_version": settings.engine_version,
        "current_term": settings.current_term,
        "llm_enabled": settings.llm_enabled,
        "llm_model": settings.llm_model if settings.llm_enabled else None,
        "llm_base_url": settings.llm_base_url if settings.llm_enabled else None,
        "graph": graph_mermaid(),
        "disclaimer": "预演，以教务处终审为准",
    }


DIST = Path(settings.frontend_dist)
for _static_dir in ("assets", "fonts", "images"):
    _path = DIST / _static_dir
    if _path.exists():
        app.mount(f"/{_static_dir}", StaticFiles(directory=str(_path)), name=_static_dir)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa(full_path: str, request: Request):
    if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {
            "app": settings.app_name,
            "message": "前端尚未构建：请在 frontend/ 目录执行 pnpm install && pnpm build，或使用 pnpm dev 开发模式。",
            "docs": "/docs",
            "api": settings.api_prefix,
        }
    )
