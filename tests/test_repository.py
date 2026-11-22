from datetime import timedelta

from petalog_reports.config import Settings
from petalog_reports.metrics import build_location_report
from petalog_reports.repository import PAGE_SIZE, SupabaseRepository
from tests.factories import DAY, LOC, at, log, worked_example
from tests.fake_supabase import FakeSupabase


def tables_from_example():
    ds = worked_example()
    payments = [dict(p, id=f"tp-{i}") for i, p in enumerate(ds.payments)]
    return {
        "log-man": ds.logs + [log("OLD", mode="cash", amount=1, day=DAY - timedelta(days=20))],
        "ticket_payments": payments,
        "vehicle": list(ds.vehicles.values()),
        "Vehicles_in_india": list(ds.catalogue.values()),
        "cust": list(ds.customers.values()),
        "cust_location": [dict(v, location_id=LOC) for v in ds.local_customers.values()],
        "owner_payment_details": list(ds.upi_accounts.values()),
        "Service_prices": [dict(p, id=i) for i, p in enumerate(ds.service_prices)],
        "users": [{"id": "u-staff", "first_name": "Ravi", "last_name": "", "role": "worker"},
                  {"id": "o-1", "email": "owner@example.com", "first_name": "Anu", "role": "owner", "status": True},
                  {"id": "o-2", "email": "co@example.com", "role": "owner", "status": None}],
        "retail_sales": [dict(r, id=f"r{i}") for i, r in enumerate(ds.retail_sales)],
        "customer_ledger": [dict(r, id=f"cl{i}") for i, r in enumerate(ds.customer_ledger)],
        "customer_due_ledger": [dict(r, id=f"d{i}") for i, r in enumerate(ds.due_ledger)],
        "expenses": [dict(r, id=f"e{i}", category_id="cat-1" if i == 0 else None) for i, r in enumerate(ds.expenses)],
        "expense_categories": [{"id": "cat-1", "name": "Soap"}],
        "staff_expenses": [dict(r, id="se1") for r in ds.staff_expenses],
        "daily_weekly_salary_payments": [dict(r, id="sp1") for r in ds.salary_payments],
        "payment_data": [dict(r, id=f"pd{i}") for i, r in enumerate(ds.staff_payments)],
        "locations": [{"id": LOC, "name": "Luxe Lane", "own_id": "o-1", "is_active": True},
                      {"id": "loc-2", "name": "Second", "own_id": "o-9", "is_active": True}],
        "location_owners": [{"owner_id": "o-2", "location_id": LOC}, {"owner_id": "o-1", "location_id": "loc-2"}],
        "view_locations_billing": [{"id": LOC, "status": "active"}, {"id": "loc-2", "status": "read_only"}],
        "user_schedules": [{"user_id": "o-1", "templateno": 3, "preferred_time": "21:00:00",
                            "timezone": "Asia/Kolkata", "is_active": True}],
    }


def repo(fake):
    return SupabaseRepository(Settings(), client=fake)


def test_dataset_from_supabase_matches_worked_example():
    fake = FakeSupabase(tables_from_example(), rpcs={"email_report_cash_balance": lambda p: {"balance": 4321.5}})
    r = repo(fake)
    locations = r.get_locations([LOC])
    ds = r.load_location_dataset(locations[LOC], DAY - timedelta(days=7), DAY)
    assert {row["id"] for row in ds.logs} == {"L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"}
    assert ds.warnings == []
    report = build_location_report(ds, DAY)
    expected = build_location_report(worked_example(), DAY)
    assert report.figures == expected.figures
    assert report.spending.total == expected.spending.total
    assert report.cash_balance == 4321.5
    assert {c.label for c in report.spending.by_category} >= {"Soap"}


def test_old_entry_settled_today_is_loaded():
    tables = tables_from_example()
    tables["log-man"].append(log("L9", mode="split", amount=700, day=DAY - timedelta(days=40)))
    tables["ticket_payments"] += [
        {"id": "tp-x", "log_id": "L9", "location_id": LOC, "mode": "credit", "amount": 700, "source": "checkout"},
        {"id": "tp-y", "log_id": "L9", "location_id": LOC, "mode": "upi", "amount": 700,
         "source": "settlement", "paid_at": at(DAY, 19)},
    ]
    r = repo(FakeSupabase(tables))
    ds = r.load_location_dataset(r.get_locations([LOC])[LOC], DAY - timedelta(days=7), DAY)
    assert "L9" in {row["id"] for row in ds.logs}
    assert build_location_report(ds, DAY).figures.ticket_collections == 1600 + 700


def test_optional_tables_missing_are_reported_not_fatal():
    fake = FakeSupabase(tables_from_example(), broken={"retail_sales", "customer_due_ledger"})
    r = repo(fake)
    ds = r.load_location_dataset(r.get_locations([LOC])[LOC], DAY - timedelta(days=7), DAY)
    assert ds.retail_sales is None and ds.due_ledger is None
    assert set(ds.warnings) == {"counter sales", "old dues"}
    assert ds.cash_balance is None  # RPC not installed


def test_owner_locations_union_of_own_id_and_co_owner():
    r = repo(FakeSupabase(tables_from_example()))
    assert r.get_owner_location_ids(["o-1", "o-2"]) == {"o-1": [LOC, "loc-2"], "o-2": [LOC]}
    locs = r.get_locations([LOC, "loc-2"])
    assert locs["loc-2"].is_billing_lapsed and not locs[LOC].is_billing_lapsed


def test_owners_and_schedules():
    r = repo(FakeSupabase(tables_from_example()))
    owners = r.get_owners(["o-1", "o-2", "u-staff"])
    assert set(owners) == {"o-1", "o-2"}
    assert owners["o-2"].is_enabled
    schedules = r.get_schedules(["o-1"])
    assert schedules["o-1"].templateno == 3 and schedules["o-1"].preferred_time.hour == 21


def test_paging_reads_every_row():
    rows = [log(f"P{i:05d}", mode="cash", amount=1, hour=9) for i in range(PAGE_SIZE * 2 + 5)]
    r = repo(FakeSupabase({"log-man": rows}))
    got = r._all(lambda: r.table("log-man").select("id"))
    assert len(got) == PAGE_SIZE * 2 + 5
