"""Plain data objects shared across the service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional


@dataclass
class Owner:
    id: str
    email: Optional[str]
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: Optional[bool] = True
    role: str = "owner"

    @property
    def display_name(self) -> str:
        name = f"{(self.first_name or '').strip()} {(self.last_name or '').strip()}".strip()
        return name or (self.email or self.id)

    @property
    def greeting_name(self) -> str:
        return (self.first_name or "").strip() or self.display_name

    @property
    def is_enabled(self) -> bool:
        # users.status false = disabled; NULL counts as enabled (as in the app).
        return self.status is not False


@dataclass
class Schedule:
    user_id: str
    templateno: int = 1
    preferred_time: time = time(21, 0)
    timezone: str = "Asia/Kolkata"
    is_active: bool = True
    has_row: bool = True  # False = owner without a user_schedules row (app defaults)


@dataclass
class Location:
    id: str
    name: str
    logo_url: Optional[str] = None
    own_id: Optional[str] = None
    is_active: bool = True
    billing_status: Optional[str] = None
    city: Optional[str] = None

    @property
    def is_billing_lapsed(self) -> bool:
        return (self.billing_status or "").lower() in ("read_only", "archived")


@dataclass
class LocationDataset:
    """Every raw row needed for one location's report, over a window of days."""

    location: Location
    first_day: date
    last_day: date
    logs: List[Dict[str, Any]] = field(default_factory=list)
    payments: List[Dict[str, Any]] = field(default_factory=list)  # ticket_payments
    vehicles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    catalogue: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Vehicles_in_india
    customers: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # cust
    local_customers: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # cust_location by customer_id
    upi_accounts: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # owner_payment_details
    service_prices: List[Dict[str, Any]] = field(default_factory=list)
    staff_names: Dict[str, str] = field(default_factory=dict)
    # None = the table/feature is not installed (left out, as the app does).
    retail_sales: Optional[List[Dict[str, Any]]] = None
    customer_ledger: Optional[List[Dict[str, Any]]] = None
    due_ledger: Optional[List[Dict[str, Any]]] = None
    expenses: List[Dict[str, Any]] = field(default_factory=list)
    staff_expenses: List[Dict[str, Any]] = field(default_factory=list)
    salary_payments: List[Dict[str, Any]] = field(default_factory=list)
    staff_payments: List[Dict[str, Any]] = field(default_factory=list)
    cash_balance: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class DayFigures:
    """One location-day, defined exactly like the PetaLog dashboard."""

    day: date
    vehicles: int = 0
    vehicles_4w: int = 0
    vehicles_2w: int = 0
    vehicles_other: int = 0
    collections: float = 0.0  # dashboard "Collections": tickets + counter sales + old dues
    ticket_collections: float = 0.0
    collection_count: int = 0
    cash: float = 0.0
    upi: float = 0.0
    card: float = 0.0
    bank: float = 0.0
    from_advance: float = 0.0
    revenue_4w: float = 0.0
    revenue_2w: float = 0.0
    revenue_other: float = 0.0
    pay_later_amount: float = 0.0
    pay_later_count: int = 0
    pending_count: int = 0
    pending_amount: float = 0.0
    expenses: float = 0.0
    expenses_cash: float = 0.0
    expenses_upi: float = 0.0
    counter_sales: float = 0.0
    counter_sales_count: int = 0
    items_sold: float = 0.0
    items_sold_count: int = 0
    advance_received: float = 0.0
    old_dues_collected: float = 0.0

    @property
    def avg_per_vehicle(self) -> float:
        return self.ticket_collections / self.collection_count if self.collection_count else 0.0

    @property
    def has_activity(self) -> bool:
        return bool(
            self.vehicles or self.collections or self.pay_later_count or self.pending_count
            or self.expenses or self.counter_sales_count or self.advance_received
        )


@dataclass
class BreakdownRow:
    label: str
    amount: float = 0.0
    count: int = 0
    share: float = 0.0  # percent of the section total
    children: List["BreakdownRow"] = field(default_factory=list)
    note: Optional[str] = None


@dataclass
class Spending:
    expenses: float = 0.0
    staff_expenses: float = 0.0
    salaries: float = 0.0
    staff_payments: float = 0.0
    by_category: List[BreakdownRow] = field(default_factory=list)

    @property
    def total(self) -> float:
        return self.expenses + self.staff_expenses + self.salaries + self.staff_payments


@dataclass
class TransactionRow:
    created_at: Optional[datetime]
    vehicle_number: str
    vehicle_model: str
    vehicle_category: str
    customer: str
    phone: str
    service: str
    amount: float
    discount: float
    payment: str
    upi_account: str
    status: str
    entry_type: str
    workshop: str
    remarks: str
    recorded_by: str


@dataclass
class LocationReport:
    location: Location
    day: date
    figures: DayFigures
    previous_day: Optional[DayFigures] = None
    last_week: Optional[DayFigures] = None
    trend: List[DayFigures] = field(default_factory=list)  # oldest first, ends at `day`
    payments: List[BreakdownRow] = field(default_factory=list)
    services: List[BreakdownRow] = field(default_factory=list)
    vehicle_mix: List[BreakdownRow] = field(default_factory=list)
    hourly: List[BreakdownRow] = field(default_factory=list)  # label = hour label, count, amount
    staff: List[BreakdownRow] = field(default_factory=list)
    spending: Spending = field(default_factory=Spending)
    cash_balance: Optional[float] = None
    customers_served: int = 0
    customers_new: int = 0
    transactions: List[TransactionRow] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def net(self) -> float:
        return self.figures.collections - self.spending.total

    @property
    def customers_returning(self) -> int:
        return max(self.customers_served - self.customers_new, 0)

    @property
    def busiest_hour(self) -> Optional[BreakdownRow]:
        rows = [r for r in self.hourly if r.count > 0]
        return max(rows, key=lambda r: (r.count, r.amount)) if rows else None


@dataclass
class OwnerReport:
    owner: Owner
    day: date
    template_no: int
    locations: List[LocationReport]
    generated_at: datetime
    timezone: str = "Asia/Kolkata"

    @property
    def is_multi(self) -> bool:
        return len(self.locations) > 1

    @property
    def has_activity(self) -> bool:
        return any(r.figures.has_activity for r in self.locations)

    def total(self, attr: str) -> float:
        return sum(getattr(r.figures, attr) for r in self.locations)

    @property
    def total_net(self) -> float:
        return sum(r.net for r in self.locations)

    @property
    def total_spending(self) -> float:
        return sum(r.spending.total for r in self.locations)

    def total_for(self, which: str, attr: str) -> Optional[float]:
        """Sum of a figure over the comparison day ('previous_day' / 'last_week')."""
        values = [getattr(r, which) for r in self.locations]
        if any(v is None for v in values):
            return None
        return sum(getattr(v, attr) for v in values)
