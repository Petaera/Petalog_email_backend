"""Email rendering: HTML (Jinja2, autoescaped) and a plain-text version.

The three templates owners pick in Profile Settings -> Daily Reports:

1. Classic Business       tables with every figure, no charts
2. Modern Analytics       the same, with bar charts and an hourly chart
3. Business Intelligence  charts plus highlights, a comparison with
                          yesterday / the same day last week, and a 7-day trend
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .. import formatting as fmt
from ..builder import delta, preheader_for, subject_for
from ..models import DayFigures, LocationReport, OwnerReport
from ..timeutil import to_ist

FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# PetaLog app palette (src/index.css): primary hsl(217.58 100% 38.82%) = #004AC6.
THEME = {
    "brand": "#004AC6",
    "brand_dark": "#00307F",
    "brand_soft": "#9DB9EA",
    "page": "#F1F5F9",
    "card": "#FFFFFF",
    "soft": "#F8FAFC",
    "track": "#EEF2F7",
    "line": "#E2E8F0",
    "ink": "#0F172A",
    "text": "#334155",
    "muted": "#64748B",
    "faint": "#94A3B8",
    "pos": "#047857",
    "pos_bg": "#ECFDF5",
    "neg": "#B91C1C",
    "neg_bg": "#FEF2F2",
    "warn": "#92400E",
    "warn_bg": "#FFFBEB",
    "warn_line": "#FCD34D",
    "cat_colors": ["#004AC6", "#0EA5E9", "#94A3B8"],
}

MODE_COLORS = {
    "Cash": "#059669",
    "UPI": "#004AC6",
    "Card": "#0284C7",
    "Bank Transfer": "#D97706",
    "From advance": "#7C3AED",
}

VARIANTS = {
    1: {"name": "Classic Business", "bars": False, "insights": False, "compare": False, "trend": False},
    2: {"name": "Modern Analytics", "bars": True, "insights": False, "compare": False, "trend": False},
    3: {"name": "Business Intelligence", "bars": True, "insights": True, "compare": True, "trend": True},
}


@dataclass
class RenderedEmail:
    subject: str
    html: str
    text: str
    preheader: str


def _mode_color(label: str) -> str:
    return MODE_COLORS.get(label, "#94A3B8")


def _delta_color(value: Optional[float], lower_is_better: bool = False) -> str:
    if value is None or abs(value) < 0.5:
        return THEME["muted"]
    good = value < 0 if lower_is_better else value > 0
    return THEME["pos"] if good else THEME["neg"]


def _share(part: float, whole: float) -> float:
    return (part / whole * 100.0) if whole else 0.0


def _environment() -> Environment:
    here = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(
        loader=FileSystemLoader(here),
        autoescape=select_autoescape(["html", "j2"], default=True, default_for_string=True),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters.update({
        "money": lambda v, d=None: fmt.money(v, d),
        "compact": fmt.compact_money,
        "num": fmt.count,
        "pct": fmt.percent,
        "signed_pct": fmt.signed_percent,
        "long_date": fmt.long_date,
        "short_date": fmt.short_date,
    })
    env.globals.update({
        "t": THEME,
        "font": FONT,
        "mode_color": _mode_color,
        "delta_color": _delta_color,
        "delta": delta,
        "share": _share,
    })
    return env


_ENV = _environment()


def _sum_figures(reports: List[LocationReport], which: str) -> Optional[Dict[str, float]]:
    values = [getattr(r, which) for r in reports]
    if not values or any(v is None for v in values):
        return None
    keys = ("collections", "vehicles", "ticket_collections", "collection_count", "pay_later_amount", "expenses")
    return {k: sum(getattr(v, k) for v in values) for k in keys}


def _hero(report: OwnerReport) -> Dict[str, object]:
    locs = report.locations
    collections = report.total("collections")
    ticket = report.total("ticket_collections")
    count = int(report.total("collection_count"))
    prev = _sum_figures(locs, "previous_day")
    week = _sum_figures(locs, "last_week")
    v4, v2, vo = (int(report.total(a)) for a in ("vehicles_4w", "vehicles_2w", "vehicles_other"))
    split = " · ".join(p for p in (
        f"{v4} 4W" if v4 else "", f"{v2} 2W" if v2 else "", f"{vo} other" if vo else "") if p) or None
    if report.is_multi:
        title = f"{len(locs)} locations"
        subtitle = fmt.long_date(report.day)
        logo = None
    else:
        title = locs[0].location.name
        subtitle = fmt.long_date(report.day) + (f" · {locs[0].location.city}" if locs[0].location.city else "")
        logo = locs[0].location.logo_url
    return {
        "title": title,
        "subtitle": subtitle,
        "logo": logo,
        "collections": collections,
        "d_yesterday": fmt.change_ratio(collections, prev["collections"]) if prev else None,
        "d_week": fmt.change_ratio(collections, week["collections"]) if week else None,
        "weekday": report.day.strftime("%A"),
        "vehicles": int(report.total("vehicles")),
        "vehicle_split": split,
        "avg": ticket / count if count else 0,
        "collection_count": count,
        "pay_later": report.total("pay_later_amount"),
        "pay_later_count": int(report.total("pay_later_count")),
        "pending_count": int(report.total("pending_count")),
        "pending_amount": report.total("pending_amount"),
        "spending": report.total_spending,
        "net": report.total_net,
    }


def _compare_rows(report: OwnerReport) -> List[Dict[str, object]]:
    if report.is_multi:
        return []
    L = report.locations[0]
    if L.previous_day is None and L.last_week is None:
        return []

    def line(label, attr, money=True, lower_is_better=False, spending=False):
        def value(f: Optional[DayFigures]):
            if f is None:
                return None
            if attr == "avg":
                return f.avg_per_vehicle
            return getattr(f, attr)
        today = value(L.figures)
        y, w = value(L.previous_day), value(L.last_week)
        def show(v):
            return fmt.money(v, 0) if money else fmt.count(v)
        return {
            "label": label,
            "today": show(today),
            "yesterday": show(y) if y is not None else "–",
            "last_week": show(w) if w is not None else "–",
            "d_yesterday": fmt.change_ratio(today, y) if y is not None else None,
            "d_week": fmt.change_ratio(today, w) if w is not None else None,
            "lower_is_better": lower_is_better,
        }

    return [
        line("Collections", "collections"),
        line("Vehicles served", "vehicles", money=False),
        line("Average per vehicle", "avg"),
        line("Pay Later", "pay_later_amount", lower_is_better=True),
        line("Expenses", "expenses", lower_is_better=True),
    ]


def _trend_items(report: OwnerReport) -> List[Dict[str, object]]:
    days: Dict = {}
    for L in report.locations:
        for f in L.trend:
            days[f.day] = days.get(f.day, 0.0) + f.collections
    ordered = sorted(days.items())
    if len(ordered) < 2:
        return []
    return [{"label": d.strftime("%a"), "value": v, "caption": fmt.compact_money(v) if v else ""} for d, v in ordered]


def _owner_insights(report: OwnerReport) -> List[str]:
    out: List[str] = []
    for L in report.locations:
        if L.insights:
            out.append(f"{L.location.name}: {L.insights[0]}")
    return out[:5]


def render_email(report: OwnerReport, *, app_url: str, logo_url: str, brand_name: str = "PetaLog",
                 unsubscribe_url: Optional[str] = None, attachment_note: Optional[str] = None) -> RenderedEmail:
    subject = subject_for(report)
    preheader = preheader_for(report)
    variant = VARIANTS.get(report.template_no, VARIANTS[1])
    warnings = sorted({w for L in report.locations for w in L.warnings})
    links = {
        "dashboard": f"{app_url}/dashboard",
        "settings": f"{app_url}/profileSettings",
        "unsubscribe": unsubscribe_url,
    }
    generated = to_ist(report.generated_at)
    context = {
        "report": report,
        "variant": variant,
        "subject": subject,
        "preheader": preheader,
        "hero": _hero(report),
        "compare_rows": _compare_rows(report),
        "trend_items": _trend_items(report),
        "owner_insights": _owner_insights(report),
        "links": links,
        "brand": {"name": brand_name, "logo": logo_url, "site": app_url.replace("https://", "").replace("http://", "")},
        "attachment_note": attachment_note,
        "warnings": warnings,
        "generated_label": f"{generated.day} {generated.strftime('%b %Y, %I:%M %p')} IST",
    }
    html = _ENV.get_template("report.html.j2").render(**context)
    text = render_text(report, context)
    return RenderedEmail(subject=subject, html=html, text=text, preheader=preheader)


def render_text(report: OwnerReport, ctx: Dict[str, object]) -> str:
    hero = ctx["hero"]
    lines: List[str] = [
        f"{hero['title']} - daily report",
        fmt.long_date(report.day),
        "",
        f"Collections:         {fmt.money(hero['collections'])}",
    ]
    if hero["d_yesterday"] is not None:
        lines.append(f"  vs yesterday:       {fmt.signed_percent(hero['d_yesterday'])}")
    if hero["d_week"] is not None:
        lines.append(f"  vs last {hero['weekday']}: {fmt.signed_percent(hero['d_week'])}")
    lines += [
        f"Vehicles served:     {fmt.count(hero['vehicles'])}",
        f"Average per vehicle: {fmt.money(hero['avg'], 0)}",
        f"Pay Later today:     {fmt.money(hero['pay_later'])} ({hero['pay_later_count']} ticket{'' if hero['pay_later_count'] == 1 else 's'})",
        f"Spending:            {fmt.money(hero['spending'])}",
        f"Net for the day:     {fmt.money(hero['net'])}",
    ]
    if hero["pending_count"]:
        lines += ["", f"{hero['pending_count']} ticket(s) ({fmt.money(hero['pending_amount'])}) waiting for approval."]
    for L in report.locations:
        lines += ["", "-" * 48]
        if report.is_multi:
            lines.append(L.location.name.upper())
        if not L.figures.has_activity:
            lines.append("No entries recorded.")
            continue
        for text in L.insights[:5]:
            lines.append(f"* {text}")
        if L.payments:
            lines += ["", "How you were paid"]
            for row in L.payments:
                lines.append(f"  {row.label:<22}{fmt.money(row.amount):>14}  {round(row.share)}%")
                for child in row.children:
                    lines.append(f"    {child.label:<20}{fmt.money(child.amount):>14}")
        if L.services:
            lines += ["", "Services"]
            for row in L.services[:10]:
                lines.append(f"  {row.label[:22]:<22}{fmt.money(row.amount):>14}  x{row.count}")
        lines += ["", "Money in & out", f"  {'Collections':<22}{fmt.money(L.figures.collections):>14}"]
        for row in L.spending.by_category:
            lines.append(f"  {row.label[:22]:<22}{('-' + fmt.money(row.amount)):>14}")
        lines.append(f"  {'Net':<22}{fmt.money(L.net):>14}")
        if L.cash_balance is not None:
            lines.append(f"  {'Cash in hand (now)':<22}{fmt.money(L.cash_balance):>14}")
    links = ctx["links"]
    lines += [
        "",
        "-" * 48,
        f"Dashboard: {links['dashboard']}",
        f"Change time or template: {links['settings']}",
    ]
    if links.get("unsubscribe"):
        lines.append(f"Stop these emails: {links['unsubscribe']}")
    if ctx.get("attachment_note"):
        lines.append(str(ctx["attachment_note"]))
    lines.append(f"Generated {ctx['generated_label']}.")
    return "\n".join(lines) + "\n"
