from __future__ import annotations

from dataclasses import dataclass, field

from app.services.plan.compiler import SecondClassroomSpec
from app.services.plan.terms import academic_year_of, completed_academic_years


@dataclass
class SecondClassroomItem:
    category: str
    period_type: str
    period_label: str
    require: int
    done: int
    ok: bool | None  # None = 数据缺失，既不算过也不算不过
    status: str  # met / unmet / missing
    message: str
    records: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "period_type": self.period_type,
            "period_label": self.period_label,
            "require": self.require,
            "done": self.done,
            "ok": self.ok,
            "status": self.status,
            "message": self.message,
            "records": self.records,
        }


def check_second_classroom(
    reqs: list[SecondClassroomSpec],
    records: list[dict],
    entry_year: int,
    current_term: str,
) -> dict:
    """第二课堂：事件 + 周期合规检查。

    三态：达标 / 未达标 / 数据缺失。数据缺失既不算过也不算不过。
    records: [{category, term, date, title, status}]
    只有 approved 记录计入。
    """
    approved = [r for r in records if r.get("status", "approved") == "approved"]
    # 没有任何登记数据时，视为“数据缺失”，不误判为不合格
    no_data_at_all = len(records) == 0
    completed_years = completed_academic_years(entry_year, current_term)
    current_ay = academic_year_of(current_term)

    items: list[SecondClassroomItem] = []
    for req in reqs:
        matched = [r for r in approved if r.get("category") == req.category]
        if req.period_type == "year":
            # 每学年 ≥ N：逐学年展开，当前学年进行中，只检查已结束学年
            if not completed_years:
                items.append(
                    SecondClassroomItem(
                        req.category, "year", f"{current_ay} 学年（进行中）", req.min_count, 0, None,
                        "missing", "尚无已结束学年，待学年结束后判定",
                    )
                )
                continue
            for ay in completed_years:
                recs = [r for r in matched if str(r.get("term", "")).startswith(ay)]
                done = len(recs)
                ok = None if (no_data_at_all and done == 0) else done >= req.min_count
                status = "missing" if ok is None else ("met" if ok else "unmet")
                message = (
                    f"{ay} 学年 {done}/{req.min_count} 次"
                    if ok is not None
                    else f"{ay} 学年数据待确认"
                )
                if ok is False:
                    message += f"，还差 {req.min_count - done} 次"
                items.append(
                    SecondClassroomItem(
                        req.category, "year", f"{ay} 学年", req.min_count, done, ok, status, message, recs
                    )
                )
        elif req.period_type == "term":
            recs = [r for r in matched if r.get("term") == current_term]
            done = len(recs)
            ok = None if (no_data_at_all and done == 0) else done >= req.min_count
            status = "missing" if ok is None else ("met" if ok else "unmet")
            message = f"本学期 {done}/{req.min_count} 次"
            if ok is False:
                message += f"，还差 {req.min_count - done} 次"
            if ok is None:
                message = "本学期数据待确认（未接入第二课堂系统）"
            items.append(
                SecondClassroomItem(
                    req.category, "term", f"{current_term} 学期", req.min_count, done, ok, status, message, recs
                )
            )
        else:  # total
            done = len(matched)
            ok = None if (no_data_at_all and done == 0) else done >= req.min_count
            status = "missing" if ok is None else ("met" if ok else "unmet")
            message = f"累计 {done}/{req.min_count} 项"
            if ok is False:
                message += f"，还差 {req.min_count - done} 项"
            items.append(
                SecondClassroomItem(
                    req.category, "total", "累计", req.min_count, done, ok, status, message, matched
                )
            )

    unmet = [i for i in items if i.status == "unmet"]
    missing = [i for i in items if i.status == "missing"]
    if unmet:
        ok: bool | None = False
    elif missing:
        ok = None
    else:
        ok = True

    return {
        "ok": ok,
        "status": "unmet" if unmet else ("missing" if missing else "met"),
        "items": [i.to_dict() for i in items],
        "unmet_count": len(unmet),
    }
