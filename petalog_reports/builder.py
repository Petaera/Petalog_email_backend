"""Turns per-location figures into an owner's report, with insights."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from . import formatting as fmt
from .models import LocationReport, Owner, OwnerReport


def _weekday(day: date) -> str:
    return day.strftime("%A")


def location_insights(r: LocationReport, limit: int = 5) -> List[str]:
    f = r.figures
    out: List[str] = []
    if r.last_week is not None and r.last_week.collections:
        change = fmt.change_ratio(f.collections, r.last_week.collections)
        if change is not None and abs(change) >= 1:
            direction = "higher" if change > 0 else "lower"
            out.append(
                f"Collections were {abs(round(change))}% {direction} than last {_weekday(r.last_week.day)} "
                f"({fmt.money(r.last_week.collections)})."
            )
    if len(r.trend) >= 3 and f.collections > 0:
        best = max(r.trend, key=lambda d: d.collections)
        if best.day == r.day:
            out.append(f"Best day for collections in the last {len(r.trend)} days.")
    if f.pending_count:
        out.append(
            f"{fmt.count(f.pending_count)} ticket{'s' if f.pending_count != 1 else ''} "
            f"({fmt.money(f.pending_amount)}) still waiting for approval: not in collections until approved."
        )
    busiest = r.busiest_hour
    if busiest is not None and f.vehicles >= 3:
        out.append(f"Busiest hour: {busiest.label}, with {fmt.count(busiest.count)} vehicles.")
    if r.services:
        top = r.services[0]
        if top.share >= 25 and len(r.services) > 1:
            out.append(f"{top.label} brought in {round(top.share)}% of the day's service value.")
    if f.pay_later_count:
        out.append(
            f"{fmt.money(f.pay_later_amount)} given on Pay Later across {fmt.count(f.pay_later_count)} "
            f"ticket{'s' if f.pay_later_count != 1 else ''}."
        )
    if r.customers_new:
        out.append(f"{fmt.count(r.customers_new)} new customer{'s' if r.customers_new != 1 else ''} today.")
    if f.collections and r.spending.total / f.collections >= 0.5:
        out.append(f"Spending was {round(r.spending.total / f.collections * 100)}% of collections.")
    return out[:limit]


def build_owner_report(owner: Owner, day: date, template_no: int, locations: List[LocationReport],
                       generated_at: datetime, timezone: str = "Asia/Kolkata") -> OwnerReport:
    for r in locations:
        r.insights = location_insights(r)
    ordered = sorted(locations, key=lambda r: (-r.figures.collections, r.location.name.lower()))
    return OwnerReport(owner=owner, day=day, template_no=template_no if template_no in (1, 2, 3) else 1,
                       locations=ordered, generated_at=generated_at, timezone=timezone)


def subject_for(report: OwnerReport) -> str:
    day = fmt.short_date(report.day)
    collections = report.total("collections")
    vehicles = int(report.total("vehicles"))
    if report.is_multi:
        name = f"{len(report.locations)} locations"
    else:
        name = report.locations[0].location.name
    if not report.has_activity:
        return f"{name} daily report · {day} · No entries recorded"
    return f"{name} daily report · {day} · {fmt.money(collections)} collected, {fmt.count(vehicles)} vehicles"


def preheader_for(report: OwnerReport) -> str:
    if not report.has_activity:
        return f"No entries were recorded on {fmt.long_date(report.day)}."
    parts = [f"{fmt.count(report.total('vehicles'))} vehicles served"]
    pay_later = report.total("pay_later_amount")
    if pay_later:
        parts.append(f"{fmt.money(pay_later)} on Pay Later")
    pending = int(report.total("pending_count"))
    if pending:
        parts.append(f"{pending} ticket{'s' if pending != 1 else ''} awaiting approval")
    previous = report.total_for("last_week", "collections")
    change = fmt.change_ratio(report.total("collections"), previous) if previous is not None else None
    if change is not None:
        parts.append(f"{fmt.signed_percent(change)} vs last {_weekday(report.day)}")
    parts.append(f"net {fmt.money(report.total_net)}")
    return " · ".join(parts)


def delta(current: float, previous: Optional[float]) -> Optional[float]:
    if previous is None:
        return None
    return fmt.change_ratio(current, previous)
