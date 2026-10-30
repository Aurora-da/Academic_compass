from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Course, CourseAlias, Enrollment, ImportJob, MappingDecision, Student
from app.services.audit.matcher import CourseMatcher
from app.services.ingestion.docx import parse_docx
from app.services.ingestion.excel import parse_excel
from app.services.ingestion.pdf import parse_pdf, parse_pdf_text_blocks


class ImportError_(ValueError):
    pass


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


async def _matcher(session: AsyncSession) -> CourseMatcher:
    courses = list((await session.execute(select(Course))).scalars().all())
    aliases = list((await session.execute(select(CourseAlias))).scalars().all())
    return CourseMatcher(
        [{"code": c.code, "name": c.name} for c in courses],
        [{"alias": a.alias, "course_code": a.course_code} for a in aliases],
    )


async def parse_upload(filename: str, content: bytes, fallback_term: str) -> list[dict]:
    suffix = _ext(filename)
    if suffix not in {".pdf", ".xlsx", ".docx", ".json", ".csv", ".txt"}:
        raise ImportError_("暂不支持该文件类型，请上传 PDF / Excel / Word / JSON")
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(content)
    try:
        if suffix == ".pdf":
            rows = parse_pdf(path, fallback_term)
            if not rows:
                rows = parse_pdf_text_blocks(path, fallback_term)
        elif suffix == ".xlsx":
            rows = parse_excel(path, fallback_term)
        elif suffix == ".docx":
            rows = parse_docx(path, fallback_term)
        elif suffix == ".json":
            payload = json.loads(content.decode("utf-8-sig"))
            rows = _rows_from_json(payload, fallback_term)
        else:
            rows = _rows_from_csv(content.decode("utf-8-sig"), fallback_term)
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    if not rows:
        raise ImportError_("没有从文件中解析出课程记录，请检查表头是否包含“课程名称/学分”等列")
    return rows


def _rows_from_json(payload: dict, fallback_term: str) -> list[dict]:
    courses = payload.get("courses") or []
    from app.services.ingestion.normalizer import normalize_row

    return [
        normalize_row(
            {
                "name": c.get("name"),
                "code": c.get("code"),
                "credit": c.get("credit"),
                "term": c.get("term", fallback_term),
                "status": c.get("status"),
                "score": c.get("score"),
                "nature": c.get("nature"),
                "category": c.get("category"),
            },
            fallback_term,
        )
        for c in courses
    ]


def _rows_from_csv(text: str, fallback_term: str) -> list[dict]:
    import csv
    import io

    reader = csv.DictReader(io.StringIO(text))
    from app.services.ingestion.normalizer import normalize_row

    rows = []
    for row in reader:
        rows.append(
            normalize_row(
                {
                    "name": row.get("课程名称") or row.get("课程名") or row.get("name"),
                    "code": row.get("课程号") or row.get("课程编码") or row.get("code"),
                    "credit": row.get("学分") or row.get("credit"),
                    "term": row.get("学期") or row.get("term") or fallback_term,
                    "status": row.get("状态") or row.get("status"),
                    "score": row.get("成绩") or row.get("score"),
                },
                fallback_term,
            )
        )
    return [r for r in rows if r["raw_name"] and r["raw_credit"] is not None]


async def create_import_job(
    session: AsyncSession,
    student: Student,
    rows: list[dict],
    *,
    filename: str,
    source: str,
) -> ImportJob:
    matcher = await _matcher(session)
    course_credits = {
        code: credit
        for code, credit in (await session.execute(select(Course.code, Course.credit))).all()
    }
    enriched = []
    for index, row in enumerate(rows):
        match = matcher.match(row["raw_name"], row["raw_code"])
        enriched.append(
            {
                "index": index,
                **row,
                "course_code": match.course_code,
                "course_name": match.course_name,
                "matched_credit": course_credits.get(match.course_code),
                "confidence": match.confidence,
                "method": match.method,
                "need_confirm": match.need_confirm,
                "candidates": [c.__dict__ for c in match.candidates],
            }
        )
    job = ImportJob(
        student_id=student.id,
        filename=filename,
        source=source,
        status="parsed",
        result_json={
            "rows": enriched,
            "summary": {
                "total": len(enriched),
                "matched": sum(1 for r in enriched if r["course_code"]),
                "need_confirm": sum(1 for r in enriched if r["need_confirm"]),
            },
        },
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def apply_import(
    session: AsyncSession,
    student: Student,
    job: ImportJob,
    items: list[dict],
) -> dict:
    rows = (job.result_json or {}).get("rows", [])
    by_index = {r["index"]: r for r in rows}
    matcher = await _matcher(session)
    courses = {c.code: c for c in (await session.execute(select(Course))).scalars().all()}

    applied = updated = skipped = 0
    for item in items:
        row = by_index.get(item.get("index"))
        if not row:
            continue
        status = item.get("status") or row["raw_status"]
        if status == "skip":
            skipped += 1
            continue
        code = (item.get("course_code") or row.get("course_code") or "").strip().upper()
        if not code:
            session.add(
                MappingDecision(
                    raw_name=row["raw_name"],
                    raw_code=row.get("raw_code", ""),
                    course_code="",
                    confidence=row.get("confidence", 0),
                    method=row.get("method", "pending"),
                    status="pending",
                    context_json={"import_job_id": job.id, "index": row["index"]},
                )
            )
            skipped += 1
            continue
        course = courses.get(code)
        name = (item.get("course_name") or (course.name if course else row["raw_name"])).strip()
        credit = (
            item.get("credit")
            if item.get("credit") is not None
            else (course.credit if course else row.get("raw_credit"))
        ) or 0.0
        term = item.get("term") or row.get("raw_term") or student.current_term
        score = item.get("score") if item.get("score") is not None else row.get("raw_score")
        credits_earned = float(credit) if status == "passed" else 0.0

        existing = (
            await session.execute(
                select(Enrollment).where(
                    Enrollment.student_id == student.id,
                    Enrollment.course_code == code,
                    Enrollment.term == term,
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.status = status
            existing.score = score
            existing.course_name = name
            existing.credits_earned = credits_earned
            existing.source = f"import:{job.source}"
            updated += 1
        else:
            session.add(
                Enrollment(
                    student_id=student.id,
                    course_code=code,
                    course_name=name,
                    term=term,
                    status=status,
                    score=score,
                    gp=round(max(0.0, ((score or 0) - 50) / 10), 2) if score else None,
                    credits_earned=credits_earned,
                    source=f"import:{job.source}",
                )
            )
            applied += 1

        match = matcher.match(row["raw_name"], code)
        session.add(
            MappingDecision(
                raw_name=row["raw_name"],
                raw_code=row.get("raw_code", ""),
                course_code=code,
                confidence=1.0 if item.get("course_code") else row.get("confidence", 0),
                method="manual" if item.get("course_code") else row.get("method", "L1"),
                status="confirmed",
                confirmed_by="student",
                context_json={"import_job_id": job.id, "index": row["index"], "need_confirm": match.need_confirm},
            )
        )

    job.status = "confirmed"
    job.result_json = {
        **(job.result_json or {}),
        "applied": {"added": applied, "updated": updated, "skipped": skipped},
    }
    await session.commit()
    return {"added": applied, "updated": updated, "skipped": skipped, "job_id": job.id}


async def list_import_jobs(session: AsyncSession, student_id: int) -> list[ImportJob]:
    return list(
        (
            await session.execute(
                select(ImportJob).where(ImportJob.student_id == student_id).order_by(ImportJob.id.desc())
            )
        )
        .scalars()
        .all()
    )
