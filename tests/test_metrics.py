"""The worked example's answers were derived by hand from the SQL in
private.dashboard_summary_body and the other functions listed in
petalog_reports/metrics.py."""

import pytest

from petalog_reports.metrics import (
    DayContext,
    build_location_report,
    day_figures,
    service_shares,
    vehicle_category,
)
from tests.factories import DAY, worked_example


@pytest.fixture
def report():
    return build_location_report(worked_example(), DAY)


def test_dashboard_vehicle_counts(report):
    f = report.figures
    # L1 cash, L2 upi, L4 split (cash/upi parts), L7 advance. Not L3 (Pay Later),
    # L5 (pending), L6 (created yesterday), L8 (approved with no payment mode).
    assert f.vehicles == 4
    assert (f.vehicles_4w, f.vehicles_2w, f.vehicles_other) == (2, 1, 1)


def test_dashboard_collections(report):
    f = report.figures
    assert f.ticket_collections == 1600  # 500 + 250 + 200 + 100 + 350 (settled) + 200
    assert f.collections == 1850  # + counter sale 100 + old dues 120 + dues from advance 30
    assert f.cash == 1150
    assert f.upi == 470  # 550 - 200 advance used + 120 dues
    assert f.card == 0 and f.bank == 0
    assert f.from_advance == 230
    assert f.cash + f.upi + f.card + f.bank + f.from_advance == f.collections
    assert f.collection_count == 5


def test_pay_later_pending_and_extras(report):
    f = report.figures
    assert (f.pay_later_count, f.pay_later_amount) == (2, 550)
    assert (f.pending_count, f.pending_amount) == (1, 600)
    assert f.advance_received == 1000
    assert f.counter_sales == 100 and f.items_sold == 180 and f.items_sold_count == 2
    assert f.old_dues_collected == 150
    assert (f.expenses, f.expenses_cash, f.expenses_upi) == (350, 250, 100)


def test_spending_and_net(report):
    s = report.spending
    assert (s.expenses, s.staff_expenses, s.salaries, s.staff_payments) == (350, 50, 700, 300)
    assert s.total == 1400
    assert report.net == 450
    assert report.cash_balance == 4321.5


def test_payment_rows_with_upi_accounts(report):
    rows = {r.label: r for r in report.payments}
    assert rows["Cash"].amount == 1150
    assert rows["UPI"].amount == 470
    accounts = {c.label: c.amount for c in rows["UPI"].children}
    assert accounts["Shop GPay"] == 350  # L2 250 + L4 part 100
    assert accounts["Counter sales, old dues & plans"] == 120
    assert rows["From advance"].amount == 230
    assert round(sum(r.share for r in report.payments)) == 100


def test_service_split_by_catalogue_price():
    ctx = DayContext(worked_example())
    shares = dict(service_shares(ctx, ctx.logs_by_id["L4"]))
    # 450 shared 600:200 -> 338 (rounded) and the remainder 112.
    assert shares == {"Foam Wash": 338.0, "Interior": 112.0}


def test_service_rows_include_pay_later_work(report):
    labels = [r.label for r in report.services]
    assert "Foam Wash" in labels and "Bike Wash" in labels
    total = sum(r.amount for r in report.services)
    # Approved entries by revenue date: L1 500, L2 250, L3 400, L4 450, L7 200, and
    # L8 (approved, no payment mode) 999. Not L6: its work was yesterday; only its
    # settlement money is today's (in collections, not in the service table).
    assert total == 500 + 250 + 400 + 450 + 200 + 999


def test_customers_staff_hourly_transactions(report):
    assert report.customers_served == 4
    assert report.customers_new == 1  # c-1 first seen today
    assert report.staff[0].label == "Ravi" and report.staff[0].count == 4
    assert report.busiest_hour.label == "10 AM"
    numbers = {t.vehicle_number for t in report.transactions}
    assert "KL07AB1234" in numbers
    l1 = next(t for t in report.transactions if t.vehicle_number == "KL07AB1234" and t.payment == "Cash")
    assert l1.customer == "Local Name" and l1.vehicle_model == "Maruti Swift"
    assert any(t.payment.startswith("Split:") for t in report.transactions)
    assert any(t.status == "Pending" for t in report.transactions)


def test_comparisons_exist(report):
    assert report.previous_day is not None and report.last_week is not None
    assert len(report.trend) == 7 and report.trend[-1].day == DAY
    assert report.previous_day.expenses == 999


def test_missing_optional_tables_are_left_out():
    data = worked_example()
    data.retail_sales = None
    data.due_ledger = None
    data.customer_ledger = None
    f = day_figures(DayContext(data), DAY)
    assert f.collections == 1600
    assert f.upi == 550  # advance not moved out when advances are unavailable
    assert f.from_advance == 0


@pytest.mark.parametrize("raw,expected", [
    ("2", "2"), ("2 wheeler", "2"), ("4", "4"), ("1", "4"), ("hatch back", "4"),
    ("car", "4"), ("suv", "4"), ("", "other"), ("truck", "other"),
])
def test_vehicle_category(raw, expected):
    assert vehicle_category(raw) == expected
