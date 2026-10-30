from __future__ import annotations

from dataclasses import dataclass

from app.services.plan.compiler import PlanSpec, RuntimePlan
from app.services.plan.terms import term_index


@dataclass
class Issue:
    level: str  # error / warning
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message}


def validate_spec(spec: PlanSpec) -> list[Issue]:
    issues: list[Issue] = []
    top_sum = round(sum(m.require for m in spec.modules), 2)
    if abs(top_sum - spec.total_credits) > 1e-6:
        issues.append(
            Issue("error", "TOTAL_MISMATCH", f"顶层模块学分之和 {top_sum} ≠ 总学分 {spec.total_credits}")
        )

    keys: set[str] = set()
    course_codes: dict[str, str] = {}

    def walk(module, parent_require: float | None = None):
        if module.key in keys:
            issues.append(Issue("error", "DUP_MODULE", f"模块 id 重复：{module.key}"))
        keys.add(module.key)

        if module.require < 0:
            issues.append(Issue("error", "NEGATIVE_REQUIRE", f"{module.key} 的 require 为负数"))
        if module.require > 0 and not module.children and not module.courses:
            issues.append(Issue("warning", "EMPTY_MODULE", f"{module.key} 有学分要求但没有课程"))
        if parent_require is not None and module.mode in {"all_of", "free"}:
            child_sum = round(sum(c.require for c in module.children), 2)
            if child_sum > parent_require + 1e-6:
                issues.append(
                    Issue(
                        "warning",
                        "CHILD_OVERFLOW",
                        f"{module.key} 子项下限之和 {child_sum} > 自身下限 {parent_require}",
                    )
                )
        if module.mode == "any_of" and module.children:
            if not any(abs(c.require - module.require) < 1e-6 for c in module.children):
                issues.append(
                    Issue(
                        "warning",
                        "ANY_OF_REQUIRE",
                        f"{module.key} 为 any_of，但没有子项达到父项下限 {module.require}",
                    )
                )

        for course in module.courses:
            if course.code in course_codes:
                issues.append(
                    Issue(
                        "error",
                        "DUP_COURSE",
                        f"课程编码 {course.code} 同时出现在 {course_codes[course.code]} 与 {module.key}",
                    )
                )
            course_codes[course.code] = module.key
            if not (0 < course.credit <= 10):
                issues.append(
                    Issue("error", "COURSE_CREDIT", f"{course.name}（{course.code}）学分异常：{course.credit}")
                )
            try:
                term_index(course.plan_term)
            except ValueError:
                issues.append(
                    Issue("error", "COURSE_TERM", f"{course.name}（{course.code}）指导性学期异常：{course.plan_term}")
                )
            if course.assessment not in {"考试", "考查"}:
                issues.append(
                    Issue("warning", "COURSE_ASSESSMENT", f"{course.name} 考核方式异常：{course.assessment}")
                )

        for child in module.children:
            walk(child, module.require)

    for module in spec.modules:
        walk(module)

    for module in spec.modules:
        if module.children:
            continue
        if any(c.nature == "必修" for c in module.courses):
            course_sum = round(sum(c.credit for c in module.courses), 2)
            if abs(course_sum - module.require) > 1e-6:
                issues.append(
                    Issue(
                        "error",
                        "MODULE_COURSE_SUM",
                        f"{module.key} 必修课程学分合计 {course_sum} ≠ 模块要求 {module.require}",
                    )
                )

    cond_credits = [c for c in spec.graduation_conditions if c.get("type") == "credits"]
    if not cond_credits:
        issues.append(Issue("warning", "NO_CREDIT_CONDITION", "毕业条件缺少 credits 项"))
    elif abs(float(cond_credits[0].get("value", 0)) - spec.total_credits) > 1e-6:
        issues.append(
            Issue(
                "error",
                "GRADUATION_CREDIT_MISMATCH",
                f"毕业条件学分 {cond_credits[0].get('value')} ≠ 总学分 {spec.total_credits}",
            )
        )
    if not any(c.get("type") == "second_classroom" for c in spec.graduation_conditions):
        issues.append(Issue("warning", "NO_SECOND_CLASSROOM", "毕业条件缺少第二课堂"))
    if not any(c.get("type") == "thesis_defense" for c in spec.graduation_conditions):
        issues.append(Issue("warning", "NO_THESIS", "毕业条件缺少毕业设计答辩"))

    if not spec.second_classroom:
        issues.append(Issue("warning", "NO_SECOND_REQ", "缺少第二课堂周期要求"))

    return issues


def validate_runtime(plan: RuntimePlan) -> list[Issue]:
    issues: list[Issue] = []
    top_sum = round(sum(r.require for r in plan.roots), 2)
    if abs(top_sum - plan.total_credits) > 1e-6:
        issues.append(Issue("error", "TOTAL_MISMATCH", f"顶层模块学分之和 {top_sum} ≠ 总学分 {plan.total_credits}"))
    for root in plan.roots:
        for node in root.walk():
            if node.mode == "free":
                # free 模式反例检查：子项下限之和不应被当作父项
                if node.children and abs(sum(c.require for c in node.children) - node.require) > 1e-6:
                    issues.append(
                        Issue(
                            "warning",
                            "FREE_SUBTOTAL",
                            f"{node.key} 为 free：子项下限之和 {sum(c.require for c in node.children)} ≠ 父项 {node.require}（预期，不是错误）",
                        )
                    )
    return issues
