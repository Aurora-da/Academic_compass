from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from app.services.plan.compiler import (
    CourseSpec,
    ModuleSpec,
    PlanSpec,
    RuntimeCourse,
    RuntimeNode,
    RuntimePlan,
    SecondClassroomSpec,
)


class PlanLoadError(ValueError):
    pass


def _course(raw: dict, default_module: str) -> CourseSpec:
    if not raw.get("code") or not raw.get("name"):
        raise PlanLoadError(f"课程缺少 code/name：{raw!r}（模块 {default_module}）")
    return CourseSpec(
        code=str(raw["code"]).strip(),
        name=str(raw["name"]).strip(),
        credit=float(raw.get("credit", 0.0)),
        plan_term=str(raw.get("term", "1-1")),
        assessment=str(raw.get("assessment", "考试")),
        nature=str(raw.get("nature", "必修")),
        category=str(raw.get("category", "专业课")),
        tags=list(raw.get("tags") or []),
    )


def _module(raw: dict) -> ModuleSpec:
    key = str(raw.get("id") or raw.get("key") or "").strip()
    if not key:
        raise PlanLoadError(f"模块缺少 id：{raw!r}")
    mode = str(raw.get("mode", "all_of"))
    if mode not in {"all_of", "any_of", "free"}:
        raise PlanLoadError(f"模块 {key} 的 mode 非法：{mode}")
    spec = ModuleSpec(
        key=key,
        name=str(raw.get("name", key)),
        mode=mode,  # type: ignore[arg-type]
        require=float(raw.get("require", 0.0)),
        tag=raw.get("tag"),
        tags=list(raw.get("tags") or []),
        window=raw.get("window"),
        direction=bool(raw.get("direction", False)),
    )
    spec.courses = [_course(c, key) for c in raw.get("courses") or []]
    spec.children = [_module(c) for c in raw.get("children") or []]
    if not spec.children and spec.courses:
        # 叶子模块：课程直接挂在模块上
        pass
    return spec


def load_plan_yaml(path: str | Path) -> PlanSpec:
    p = Path(path)
    if not p.exists():
        raise PlanLoadError(f"培养方案文件不存在：{p}")
    raw_text = p.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    if not isinstance(data, dict):
        raise PlanLoadError("培养方案 YAML 顶层必须是对象")

    required = ["plan_id", "name", "major", "grade", "total_credits", "modules"]
    missing = [k for k in required if k not in data]
    if missing:
        raise PlanLoadError(f"培养方案缺少字段：{', '.join(missing)}")

    duration = data.get("duration") or {"standard": 4, "min": 3, "max": 6}
    second = [
        SecondClassroomSpec(
            category=str(x["category"]),
            period_type=str(x.get("period_type", "year")),
            min_count=int(x.get("min_count", 1)),
            label=str(x.get("label", "")),
        )
        for x in data.get("second_classroom") or []
    ]
    modules = [_module(m) for m in data["modules"]]
    return PlanSpec(
        plan_id=str(data["plan_id"]),
        name=str(data["name"]),
        major=str(data["major"]),
        major_code=str(data.get("major_code", "")),
        grade=int(data["grade"]),
        degree=str(data.get("degree", "工学学士")),
        total_credits=float(data["total_credits"]),
        duration={k: int(v) for k, v in duration.items()},
        status=str(data.get("status", "draft")),
        source=str(data.get("source", "")),
        effective_from=str(data.get("effective_from", "")),
        graduation_conditions=list(data.get("graduation_conditions") or []),
        modules=modules,
        second_classroom=second,
        prerequisites=list(data.get("prerequisites") or []),
    )


def spec_to_dict(spec: PlanSpec) -> dict:
    def module_dict(m: ModuleSpec) -> dict:
        return {
            "id": m.key,
            "name": m.name,
            "mode": m.mode,
            "require": m.require,
            "tag": m.tag,
            "tags": m.tags,
            "window": m.window,
            "direction": m.direction,
            "courses": [
                {
                    "code": c.code,
                    "name": c.name,
                    "credit": c.credit,
                    "term": c.plan_term,
                    "assessment": c.assessment,
                    "nature": c.nature,
                    "category": c.category,
                    "tags": c.tags,
                }
                for c in m.courses
            ],
            "children": [module_dict(c) for c in m.children],
        }

    return {
        "plan_id": spec.plan_id,
        "name": spec.name,
        "major": spec.major,
        "major_code": spec.major_code,
        "grade": spec.grade,
        "degree": spec.degree,
        "total_credits": spec.total_credits,
        "duration": spec.duration,
        "status": spec.status,
        "source": spec.source,
        "effective_from": spec.effective_from,
        "graduation_conditions": spec.graduation_conditions,
        "second_classroom": [s.__dict__ for s in spec.second_classroom],
        "modules": [module_dict(m) for m in spec.modules],
        "prerequisites": spec.prerequisites,
    }


def compile_spec(spec: PlanSpec) -> RuntimePlan:
    def build(m: ModuleSpec) -> RuntimeNode:
        node = RuntimeNode(
            key=m.key,
            name=m.name,
            mode=m.mode,
            require=m.require,
            tag=m.tag,
            tags=m.tags,
            window=m.window,
            direction=m.direction,
        )
        node.courses = [
            RuntimeCourse(
                code=c.code,
                name=c.name,
                credit=c.credit,
                plan_term=c.plan_term,
                assessment=c.assessment,
                nature=c.nature,
                category=c.category,
                tags=c.tags,
                module_key=m.key,
            )
            for c in m.courses
        ]
        node.children = [build(c) for c in m.children]
        return node

    return RuntimePlan(
        plan_id=spec.plan_id,
        name=spec.name,
        major=spec.major,
        major_code=spec.major_code,
        grade=spec.grade,
        degree=spec.degree,
        total_credits=spec.total_credits,
        duration=spec.duration,
        status=spec.status,
        source=spec.source,
        effective_from=spec.effective_from,
        graduation_conditions=spec.graduation_conditions,
        roots=[build(m) for m in spec.modules],
        second_classroom=spec.second_classroom,
        prerequisites=spec.prerequisites,
    )


def spec_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
