"""All Supabase reads and writes.

Uses the service-role key, so row-level security does not apply: every query
here filters by owner / location explicitly. Each list query is paged
(PostgREST returns at most 1,000 rows per request) and `in` filters are sent
in chunks to keep URLs short.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set

from .config import Settings
from .models import Location, LocationDataset, Owner, Schedule
from .timeutil import iso_z, parse_clock, range_bounds

logger = logging.getLogger(__name__)

PAGE_SIZE = 1000
IN_CHUNK = 150

LOG_COLUMNS = (
    "id,loc_id,veh_id,cust_id,created_by,approval_status,payment_mode,payment_id,"
    "amount,discount,total,items_total,extra_work_name,extra_work_amount,service,"
    "entry_type,workshop,remarks,created_at,entry_time,exit_time,payment_date"
)
PAYMENT_COLUMNS = "id,log_id,location_id,mode,amount,payment_id,source,paid_at"


class RepositoryError(Exception):
    pass


def _chunks(values: Sequence[Any], size: int = IN_CHUNK) -> Iterable[List[Any]]:
    values = list(values)
    for i in range(0, len(values), size):
        yield values[i:i + size]


def _ids(values: Iterable[Any]) -> List[str]:
    return sorted({str(v) for v in values if v not in (None, "")})


class SupabaseRepository:
    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        self._client = client

    # ------------------------------------------------------------------ setup
    @property
    def client(self):
        if self._client is None:
            if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
                raise RepositoryError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
            from supabase import create_client
            from supabase.lib.client_options import ClientOptions

            options = ClientOptions(
                schema="public",
                auto_refresh_token=False,
                persist_session=False,
                postgrest_client_timeout=30,
            )
            self._client = create_client(
                self.settings.supabase_url, self.settings.supabase_service_role_key, options=options
            )
        return self._client

    def table(self, name: str):
        return self.client.table(name)

    # ---------------------------------------------------------------- helpers
    def _all(self, build: Callable[[], Any], order: Optional[str] = "id") -> List[Dict[str, Any]]:
        """Run a query page by page until every row is read."""
        rows: List[Dict[str, Any]] = []
        offset = 0
        while True:
            query = build()
            if order:
                query = query.order(order)
            page = query.range(offset, offset + PAGE_SIZE - 1).execute().data or []
            rows.extend(page)
            if len(page) < PAGE_SIZE:
                return rows
            offset += PAGE_SIZE

    def _in(self, table: str, columns: str, column: str, values: Iterable[Any],
            extra: Optional[Callable[[Any], Any]] = None, order: Optional[str] = "id") -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for chunk in _chunks(_ids(values)):
            def build(chunk=chunk):
                q = self.table(table).select(columns).in_(column, chunk)
                return extra(q) if extra else q
            out.extend(self._all(build, order=order))
        return out

    def _optional(self, label: str, fn: Callable[[], Any], warnings: List[str]):
        """For tables/functions the app also treats as optional."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - logged and reported in the email footer
            logger.warning("Optional source %s unavailable: %s", label, exc)
            warnings.append(label)
            return None

    # ---------------------------------------------------------- owners, plans
    def get_owners(self, ids: Optional[Sequence[str]] = None) -> Dict[str, Owner]:
        columns = "id,email,first_name,last_name,status,role"
        if ids is not None:
            rows = self._in("users", columns, "id", ids, extra=lambda q: q.eq("role", "owner"))
        else:
            rows = self._all(lambda: self.table("users").select(columns).eq("role", "owner"))
        return {
            str(r["id"]): Owner(
                id=str(r["id"]), email=(r.get("email") or "").strip() or None,
                first_name=r.get("first_name"), last_name=r.get("last_name"),
                status=r.get("status"), role=r.get("role") or "owner",
            )
            for r in rows
        }

    def get_schedules(self, user_ids: Optional[Sequence[str]] = None,
                      active_only: bool = False) -> Dict[str, Schedule]:
        columns = "user_id,templateno,preferred_time,timezone,is_active"

        def extra(q):
            return q.eq("is_active", True) if active_only else q

        if user_ids is not None:
            rows = self._in("user_schedules", columns, "user_id", user_ids, extra=extra, order="user_id")
        else:
            rows = self._all(lambda: extra(self.table("user_schedules").select(columns)), order="user_id")
        out: Dict[str, Schedule] = {}
        for r in rows:
            try:
                template = int(r.get("templateno") or 1)
            except (TypeError, ValueError):
                template = 1
            out[str(r["user_id"])] = Schedule(
                user_id=str(r["user_id"]),
                templateno=template if template in (1, 2, 3) else 1,
                preferred_time=parse_clock(r.get("preferred_time")),
                timezone=(r.get("timezone") or "Asia/Kolkata"),
                is_active=r.get("is_active") is not False,
            )
        return out

    def set_schedule_active(self, user_id: str, active: bool) -> bool:
        resp = self.table("user_schedules").update({"is_active": active}).eq("user_id", user_id).execute()
        return bool(resp.data)

    def get_owner_location_ids(self, owner_ids: Sequence[str]) -> Dict[str, List[str]]:
        """Locations an owner may see: locations.own_id plus location_owners
        (co-owners), as private.dashboard_user_can_access_location does."""
        result: Dict[str, Set[str]] = {str(o): set() for o in owner_ids}
        for row in self._in("locations", "id,own_id", "own_id", owner_ids):
            result.setdefault(str(row["own_id"]), set()).add(str(row["id"]))
        for row in self._in("location_owners", "owner_id,location_id", "owner_id", owner_ids, order="location_id"):
            result.setdefault(str(row["owner_id"]), set()).add(str(row["location_id"]))
        return {k: sorted(v) for k, v in result.items()}

    def get_locations(self, ids: Sequence[str]) -> Dict[str, Location]:
        rows = self._in("locations", "id,name,logo_url,own_id,is_active,city", "id", ids)
        statuses: Dict[str, str] = {}
        try:
            for r in self._in("view_locations_billing", "id,status", "id", ids):
                statuses[str(r["id"])] = r.get("status")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Billing status unavailable, not filtering on it: %s", exc)
        return {
            str(r["id"]): Location(
                id=str(r["id"]), name=(r.get("name") or "Location").strip(), logo_url=r.get("logo_url") or None,
                own_id=r.get("own_id"), is_active=r.get("is_active") is not False,
                billing_status=statuses.get(str(r["id"])), city=r.get("city"),
            )
            for r in rows
        }

    # -------------------------------------------------------- location data
    def load_location_dataset(self, location: Location, first_day: date, last_day: date) -> LocationDataset:
        settings = self.settings
        start, end = range_bounds(first_day, last_day)
        s, e = iso_z(start), iso_z(end)
        loc = location.id
        data = LocationDataset(location=location, first_day=first_day, last_day=last_day)
        warnings = data.warnings

        window = ",".join(
            f"and({col}.gte.{s},{col}.lt.{e})" for col in ("created_at", "entry_time", "payment_date", "exit_time")
        )
        logs = {
            str(r["id"]): r for r in self._all(
                lambda: self.table(settings.logs_table).select(LOG_COLUMNS).eq("loc_id", loc).or_(window)
            )
        }
        # Parts of those entries (any location: an entry with parts anywhere is
        # read from its parts), plus parts paid here in the window, e.g. Pay
        # Later settled today for an older entry.
        payments = {str(p["id"]): p for p in self._in("ticket_payments", PAYMENT_COLUMNS, "log_id", logs.keys())}
        for p in self._all(lambda: self.table("ticket_payments").select(PAYMENT_COLUMNS)
                           .eq("location_id", loc).gte("paid_at", s).lt("paid_at", e)):
            payments[str(p["id"])] = p
        missing = [i for i in _ids(p.get("log_id") for p in payments.values()) if i not in logs]
        for r in self._in(settings.logs_table, LOG_COLUMNS, "id", missing):
            logs[str(r["id"])] = r
        if missing:
            for p in self._in("ticket_payments", PAYMENT_COLUMNS, "log_id", missing):
                payments[str(p["id"])] = p
        data.logs = list(logs.values())
        data.payments = list(payments.values())

        vehicles = self._in("vehicle", "id,number_plate,type,veh_det", "id", (r.get("veh_id") for r in data.logs))
        data.vehicles = {str(v["id"]): v for v in vehicles}
        catalogue = self._optional("vehicle models", lambda: self._in(
            # '*': the "Vehicle Brands" column name has a space, which does not
            # survive query-string encoding reliably; the table has 4 columns.
            "Vehicles_in_india", "*", "id",
            (v.get("veh_det") for v in vehicles)), warnings) or []
        data.catalogue = {str(c["id"]): c for c in catalogue}

        cust_ids = _ids(r.get("cust_id") for r in data.logs)
        data.customers = {str(c["id"]): c for c in self._in("cust", "id,name,phone", "id", cust_ids)}
        local = self._optional("customer records", lambda: self._in(
            "cust_location", "customer_id,name,first_seen_at", "customer_id", cust_ids,
            extra=lambda q: q.eq("location_id", loc), order="customer_id"), warnings) or []
        data.local_customers = {str(c["customer_id"]): c for c in local}

        payment_ids = _ids([r.get("payment_id") for r in data.logs] + [p.get("payment_id") for p in data.payments])
        accounts = self._optional("UPI accounts", lambda: self._in(
            "owner_payment_details", "id,account_name,upi_id", "id", payment_ids), warnings) or []
        data.upi_accounts = {str(a["id"]): a for a in accounts}

        data.service_prices = self._optional("service prices", lambda: self._all(
            lambda: self.table("Service_prices").select("id,SERVICE,VEHICLE,PRICE").eq("locationid", loc)),
            warnings) or []

        staff = self._optional("staff names", lambda: self._in(
            "users", "id,first_name,last_name,email", "id", (r.get("created_by") for r in data.logs)), warnings) or []
        data.staff_names = {
            str(u["id"]): (f"{u.get('first_name') or ''} {u.get('last_name') or ''}".strip() or u.get("email") or "Unknown")
            for u in staff
        }

        data.retail_sales = self._optional("counter sales", lambda: self._all(
            lambda: self.table("retail_sales").select("id,location_id,total,payment_mode,log_id,created_at")
            .eq("location_id", loc).gte("created_at", s).lt("created_at", e)), warnings)
        data.customer_ledger = self._optional("customer advances", lambda: self._all(
            lambda: self.table("customer_ledger").select("id,location_id,kind,amount,payment_mode,created_at")
            .eq("location_id", loc).gte("created_at", s).lt("created_at", e)), warnings)
        data.due_ledger = self._optional("old dues", lambda: self._all(
            lambda: self.table("customer_due_ledger").select("id,location_id,kind,amount,payment_mode,created_at")
            .eq("location_id", loc).gte("created_at", s).lt("created_at", e)), warnings)

        expenses = self._optional("expenses", lambda: self._all(
            lambda: self.table("expenses").select("id,branch_id,date,amount,payment_mode,category_id")
            .eq("branch_id", loc).gte("date", first_day.isoformat()).lte("date", last_day.isoformat())),
            warnings) or []
        categories = self._optional("expense categories", lambda: self._in(
            "expense_categories", "id,name", "id", (x.get("category_id") for x in expenses)), []) or []
        names = {str(c["id"]): c.get("name") for c in categories}
        for x in expenses:
            x["category_name"] = names.get(str(x.get("category_id"))) or "Expense"
        data.expenses = expenses

        day = last_day.isoformat()
        data.staff_expenses = self._optional("staff expenses", lambda: self._all(
            lambda: self.table("staff_expenses").select("id,branch_id,date,amount,category,payment_mode")
            .eq("branch_id", loc).eq("date", day)), warnings) or []
        data.salary_payments = self._optional("salary payments", lambda: self._all(
            lambda: self.table("daily_weekly_salary_payments").select("id,branch_id,payment_date,amount")
            .eq("branch_id", loc).eq("payment_date", day)), warnings) or []
        data.staff_payments = self._optional("staff payments", lambda: self._all(
            lambda: self.table("payment_data").select("id,location_id,payment_date,amount,type")
            .eq("location_id", loc).eq("payment_date", day)), warnings) or []

        data.cash_balance = self.get_cash_balance(loc)
        return data

    def get_cash_balance(self, location_id: str) -> Optional[float]:
        """Cash in hand now, via the optional email_report_cash_balance RPC
        (sql/001_report_deliveries.sql). None when it is not installed."""
        try:
            value = self.client.rpc("email_report_cash_balance", {"p_location_id": location_id}).execute().data
        except Exception as exc:  # noqa: BLE001
            logger.info("Cash balance not available for %s: %s", location_id, exc)
            return None
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            value = value.get("balance")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


def dataset_window(day: date, days_back: int = 7):
    """Report day plus the comparison days (previous day and a week before)."""
    return day - timedelta(days=days_back), day
