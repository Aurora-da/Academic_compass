from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    semester: str | None = None
    resume: dict[str, Any] | None = None


class SimulateRequest(BaseModel):
    course_code: str
    semester: str | None = None


class DirectionRequest(BaseModel):
    direction_id: str


class SecondClassroomCreate(BaseModel):
    category: str
    term: str
    date: str = ""
    title: str = Field(min_length=1, max_length=200)
    evidence: str = ""


class SecondClassroomReview(BaseModel):
    status: Literal["approved", "rejected"]
    comment: str = ""


class DocumentReviewItem(BaseModel):
    index: int
    course_code: str | None = None
    course_name: str | None = None
    credit: float | None = None
    term: str | None = None
    status: Literal["passed", "studying", "failed", "withdrawn", "skip"] | None = None
    score: float | None = None


class DocumentReviewRequest(BaseModel):
    items: list[DocumentReviewItem] = Field(default_factory=list)
    apply: bool = True


class PluginCourse(BaseModel):
    code: str | None = None
    name: str
    credit: float
    term: str
    status: str = "passed"
    score: float | None = None
    category: str | None = None
    nature: str | None = None


class PluginImportRequest(BaseModel):
    source: str = "plugin"
    courses: list[PluginCourse]
    apply: bool = False


class MappingConfirmRequest(BaseModel):
    course_code: str
    create_alias: bool = True


class TrialRequest(BaseModel):
    student_nos: list[str] = Field(default_factory=list)
