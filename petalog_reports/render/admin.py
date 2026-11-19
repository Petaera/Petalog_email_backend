"""Operator summary email (ADMIN_SUMMARY_MODE: failures | always | off)."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from markupsafe import escape

from .. import formatting as fmt
from . import FONT, THEME

STATUS_COLORS = {"success": THEME["pos"], "failed": THEME["neg"], "skipped": THEME["muted"]}


def render_admin_summary(summary: Dict[str, Any]) -> Tuple[str, str, str]:
    dates = ", ".join(summary["reportDates"]) or "-"
    subject = (f"PetaLog daily reports: {summary['sent']} sent, {summary['failed']} failed, "
               f"{summary['skipped']} skipped ({summary['trigger']}, {dates})")
    rows = []
    lines = [subject, ""]
    for r in summary["results"]:
        detail = r.get("error") or r.get("reason") or r.get("locationNames") or ""
        color = STATUS_COLORS.get(r["status"], THEME["muted"])
        rows.append(
            f"<tr><td style='padding:8px;border-top:1px solid {THEME['line']};'>{escape(r.get('owner', ''))}<br>"
            f"<span style='color:{THEME['muted']};font-size:12px;'>{escape(r.get('email', ''))}</span></td>"
            f"<td style='padding:8px;border-top:1px solid {THEME['line']};color:{color};font-weight:600;'>"
            f"{escape(r['status'])}</td>"
            f"<td style='padding:8px;border-top:1px solid {THEME['line']};text-align:right;'>"
            f"{escape(fmt.money(r.get('revenue', 0) or 0))}</td>"
            f"<td style='padding:8px;border-top:1px solid {THEME['line']};font-size:12px;color:{THEME['text']};'>"
            f"{escape(detail)}</td></tr>"
        )
        lines.append(f"- {r.get('owner')} <{r.get('email')}>: {r['status']} {detail}")
    html = (
        f"<!DOCTYPE html><html><body style='margin:0;padding:24px;background:{THEME['page']};font-family:{FONT};'>"
        f"<table role='presentation' width='100%' style='max-width:760px;margin:0 auto;background:#fff;"
        f"border:1px solid {THEME['line']};border-radius:12px;border-collapse:collapse;'>"
        f"<tr><td style='padding:20px 24px;border-top:4px solid {THEME['brand']};'>"
        f"<div style='font-size:18px;font-weight:700;color:{THEME['ink']};'>Daily reports run</div>"
        f"<div style='font-size:13px;color:{THEME['muted']};padding-top:4px;'>Trigger {escape(summary['trigger'])} "
        f"&middot; report day {escape(dates)} &middot; {summary['sent']} sent &middot; {summary['failed']} failed "
        f"&middot; {summary['skipped']} skipped</div>"
        f"<table role='presentation' width='100%' style='border-collapse:collapse;margin-top:16px;font-size:14px;"
        f"color:{THEME['ink']};'><tr style='color:{THEME['muted']};font-size:12px;text-align:left;'>"
        f"<th style='padding:8px;'>Owner</th><th style='padding:8px;'>Status</th>"
        f"<th style='padding:8px;text-align:right;'>Collections</th><th style='padding:8px;'>Detail</th></tr>"
        + "".join(rows) +
        "</table></td></tr></table></body></html>"
    )
    return subject, html, "\n".join(lines) + "\n"
