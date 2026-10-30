from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), default="student")  # student / admin / teacher(预留)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    major: Mapped[str] = mapped_column(String(120), index=True)
    major_code: Mapped[str] = mapped_column(String(16), default="080901", index=True)
    grade: Mapped[int] = mapped_column(Integer, index=True)
    degree: Mapped[str] = mapped_column(String(32), default="工学学士")
    version: Mapped[str] = mapped_column(String(32), default="v1")
    total_credits: Mapped[float] = mapped_column(Float, default=169.0)
    duration_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    graduation_conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="frozen")  # draft/reviewing/frozen
    source: Mapped[str] = mapped_column(String(256), default="")
    hash: Mapped[str] = mapped_column(String(64), default="")
    effective_from: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    modules: Mapped[list[Module]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    courses: Mapped[list[PlanCourse]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    second_classroom_reqs: Mapped[list[SecondClassroomReq]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (UniqueConstraint("plan_id", "key", name="uq_module_plan_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(16), default="all_of")  # all_of/any_of/free
    require_credits: Mapped[float] = mapped_column(Float, default=0.0)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    window_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    direction: Mapped[bool] = mapped_column(Boolean, default=False)

    plan: Mapped[Plan] = relationship(back_populates="modules")
    parent: Mapped[Module | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[Module]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    courses: Mapped[list[PlanCourse]] = relationship(back_populates="module")


class PlanCourse(Base):
    __tablename__ = "plan_courses"
    __table_args__ = (
        UniqueConstraint("plan_id", "module_id", "course_code", name="uq_plan_module_course"),
        Index("ix_plan_course_code", "plan_id", "course_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), index=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), index=True)
    course_code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(160))
    credit: Mapped[float] = mapped_column(Float, default=0.0)
    plan_term: Mapped[str] = mapped_column(String(8), default="1-1")  # 指导性学期 1-1 … 4-2
    assessment: Mapped[str] = mapped_column(String(8), default="考试")
    nature: Mapped[str] = mapped_column(String(8), default="必修")
    category: Mapped[str] = mapped_column(String(32), default="专业课")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    plan: Mapped[Plan] = relationship(back_populates="courses")
    module: Mapped[Module] = relationship(back_populates="courses")


class Course(Base):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    name_norm: Mapped[str] = mapped_column(String(160), index=True)
    credit: Mapped[float] = mapped_column(Float, default=0.0)
    hours_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    nature: Mapped[str] = mapped_column(String(8), default="必修")
    category: Mapped[str] = mapped_column(String(32), default="专业课")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    stats_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CourseAlias(Base):
    __tablename__ = "course_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(String(160), index=True)
    alias_norm: Mapped[str] = mapped_column(String(160), index=True)
    course_code: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_code: Mapped[str] = mapped_column(String(32), index=True)
    prereq_code: Mapped[str] = mapped_column(String(32), index=True)
    type: Mapped[str] = mapped_column(String(8), default="先修")


class Offering(Base):
    __tablename__ = "offerings"
    __table_args__ = (
        UniqueConstraint("semester", "course_code", "class_id", name="uq_offering"),
        Index("ix_offering_sem_course", "semester", "course_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    semester: Mapped[str] = mapped_column(String(16), index=True)
    course_code: Mapped[str] = mapped_column(String(32), index=True)
    class_id: Mapped[str] = mapped_column(String(16), default="01")
    teacher: Mapped[str] = mapped_column(String(64), default="")
    time_slots: Mapped[list[str]] = mapped_column(JSON, default=list)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    enrolled: Mapped[int] = mapped_column(Integer, default=0)
    allowed_grades: Mapped[list[int]] = mapped_column(JSON, default=list)
    campus: Mapped[str] = mapped_column(String(32), default="主校区")
    note: Mapped[str] = mapped_column(String(120), default="")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    major: Mapped[str] = mapped_column(String(120))
    grade: Mapped[int] = mapped_column(Integer, index=True)
    entry_year: Mapped[int] = mapped_column(Integer)
    class_name: Mapped[str] = mapped_column(String(64), default="")
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"))
    target_graduation_term: Mapped[str] = mapped_column(String(16), default="")
    current_term: Mapped[str] = mapped_column(String(16), default="")
    direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    enrollments: Mapped[list[Enrollment]] = relationship(back_populates="student", cascade="all, delete-orphan")
    second_classroom: Mapped[list[SecondClassroomRecord]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    overlays: Mapped[list[PlanOverlay]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (Index("ix_enrollment_student_course", "student_id", "course_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    course_code: Mapped[str] = mapped_column(String(32), index=True)
    course_name: Mapped[str] = mapped_column(String(160), default="")
    term: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), default="studying")  # passed/studying/failed/withdrawn
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gp: Mapped[float | None] = mapped_column(Float, nullable=True)
    credits_earned: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="seed")

    student: Mapped[Student] = relationship(back_populates="enrollments")


class CreditRecognition(Base):
    __tablename__ = "credit_recognitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    source: Mapped[str] = mapped_column(String(120))
    target: Mapped[str] = mapped_column(String(32))
    credits: Mapped[float] = mapped_column(Float, default=0.0)
    type: Mapped[str] = mapped_column(String(16), default="认定")
    evidence: Mapped[str] = mapped_column(String(256), default="")
    approved_by: Mapped[str] = mapped_column(String(64), default="")


class SecondClassroomReq(Base):
    __tablename__ = "second_classroom_reqs"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), index=True)
    category: Mapped[str] = mapped_column(String(64))
    period_type: Mapped[str] = mapped_column(String(8), default="year")  # year/term/total
    min_count: Mapped[int] = mapped_column(Integer, default=1)
    label: Mapped[str] = mapped_column(String(120), default="")

    plan: Mapped[Plan] = relationship(back_populates="second_classroom_reqs")


class SecondClassroomRecord(Base):
    __tablename__ = "second_classroom_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    term: Mapped[str] = mapped_column(String(16))
    date: Mapped[str] = mapped_column(String(32), default="")
    title: Mapped[str] = mapped_column(String(200))
    evidence: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student: Mapped[Student] = relationship(back_populates="second_classroom")


class PlanOverlay(Base):
    __tablename__ = "plan_overlays"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    plan_id: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(32))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    approved_by: Mapped[str] = mapped_column(String(64), default="")
    effective_term: Mapped[str] = mapped_column(String(16), default="")

    student: Mapped[Student] = relationship(back_populates="overlays")


class MappingDecision(Base):
    __tablename__ = "mapping_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_name: Mapped[str] = mapped_column(String(200))
    raw_code: Mapped[str] = mapped_column(String(32), default="")
    course_code: Mapped[str] = mapped_column(String(32), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    method: Mapped[str] = mapped_column(String(16), default="L1")  # L1/L2/L3/manual
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/confirmed/rejected
    confirmed_by: Mapped[str] = mapped_column(String(64), default="")
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditSnapshot(Base):
    __tablename__ = "audit_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    semester: Mapped[str] = mapped_column(String(16), index=True)
    plan_id: Mapped[str] = mapped_column(String(64))
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    engine_version: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    filename: Mapped[str] = mapped_column(String(256), default="")
    source: Mapped[str] = mapped_column(String(32), default="file")  # pdf/excel/docx/plugin
    status: Mapped[str] = mapped_column(String(16), default="parsed")  # parsed/confirmed/rejected
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
