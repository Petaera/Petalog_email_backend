"""Small hand-made datasets with known answers."""

from datetime import date, datetime, timedelta

from petalog_reports.models import Location, LocationDataset
from petalog_reports.timeutil import IST, iso_z

DAY = date(2026, 11, 18)
LOC = "loc-1"


def at(day: date, hour: int, minute: int = 0) -> str:
    """IST wall-clock time -> UTC ISO string, as Supabase returns it."""
    return iso_z(datetime(day.year, day.month, day.day, hour, minute, tzinfo=IST))


def log(id, *, mode, amount, hour=10, day=DAY, status="approved", discount=None, total=None,
        veh="v-car", payment_id=None, service="Foam Wash", cust="c-1", entry_hour=None, **extra):
    row = {
        "id": id, "loc_id": LOC, "veh_id": veh, "cust_id": cust,
        "approval_status": status, "payment_mode": mode, "payment_id": payment_id,
        "amount": amount, "discount": discount, "total": total,
        "created_at": at(day, hour), "entry_time": at(day, entry_hour if entry_hour is not None else hour),
        "exit_time": None, "payment_date": None, "service": service,
        "created_by": "u-staff", "entry_type": "manual",
    }
    row.update(extra)
    return row


def part(log_id, mode, amount, *, paid_at=None, payment_id=None, source="checkout"):
    return {"log_id": log_id, "location_id": LOC, "mode": mode, "amount": amount,
            "paid_at": paid_at, "payment_id": payment_id, "source": source}


def worked_example() -> LocationDataset:
    yesterday = DAY - timedelta(days=1)
    logs = [
        log("L1", mode="cash", amount=500, hour=10),
        log("L2", mode="upi", amount=300, discount=50, hour=10, veh="v-bike", payment_id="acc-1",
            service="Bike Wash", cust="c-2"),
        log("L3", mode="credit", amount=400, hour=11, cust="c-3"),
        log("L4", mode="split", amount=450, hour=12, veh="v-suv", service="Foam Wash, Interior", cust="c-4"),
        log("L5", mode=None, amount=600, hour=13, status=None),
        log("L6", mode="split", amount=350, hour=15, day=yesterday, cust="c-5"),
        log("L7", mode="advance", amount=200, hour=16, veh=None, cust="c-6"),
        log("L8", mode=None, amount=999, hour=17),
    ]
    payments = [
        part("L4", "cash", 200),
        part("L4", "upi", 100, payment_id="acc-1"),
        part("L4", "credit", 150),
        part("L6", "credit", 350),
        part("L6", "cash", 350, paid_at=at(DAY, 18), source="settlement"),
    ]
    return LocationDataset(
        location=Location(id=LOC, name="Luxe Lane"),
        first_day=DAY - timedelta(days=7),
        last_day=DAY,
        logs=logs,
        payments=payments,
        vehicles={
            "v-car": {"id": "v-car", "number_plate": "KL07AB1234", "type": "car", "veh_det": "m-1"},
            "v-bike": {"id": "v-bike", "number_plate": "KL07CD5678", "type": "2", "veh_det": None},
            "v-suv": {"id": "v-suv", "number_plate": "KL01EF0001", "type": "SUV", "veh_det": None},
        },
        catalogue={"m-1": {"id": "m-1", "type": "4 Wheeler", "Vehicle Brands": "Maruti", "Models": "Swift"}},
        customers={"c-1": {"id": "c-1", "name": "Global Name", "phone": "9999999999"}},
        local_customers={
            "c-1": {"customer_id": "c-1", "name": "Local Name", "first_seen_at": at(DAY, 9)},
            "c-2": {"customer_id": "c-2", "first_seen_at": at(DAY - timedelta(days=30), 9)},
        },
        upi_accounts={"acc-1": {"id": "acc-1", "account_name": "Shop GPay", "upi_id": "shop@okaxis"}},
        service_prices=[
            {"SERVICE": "Foam Wash", "VEHICLE": "suv", "PRICE": 600, "locationid": LOC},
            {"SERVICE": "Interior", "VEHICLE": "suv", "PRICE": 200, "locationid": LOC},
        ],
        staff_names={"u-staff": "Ravi"},
        retail_sales=[
            {"location_id": LOC, "total": 100, "payment_mode": "cash", "log_id": None, "created_at": at(DAY, 14)},
            {"location_id": LOC, "total": 80, "payment_mode": "cash", "log_id": "L1", "created_at": at(DAY, 10)},
        ],
        customer_ledger=[
            {"location_id": LOC, "kind": "advance_deposit", "amount": 1000, "created_at": at(DAY, 9)},
        ],
        due_ledger=[
            {"location_id": LOC, "kind": "payment", "amount": -120, "payment_mode": "upi", "created_at": at(DAY, 11)},
            {"location_id": LOC, "kind": "paid_from_advance", "amount": -30, "created_at": at(DAY, 11)},
        ],
        expenses=[
            {"branch_id": LOC, "date": DAY.isoformat(), "amount": 250, "payment_mode": "Cash", "category_name": "Soap"},
            {"branch_id": LOC, "date": DAY.isoformat(), "amount": 100, "payment_mode": "UPI", "category_name": "Power"},
            {"branch_id": LOC, "date": yesterday.isoformat(), "amount": 999, "payment_mode": "Cash"},
        ],
        staff_expenses=[{"branch_id": LOC, "date": DAY.isoformat(), "amount": 50, "category": "food"}],
        salary_payments=[{"branch_id": LOC, "payment_date": DAY.isoformat(), "amount": 700}],
        staff_payments=[{"location_id": LOC, "payment_date": DAY.isoformat(), "amount": 300, "type": "Advance"},
                        {"location_id": LOC, "payment_date": DAY.isoformat(), "amount": 999, "type": "Other"}],
        cash_balance=4321.5,
    )
