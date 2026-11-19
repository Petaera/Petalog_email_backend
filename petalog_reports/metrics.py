"""Daily figures, computed with the same rules as the PetaLog app.

Sources mirrored here (Petalog-UI / database), so the email always shows the
numbers the owner sees on the Dashboard:

* private.dashboard_summary_body  -> vehicles, collections by mode, vehicle
  mix, Pay Later, pending tickets, expenses (``day_figures``)
* get_advance_summary             -> advance used / received
* get_retail_sales_summary        -> counter sales, items sold
* get_due_payments_summary        -> old dues collected
* src/lib/dashboardSummary.ts     -> how the four above are combined
  (withAdvances, withRetailSales, withDuePayments)
* OperationsReport.serviceSharesOf -> service breakdown (amount shared by
  catalogue price; items sold and extra work as their own rows)
* income_expense_report           -> spending (expenses, staff expenses,
  salaries, staff payments)

If one of those changes in the app, change the matching function here and
its test in tests/test_metrics.py.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .formatting import hour_label
from .models import (
    BreakdownRow,
    DayFigures,
    LocationDataset,
    LocationReport,
    Spending,
    TransactionRow,
)
from .timeutil import day_bounds, in_window, parse_date, parse_ts, to_ist

PAY_LATER_MODES = ("credit", "subscription_credit_later")
CARD_MODES = ("card", "subscription_credit_card")
BANK_MODES = ("bank", "subscription_credit_bank")
UPI_ACCOUNT_MODES = ("upi", "subscription_credit_upi")

MODE_LABELS = {
    "cash": "Cash",
    "upi": "UPI",
    "card": "Card",
    "bank": "Bank Transfer",
    "credit": "Pay Later",
    "advance": "Advance",
    "split": "Split",
    "subscription": "Plan",
    "subscription_credit": "Plan",
    "subscription_credit_cash": "Plan + Cash",
    "subscription_credit_upi": "Plan + UPI",
    "subscription_credit_card": "Plan + Card",
    "subscription_credit_bank": "Plan + Bank Transfer",
    "subscription_credit_later": "Plan + Pay Later",
}


def num(value: Any) -> float:
    try:
        result = float(value) if value is not None and value != "" else 0.0
    except (TypeError, ValueError):
        return 0.0
    return result if result == result else 0.0  # NaN -> 0


def net_amount(log: Dict[str, Any]) -> float:
    """COALESCE(total, amount - discount): the app's ticket amount."""
    if log.get("total") is not None:
        return num(log.get("total"))
    return num(log.get("amount")) - num(log.get("discount"))


def mode_label(mode: Optional[str]) -> str:
    key = (mode or "").strip().lower()
    if not key:
        return "Not set"
    return MODE_LABELS.get(key, key.replace("_", " ").title())


def vehicle_category(raw_type: str) -> str:
    """'4', '2' or 'other': the dashboard's CASE, verbatim."""
    t = raw_type
    if t == "2" or "2 wheeler" in t or "2-wheeler" in t:
        return "2"
    if t in ("1", "4") or any(k in t for k in ("4 wheeler", "4-wheeler", "car", "suv", "sedan", "hatch back")):
        return "4"
    return "other"


CATEGORY_LABELS = {"4": "4-wheelers", "2": "2-wheelers", "other": "Other"}


@dataclass
class _Row:
    """One row of the dashboard's `base` CTE (a ticket, or one split part)."""

    key: str
    log: Dict[str, Any]
    approval_status: Optional[str]
    payment_mode: Optional[str]
    payment_id: Optional[str]
    payment_date: Optional[datetime]
    exit_time: Optional[datetime]
    created_at: Optional[datetime]
    entry_time: Optional[datetime]
    amount: float
    category: str


class DayContext:
    """Pre-parsed rows of a dataset, reusable for every day in its window."""

    def __init__(self, data: LocationDataset):
        self.data = data
        loc_id = data.location.id
        logs_by_id = {str(log["id"]): log for log in data.logs if log.get("id") is not None}
        any_parts: set = set()  # entries with parts anywhere (the SQL's NOT EXISTS)
        parts_by_log: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # parts at this location
        for part in data.payments:
            if part.get("log_id") is None:
                continue
            any_parts.add(str(part["log_id"]))
            if str(part.get("location_id")) == str(loc_id):
                parts_by_log[str(part["log_id"])].append(part)
        self.logs_by_id = logs_by_id
        self.parts_by_log = parts_by_log
        self.rows: List[_Row] = []
        for log_id, log in logs_by_id.items():
            at_location = str(log.get("loc_id")) == str(loc_id)
            parts = parts_by_log.get(log_id)
            if not parts and (not at_location or log_id in any_parts):
                continue
            category = self.category_of(log)
            common = dict(
                key=log_id,
                log=log,
                approval_status=log.get("approval_status"),
                exit_time=parse_ts(log.get("exit_time")),
                created_at=parse_ts(log.get("created_at")),
                entry_time=parse_ts(log.get("entry_time")),
                category=category,
            )
            if not parts:
                self.rows.append(_Row(
                    payment_mode=log.get("payment_mode"),
                    payment_id=log.get("payment_id"),
                    payment_date=parse_ts(log.get("payment_date")),
                    amount=net_amount(log),
                    **common,
                ))
            else:
                for part in parts:
                    self.rows.append(_Row(
                        payment_mode=part.get("mode"),
                        payment_id=part.get("payment_id"),
                        payment_date=parse_ts(part.get("paid_at")) or parse_ts(log.get("payment_date")),
                        amount=num(part.get("amount")),
                        **common,
                    ))

    def category_of(self, log: Dict[str, Any]) -> str:
        vehicle = self.data.vehicles.get(str(log.get("veh_id"))) or {}
        catalogue = self.data.catalogue.get(str(vehicle.get("veh_det"))) or {}
        catalogue_type = str(catalogue.get("type") or "").strip()
        raw = catalogue_type if catalogue_type else str(vehicle.get("type") or "")
        return vehicle_category(raw.strip().lower())


# --- Dashboard flags (NULL behaves as in SQL: NULL NOT IN (...) is not true) ---

def _is_approved(row: _Row) -> bool:
    return row.approval_status == "approved"


def _is_processed(row: _Row, start: datetime, end: datetime) -> bool:
    return (_is_approved(row) and row.payment_mode is not None
            and row.payment_mode not in PAY_LATER_MODES and in_window(row.created_at, start, end))


def _revenue_date_in(row: _Row, start: datetime, end: datetime) -> bool:
    if row.payment_date is not None:
        return in_window(row.payment_date, start, end)
    if row.exit_time is not None:
        return in_window(row.exit_time, start, end)
    return in_window(row.created_at, start, end)


def _is_revenue(row: _Row, start: datetime, end: datetime) -> bool:
    return (_is_approved(row) and row.payment_mode is not None
            and row.payment_mode not in PAY_LATER_MODES and _revenue_date_in(row, start, end))


def _is_pay_later(row: _Row, start: datetime, end: datetime) -> bool:
    return _is_approved(row) and row.payment_mode in PAY_LATER_MODES and in_window(row.created_at, start, end)


def _is_pending(row: _Row, start: datetime, end: datetime) -> bool:
    return row.approval_status in ("pending", None) and in_window(row.entry_time, start, end)


def _bucket(mode: Optional[str]) -> str:
    m = (mode or "").lower()
    if m == "cash":
        return "cash"
    if m in CARD_MODES:
        return "card"
    if m in BANK_MODES:
        return "bank"
    return "upi"


def _log_revenue_date(log: Dict[str, Any]) -> Optional[datetime]:
    return parse_ts(log.get("payment_date")) or parse_ts(log.get("exit_time")) or parse_ts(log.get("created_at"))


def day_figures(ctx: DayContext, day: date) -> DayFigures:
    start, end = day_bounds(day)
    f = DayFigures(day=day)
    processed: Dict[str, set] = defaultdict(set)
    revenue_keys: Dict[str, set] = defaultdict(set)
    pay_later_keys: set = set()
    pending_keys: set = set()
    buckets = defaultdict(float)
    for row in ctx.rows:
        if _is_processed(row, start, end):
            processed[row.category].add(row.key)
        if _is_revenue(row, start, end):
            f.ticket_collections += row.amount
            buckets[_bucket(row.payment_mode)] += row.amount
            revenue_keys[row.category].add(row.key)
            if row.category == "4":
                f.revenue_4w += row.amount
            elif row.category == "2":
                f.revenue_2w += row.amount
            else:
                f.revenue_other += row.amount
        if _is_pay_later(row, start, end):
            f.pay_later_amount += row.amount
            pay_later_keys.add(row.key)
        if _is_pending(row, start, end):
            f.pending_amount += row.amount
            pending_keys.add(row.key)

    all_processed = set().union(*processed.values()) if processed else set()
    f.vehicles = len(all_processed)
    f.vehicles_4w = len(processed["4"])
    f.vehicles_2w = len(processed["2"])
    f.vehicles_other = len(processed["other"])
    f.collection_count = len(revenue_keys["4"]) + len(revenue_keys["2"]) + len(revenue_keys["other"])
    f.pay_later_count = len(pay_later_keys)
    f.pending_count = len(pending_keys)

    # Expenses: the expenses table only, on the business date (as the Dashboard).
    for expense in ctx.data.expenses:
        if parse_date(expense.get("date")) != day:
            continue
        amount = num(expense.get("amount"))
        f.expenses += amount
        mode = str(expense.get("payment_mode") or "").upper()
        if mode == "CASH":
            f.expenses_cash += amount
        elif mode == "UPI":
            f.expenses_upi += amount

    cash, upi, card, bank = buckets["cash"], buckets["upi"], buckets["card"], buckets["bank"]
    total = f.ticket_collections

    # withAdvances: visits paid from advance leave the UPI figure.
    advances = advance_summary(ctx, start, end)
    if advances is not None:
        used = advances["used"]
        upi = max(upi - used, 0.0)
        f.from_advance = used
        f.advance_received = advances["deposits"]

    # withRetailSales: counter sales join the collections.
    retail = retail_summary(ctx, start, end)
    if retail is not None:
        total += retail["total"]
        cash += retail["cash"]
        upi += retail["upi"]
        card += retail["card"]
        f.counter_sales = retail["total"]
        f.counter_sales_count = retail["count"]
        f.items_sold = retail["total"] + retail["ticket_items_total"]
        f.items_sold_count = retail["count"] + retail["ticket_items_count"]

    # withDuePayments: old dues collected (and paid from advance).
    dues = due_payments_summary(ctx, start, end)
    if dues is not None:
        total += dues["total"] + dues["from_advance"]
        cash += dues["cash"]
        upi += dues["upi"]
        card += dues["card"]
        f.from_advance += dues["from_advance"]
        f.old_dues_collected = dues["total"] + dues["from_advance"]

    f.collections, f.cash, f.upi, f.card, f.bank = total, cash, upi, card, bank
    return f


def advance_summary(ctx: DayContext, start: datetime, end: datetime) -> Optional[Dict[str, float]]:
    ledger = ctx.data.customer_ledger
    if ledger is None:
        return None
    loc = str(ctx.data.location.id)
    deposits = sum(
        num(e.get("amount")) for e in ledger
        if str(e.get("location_id")) == loc and e.get("kind") == "advance_deposit"
        and in_window(parse_ts(e.get("created_at")), start, end)
    )
    used = 0.0
    for log in ctx.logs_by_id.values():
        if log.get("approval_status") != "approved" or not in_window(_log_revenue_date(log), start, end):
            continue
        if str(log.get("loc_id")) == loc and log.get("payment_mode") == "advance":
            used += net_amount(log)
        # The advance part of split entries (parts recorded at this location).
        for part in ctx.parts_by_log.get(str(log["id"]), []):
            if part.get("mode") == "advance":
                used += num(part.get("amount"))
    return {"deposits": deposits, "used": used}


def retail_summary(ctx: DayContext, start: datetime, end: datetime) -> Optional[Dict[str, float]]:
    sales = ctx.data.retail_sales
    if sales is None:
        return None
    loc = str(ctx.data.location.id)
    out = {"total": 0.0, "cash": 0.0, "upi": 0.0, "card": 0.0, "count": 0,
           "ticket_items_total": 0.0, "ticket_items_count": 0}
    for sale in sales:
        if str(sale.get("location_id")) != loc or not in_window(parse_ts(sale.get("created_at")), start, end):
            continue
        amount = num(sale.get("total"))
        if sale.get("log_id") is None:
            out["total"] += amount
            out["count"] += 1
            mode = sale.get("payment_mode")
            if mode in ("cash", "upi", "card"):
                out[mode] += amount
        else:
            out["ticket_items_total"] += amount
            out["ticket_items_count"] += 1
    return out


def due_payments_summary(ctx: DayContext, start: datetime, end: datetime) -> Optional[Dict[str, float]]:
    ledger = ctx.data.due_ledger
    if ledger is None:
        return None
    loc = str(ctx.data.location.id)
    out = {"total": 0.0, "cash": 0.0, "upi": 0.0, "card": 0.0, "from_advance": 0.0, "count": 0}
    for entry in ledger:
        if str(entry.get("location_id")) != loc or not in_window(parse_ts(entry.get("created_at")), start, end):
            continue
        amount = -num(entry.get("amount"))
        kind = entry.get("kind")
        if kind == "payment":
            out["total"] += amount
            out["count"] += 1
            mode = entry.get("payment_mode")
            if mode in ("cash", "upi", "card"):
                out[mode] += amount
        elif kind == "paid_from_advance":
            out["from_advance"] += amount
    return out


# --------------------------------------------------------------------------
# Detail sections of the report day
# --------------------------------------------------------------------------

def _share_rows(rows: List[BreakdownRow], total: Optional[float] = None) -> List[BreakdownRow]:
    base = total if total is not None else sum(r.amount for r in rows)
    for r in rows:
        r.share = (r.amount / base * 100.0) if base else 0.0
    return rows


def upi_account_label(ctx: DayContext, payment_id: Optional[str]) -> str:
    if not payment_id:
        return "No account selected"
    account = ctx.data.upi_accounts.get(str(payment_id))
    if not account:
        return "Account not found (deleted?)"
    name = (account.get("account_name") or "").strip()
    if name:
        return name
    upi_id = (account.get("upi_id") or "").strip()
    return upi_id or "Unnamed UPI account (QR only)"


def payment_rows(ctx: DayContext, day: date, figures: DayFigures) -> List[BreakdownRow]:
    start, end = day_bounds(day)
    counts = defaultdict(set)
    accounts: Dict[str, BreakdownRow] = {}
    for row in ctx.rows:
        if not _is_revenue(row, start, end):
            continue
        counts[_bucket(row.payment_mode)].add(row.key)
        if (row.payment_mode or "").lower() in UPI_ACCOUNT_MODES:
            label = upi_account_label(ctx, row.payment_id)
            item = accounts.setdefault(label, BreakdownRow(label=label))
            item.amount += row.amount
            item.count += 1
    upi = BreakdownRow("UPI", figures.upi, len(counts["upi"]))
    children = sorted(accounts.values(), key=lambda r: -r.amount)
    rest = figures.upi - sum(c.amount for c in children)
    if children and rest > 0.5:
        children.append(BreakdownRow("Counter sales & other", rest))
    upi.children = _share_rows(children, figures.upi) if len(children) > 1 or rest > 0.5 else []
    rows = [
        BreakdownRow("Cash", figures.cash, len(counts["cash"])),
        upi,
        BreakdownRow("Card", figures.card, len(counts["card"])),
        BreakdownRow("Bank Transfer", figures.bank, len(counts["bank"])),
        BreakdownRow("From advance", figures.from_advance),
    ]
    rows = [r for r in rows if r.amount or r.count]
    return _share_rows(rows, figures.collections or None)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def service_shares(ctx: DayContext, log: Dict[str, Any]) -> List[Tuple[str, float]]:
    """OperationsReport.serviceSharesOf, in Python."""
    services = [s.strip() for s in str(log.get("service") or "").split(",") if s.strip()] or ["Unknown"]
    ticket = net_amount(log)
    items = min(max(num(log.get("items_total")), 0.0), max(ticket, 0.0))
    extra = min(max(num(log.get("extra_work_amount")), 0.0), max(ticket - items, 0.0))
    amount = ticket - items - extra
    vehicle = ctx.data.vehicles.get(str(log.get("veh_id"))) or {}
    types: List[str] = []
    for t in (_norm(vehicle.get("type")),):
        if not t:
            continue
        types.extend([t, "bike"] if t == "2" else [t, "car"] if t == "4" else [t])
    weights = []
    for service in services:
        price = 0.0
        for row in ctx.data.service_prices:
            if _norm(row.get("SERVICE")) == _norm(service) and _norm(row.get("VEHICLE")) in types:
                price = num(row.get("PRICE"))
                break
        weights.append(price)
    weight_total = sum(weights)
    shares: List[Tuple[str, float]] = []
    allocated = 0.0
    for i, service in enumerate(services):
        if i == len(services) - 1:
            share = amount - allocated
        else:
            raw = amount * weights[i] / weight_total if weight_total > 0 else amount / len(services)
            share = float(round(raw))
        allocated += share
        shares.append((service, share))
    if items > 0:
        shares.append(("Items sold", items))
    if extra > 0:
        shares.append(("Extra work", extra))
    return shares


def served_logs(ctx: DayContext, day: date) -> List[Dict[str, Any]]:
    """Approved entries of the day by revenue date, paid or Pay Later
    (the Reports / Operations definition of the day's work)."""
    start, end = day_bounds(day)
    loc = str(ctx.data.location.id)
    return [
        log for log in ctx.logs_by_id.values()
        if str(log.get("loc_id")) == loc and log.get("approval_status") == "approved"
        and in_window(_log_revenue_date(log), start, end)
    ]


def service_rows(ctx: DayContext, day: date) -> List[BreakdownRow]:
    rows: Dict[str, BreakdownRow] = {}
    for log in served_logs(ctx, day):
        for service, share in service_shares(ctx, log):
            item = rows.setdefault(service.lower(), BreakdownRow(label=service))
            item.amount += share
            item.count += 1
    ordered = sorted(rows.values(), key=lambda r: (-r.amount, -r.count, r.label))
    return _share_rows(ordered)


def vehicle_mix(figures: DayFigures) -> List[BreakdownRow]:
    rows = [
        BreakdownRow(CATEGORY_LABELS["4"], figures.revenue_4w, figures.vehicles_4w),
        BreakdownRow(CATEGORY_LABELS["2"], figures.revenue_2w, figures.vehicles_2w),
        BreakdownRow(CATEGORY_LABELS["other"], figures.revenue_other, figures.vehicles_other),
    ]
    total = sum(r.count for r in rows)
    for r in rows:
        r.share = (r.count / total * 100.0) if total else 0.0
    return [r for r in rows if r.count or r.amount]


def hourly_rows(ctx: DayContext, day: date) -> List[BreakdownRow]:
    start, end = day_bounds(day)
    hours = {h: BreakdownRow(label=hour_label(h)) for h in range(24)}
    seen = set()
    for row in ctx.rows:
        if _is_processed(row, start, end) and row.key not in seen:
            seen.add(row.key)
            hours[to_ist(row.created_at).hour].count += 1
        if _is_revenue(row, start, end):
            when = row.payment_date or row.exit_time or row.created_at
            hours[to_ist(when).hour].amount += row.amount
    active = [h for h in range(24) if hours[h].count or hours[h].amount]
    if not active:
        return []
    return [hours[h] for h in range(min(active), max(active) + 1)]


def staff_rows(ctx: DayContext, day: date) -> List[BreakdownRow]:
    start, end = day_bounds(day)
    counts: Dict[str, BreakdownRow] = {}
    seen = set()
    for row in ctx.rows:
        if row.key in seen or not _is_processed(row, start, end):
            continue
        seen.add(row.key)
        who = ctx.data.staff_names.get(str(row.log.get("created_by"))) or "Unknown"
        item = counts.setdefault(who, BreakdownRow(label=who))
        item.count += 1
        item.amount += net_amount(row.log)
    return sorted(counts.values(), key=lambda r: (-r.count, r.label))


def spending(ctx: DayContext, day: date) -> Spending:
    out = Spending()
    categories: Dict[str, float] = defaultdict(float)
    for e in ctx.data.expenses:
        if parse_date(e.get("date")) == day:
            amount = num(e.get("amount"))
            out.expenses += amount
            categories[e.get("category_name") or "Expense"] += amount
    for e in ctx.data.staff_expenses:
        if parse_date(e.get("date")) == day:
            amount = num(e.get("amount"))
            out.staff_expenses += amount
            label = "Staff incentive" if e.get("category") == "incentive" else "Staff expenses"
            categories[label] += amount
    for p in ctx.data.salary_payments:
        if parse_date(p.get("payment_date")) == day:
            out.salaries += num(p.get("amount"))
    for p in ctx.data.staff_payments:
        if parse_date(p.get("payment_date")) == day and p.get("type") in ("Advance", "Salary", "Salary_Carryforward"):
            out.staff_payments += num(p.get("amount"))
    if out.salaries + out.staff_payments:
        categories["Salaries & staff advances"] += out.salaries + out.staff_payments
    rows = [BreakdownRow(label=k, amount=v) for k, v in categories.items() if v]
    out.by_category = _share_rows(sorted(rows, key=lambda r: -r.amount))
    return out


def customer_counts(ctx: DayContext, day: date) -> Tuple[int, int]:
    start, end = day_bounds(day)
    served = set()
    for row in ctx.rows:
        if _is_processed(row, start, end) and row.log.get("cust_id"):
            served.add(str(row.log["cust_id"]))
    new = 0
    for cust_id in served:
        local = ctx.data.local_customers.get(cust_id) or {}
        if in_window(parse_ts(local.get("first_seen_at")), start, end):
            new += 1
    return len(served), new


def _payment_text(ctx: DayContext, log: Dict[str, Any]) -> Tuple[str, str]:
    parts = ctx.parts_by_log.get(str(log.get("id")))
    if parts:
        pieces = [f"{mode_label(p.get('mode'))} {num(p.get('amount')):.0f}" for p in parts]
        accounts = sorted({upi_account_label(ctx, p.get("payment_id")) for p in parts if p.get("mode") == "upi"})
        return "Split: " + " + ".join(pieces), ", ".join(accounts)
    mode = (log.get("payment_mode") or "").lower()
    account = upi_account_label(ctx, log.get("payment_id")) if mode in UPI_ACCOUNT_MODES else ""
    return mode_label(log.get("payment_mode")), account


def transactions(ctx: DayContext, day: date) -> List[TransactionRow]:
    """Every entry the day touched: created, worked on, or paid that day."""
    start, end = day_bounds(day)
    loc = str(ctx.data.location.id)
    out: List[TransactionRow] = []
    for log in ctx.logs_by_id.values():
        if str(log.get("loc_id")) != loc:
            continue
        stamps = [parse_ts(log.get(k)) for k in ("created_at", "entry_time", "exit_time", "payment_date")]
        stamps += [parse_ts(p.get("paid_at")) for p in ctx.parts_by_log.get(str(log.get("id")), [])]
        if not any(in_window(s, start, end) for s in stamps):
            continue
        vehicle = ctx.data.vehicles.get(str(log.get("veh_id"))) or {}
        model = ctx.data.catalogue.get(str(vehicle.get("veh_det"))) or {}
        cust_id = str(log.get("cust_id")) if log.get("cust_id") else ""
        local = ctx.data.local_customers.get(cust_id) or {}
        cust = ctx.data.customers.get(cust_id) or {}
        payment, account = _payment_text(ctx, log)
        status = "Approved" if log.get("approval_status") == "approved" else "Pending"
        model_text = " ".join(x for x in (model.get("Vehicle Brands"), model.get("Models")) if x)
        out.append(TransactionRow(
            created_at=parse_ts(log.get("created_at")),
            vehicle_number=str(vehicle.get("number_plate") or ""),
            vehicle_model=model_text,
            vehicle_category=CATEGORY_LABELS[ctx.category_of(log)],
            customer=str(local.get("name") or cust.get("name") or ""),
            phone=str(cust.get("phone") or ""),
            service=str(log.get("service") or ""),
            amount=net_amount(log),
            discount=num(log.get("discount")),
            payment=payment,
            upi_account=account,
            status=status,
            entry_type=str(log.get("entry_type") or ""),
            workshop=str(log.get("workshop") or ""),
            remarks=str(log.get("remarks") or ""),
            recorded_by=ctx.data.staff_names.get(str(log.get("created_by")), ""),
        ))
    epoch = datetime.min.replace(tzinfo=start.tzinfo)
    return sorted(out, key=lambda t: t.created_at or epoch)


def build_location_report(data: LocationDataset, day: date, trend_days: int = 7) -> LocationReport:
    ctx = DayContext(data)
    figures = day_figures(ctx, day)
    first = max(data.first_day, day - timedelta(days=trend_days - 1))
    trend = [day_figures(ctx, first + timedelta(days=i)) for i in range((day - first).days)] + [figures]
    prev_day = day - timedelta(days=1)
    week_ago = day - timedelta(days=7)
    previous = next((t for t in trend if t.day == prev_day), None)
    if previous is None and data.first_day <= prev_day:
        previous = day_figures(ctx, prev_day)
    last_week = day_figures(ctx, week_ago) if data.first_day <= week_ago else None
    served, new = customer_counts(ctx, day)
    return LocationReport(
        location=data.location,
        day=day,
        figures=figures,
        previous_day=previous,
        last_week=last_week,
        trend=trend,
        payments=payment_rows(ctx, day, figures),
        services=service_rows(ctx, day),
        vehicle_mix=vehicle_mix(figures),
        hourly=hourly_rows(ctx, day),
        staff=staff_rows(ctx, day),
        spending=spending(ctx, day),
        cash_balance=data.cash_balance,
        customers_served=served,
        customers_new=new,
        transactions=transactions(ctx, day),
        warnings=list(data.warnings),
    )


def iter_days(first: date, last: date) -> Iterable[date]:
    d = first
    while d <= last:
        yield d
        d += timedelta(days=1)
