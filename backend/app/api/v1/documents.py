from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student
from app.core.db import get_db
from app.models import ImportJob, Student
from app.schemas.api import DocumentReviewRequest, PluginImportRequest
from app.services.ingestion.documents import (
    ImportError_,
    apply_import,
    create_import_job,
    list_import_jobs,
    parse_upload,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_jobs(student: Student = Depends(get_current_student), db: AsyncSession = Depends(get_db)):
    jobs = await list_import_jobs(db, student.id)
    return [
        {
            "id": j.id,
            "filename": j.filename,
            "source": j.source,
            "status": j.status,
            "summary": (j.result_json or {}).get("summary"),
            "applied": (j.result_json or {}).get("applied"),
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


@router.post("")
async def upload(
    file: UploadFile = File(...),
    source: str = Form(default="file"),
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件超过 20MB")
    try:
        rows = await parse_upload(file.filename or "upload", content, student.current_term)
    except ImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = await create_import_job(
        db, student, rows, filename=file.filename or "upload", source=source
    )
    return {
        "job_id": job.id,
        "filename": job.filename,
        "rows": job.result_json["rows"],
        "summary": job.result_json["summary"],
    }


@router.post("/plugin")
async def plugin_import(
    payload: PluginImportRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    if not payload.courses:
        raise HTTPException(status_code=400, detail="courses 不能为空")
    raw = {
        "courses": [c.model_dump() for c in payload.courses],
    }
    from app.services.ingestion.documents import _rows_from_json

    rows = [r for r in _rows_from_json(raw, student.current_term)]
    job = await create_import_job(
        db, student, rows, filename=f"plugin:{payload.source}", source="plugin"
    )
    if payload.apply:
        items = []
        for row in job.result_json["rows"]:
            if row.get("course_code"):
                items.append(
                    {
                        "index": row["index"],
                        "course_code": row["course_code"],
                        "status": row["raw_status"],
                        "score": row["raw_score"],
                        "term": row["raw_term"],
                        "credit": row["raw_credit"],
                    }
                )
        result = await apply_import(db, student, job, items)
        return {"job_id": job.id, "applied": result, "rows": job.result_json["rows"]}
    return {"job_id": job.id, "rows": job.result_json["rows"], "summary": job.result_json["summary"]}


@router.get("/{job_id}")
async def get_job(
    job_id: int, student: Student = Depends(get_current_student), db: AsyncSession = Depends(get_db)
):
    job = await db.get(ImportJob, job_id)
    if job is None or job.student_id != student.id:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return {
        "id": job.id,
        "filename": job.filename,
        "source": job.source,
        "status": job.status,
        "rows": (job.result_json or {}).get("rows", []),
        "summary": (job.result_json or {}).get("summary"),
        "applied": (job.result_json or {}).get("applied"),
    }


@router.post("/{job_id}/review")
async def review(
    job_id: int,
    payload: DocumentReviewRequest,
    student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(ImportJob, job_id)
    if job is None or job.student_id != student.id:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    if not payload.apply:
        return {"job_id": job.id, "rows": (job.result_json or {}).get("rows", []), "applied": None}
    result = await apply_import(db, student, job, [item.model_dump() for item in payload.items])
    return {"job_id": job.id, **result}
