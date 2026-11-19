"""Formatting for emails: Indian-style rupee amounts, counts, dates."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional


def _group_indian(integer_digits: str) -> str:
    """'1234567' -> '12,34,567'."""
    if len(integer_digits) <= 3:
        return integer_digits
    head, tail = integer_digits[:-3], integer_digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def money(value, decimals: Optional[int] = None, symbol: str = "₹") -> str:
    """₹1,23,456 (whole rupees) or ₹1,23,456.50 when there are paise."""
    try:
        amount = Decimal(str(value if value is not None else 0))
    except Exception:
        amount = Decimal(0)
    if decimals is None:
        decimals = 0 if amount == amount.to_integral_value() else 2
    quant = Decimal(1) if decimals == 0 else Decimal(1).scaleb(-decimals)
    amount = amount.quantize(quant, rounding=ROUND_HALF_UP)
    negative = amount < 0
    text = f"{abs(amount):.{decimals}f}"
    integer, _, fraction = text.partition(".")
    out = _group_indian(integer) + (f".{fraction}" if fraction else "")
    return f"{'-' if negative else ''}{symbol}{out}"


def compact_money(value, symbol: str = "₹") -> str:
    """₹48.2K, ₹1.2L, ₹3.4Cr: for chart labels."""
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    if amount >= 1e7:
        return f"{sign}{symbol}{amount / 1e7:.1f}Cr"
    if amount >= 1e5:
        return f"{sign}{symbol}{amount / 1e5:.1f}L"
    if amount >= 1e3:
        return f"{sign}{symbol}{amount / 1e3:.1f}K"
    return f"{sign}{symbol}{amount:.0f}"


def count(value) -> str:
    try:
        return _group_indian(str(int(round(float(value or 0)))))
    except (TypeError, ValueError):
        return "0"


def percent(value, decimals: int = 0) -> str:
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "0%"


def signed_percent(value: Optional[float]) -> str:
    if value is None:
        return "–"
    rounded = round(value)
    if rounded == 0:
        return "0%"
    return f"{'+' if rounded > 0 else '−'}{abs(rounded)}%"


def change_ratio(current: float, previous: float) -> Optional[float]:
    """Percentage change, or None when there is nothing to compare with."""
    if not previous:
        return None
    return (current - previous) / abs(previous) * 100.0


def long_date(day: date) -> str:
    """Tuesday, 18 November 2026."""
    return f"{day.strftime('%A')}, {day.day} {day.strftime('%B %Y')}"


def short_date(day: date) -> str:
    """Tue 18 Nov."""
    return f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"


def hour_label(hour: int) -> str:
    """13 -> '1 PM'."""
    suffix = "AM" if hour < 12 else "PM"
    h = hour % 12 or 12
    return f"{h} {suffix}"
