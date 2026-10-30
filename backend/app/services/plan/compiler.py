from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Mode = Literal["all_of", "any_of", "free"]


@dataclass
class CourseSpec:
    code: str
    name: str
    credit: float
    plan_term: str = "1-1"
    assessment: str = "考试"
    nature: str = "必修"
    category: str = "专业课"
    tags: list[str] = field(default_factory=list)


@dataclass
class ModuleSpec:
    key: str
    name: str
    mode: Mode = "all_of"
    require: float = 0.0
    children: list[ModuleSpec] = field(default_factory=list)
    courses: list[CourseSpec] = field(default_factory=list)
    tag: str | None = None
    tags: list[str] = field(default_factory=list)
    window: dict[str, Any] | None = None
    direction: bool = False


@dataclass
class SecondClassroomSpec:
    category: str
    period_type: str
    min_count: int
    label: str = ""


@dataclass
class PlanSpec:
    plan_id: str
    name: str
    major: str
    major_code: str
    grade: int
    degree: str
    total_credits: float
    duration: dict[str, int]
    status: str
    source: str
    effective_from: str
    graduation_conditions: list[dict[str, Any]]
    modules: list[ModuleSpec]
    second_classroom: list[SecondClassroomSpec]
    prerequisites: list[dict[str, str]]


@dataclass
class RuntimeCourse:
    code: str
    name: str
    credit: float
    plan_term: str
    assessment: str
    nature: str
    category: str
    tags: list[str]
    module_key: str


@dataclass
class RuntimeNode:
    key: str
    name: str
    mode: Mode
    require: float
    children: list[RuntimeNode] = field(default_factory=list)
    courses: list[RuntimeCourse] = field(default_factory=list)
    tag: str | None = None
    tags: list[str] = field(default_factory=list)
    window: dict[str, Any] | None = None
    direction: bool = False

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def all_courses(self) -> list[RuntimeCourse]:
        courses: list[RuntimeCourse] = list(self.courses)
        for child in self.children:
            courses.extend(child.all_courses())
        seen: set[str] = set()
        unique: list[RuntimeCourse] = []
        for course in courses:
            if course.code in seen:
                continue
            seen.add(course.code)
            unique.append(course)
        return unique


@dataclass
class RuntimePlan:
    plan_id: str
    name: str
    major: str
    major_code: str
    grade: int
    degree: str
    total_credits: float
    duration: dict[str, int]
    status: str
    source: str
    effective_from: str
    graduation_conditions: list[dict[str, Any]]
    roots: list[RuntimeNode]
    second_classroom: list[SecondClassroomSpec]
    prerequisites: list[dict[str, str]]

    def walk(self):
        for root in self.roots:
            yield from root.walk()

    def node(self, key: str) -> RuntimeNode | None:
        for node in self.walk():
            if node.key == key:
                return node
        return None

    def course_map(self) -> dict[str, RuntimeCourse]:
        result: dict[str, RuntimeCourse] = {}
        for node in self.walk():
            for course in node.courses:
                result.setdefault(course.code, course)
        return result

    def course_module(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for node in self.walk():
            for course in node.courses:
                result.setdefault(course.code, node.key)
        return result
