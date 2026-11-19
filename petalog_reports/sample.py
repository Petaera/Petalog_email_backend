"""Made-up but realistic data for previews (/dev/preview, scripts/render_previews.py).

Nothing here touches Supabase or real customers.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import List, Optional

from .builder import build_owner_report
from .metrics import build_location_report
from .models import Location, LocationDataset, Owner, OwnerReport
from .timeutil import IST, iso_z, utc_now

SERVICES = [("Foam Wash", 450, 250), ("Interior Cleaning", 600, 0), ("Premium Wash", 900, 400),
            ("Bike Wash", 0, 150), ("Ceramic Coating", 4500, 0), ("Engine Wash", 350, 200)]


def _at(day: date, hour: int, minute: int) -> str:
    return iso_z(datetime(day.year, day.month, day.day, hour, minute, tzinfo=IST))


def sample_dataset(location: Location, day: date, seed: int = 7, scale: float = 1.0) -> LocationDataset:
    rng = random.Random(seed)
    first = day - timedelta(days=7)
    vehicles = {}
    for i in range(80):
        bike = rng.random() < 0.3
        vehicles[f"v{i}"] = {"id": f"v{i}", "number_plate": f"KL{rng.randint(1, 60):02d}{chr(65 + i % 26)}{chr(66 + i % 20)}{rng.randint(1000, 9999)}",
                             "type": "2" if bike else rng.choice(["car", "suv", "sedan", "hatch back"]), "veh_det": None}
    logs, payments, retail, ledger, dues, expenses = [], [], [], [], [], []
    staff = {"s1": "Ravi Kumar", "s2": "Anjali Nair", "s3": "Vishnu P"}
    for offset in range(8):
        d = first + timedelta(days=offset)
        n = int((14 + rng.randint(-4, 8) + (6 if d.weekday() >= 5 else 0)) * scale)
        if d == day:
            n = int(26 * scale)
        for j in range(n):
            vid = f"v{rng.randrange(80)}"
            bike = vehicles[vid]["type"] == "2"
            name, car_price, bike_price = rng.choice([s for s in SERVICES if (s[2] if bike else s[1])])
            if not bike and rng.random() < 0.2:
                extra = rng.choice([s for s in SERVICES if s[1] and s[0] != name])
                name, car_price = f"{name}, {extra[0]}", car_price + extra[1]
            amount = bike_price if bike else car_price
            hour = rng.choice([8, 9, 9, 10, 10, 10, 11, 11, 12, 13, 14, 15, 16, 16, 17, 17, 18, 19])
            mode = rng.choices(["cash", "upi", "card", "credit", "split"], [38, 44, 5, 8, 5])[0]
            status = "approved" if (d != day or rng.random() > 0.12) else "pending"
            log_id = f"{d.isoformat()}-{j}"
            logs.append({
                "id": log_id, "loc_id": location.id, "veh_id": vid, "cust_id": f"c{rng.randrange(60)}",
                "approval_status": status, "payment_mode": mode if status == "approved" else rng.choice(["cash", "upi"]),
                "payment_id": rng.choice(["acc1", "acc1", "acc2"]) if mode == "upi" else None,
                "amount": amount, "discount": rng.choice([0, 0, 0, 50, 100]) if amount > 400 else 0, "total": None,
                "items_total": rng.choice([0, 0, 0, 120]), "extra_work_amount": 0,
                "created_at": _at(d, hour, rng.randrange(60)), "entry_time": _at(d, hour, rng.randrange(60)),
                "exit_time": None, "payment_date": None, "service": name, "created_by": rng.choice(list(staff)),
                "entry_type": "manual",
            })
            if mode == "split" and status == "approved":
                half = amount // 2
                payments += [
                    {"id": f"{log_id}-a", "log_id": log_id, "location_id": location.id, "mode": "cash", "amount": half, "source": "checkout"},
                    {"id": f"{log_id}-b", "log_id": log_id, "location_id": location.id, "mode": "upi", "amount": amount - half,
                     "payment_id": "acc2", "source": "checkout"},
                ]
        expenses.append({"branch_id": location.id, "date": d.isoformat(), "amount": rng.choice([300, 450, 800, 1200]),
                         "payment_mode": "Cash", "category_name": rng.choice(["Shampoo & chemicals", "Electricity", "Water"])})
        retail.append({"location_id": location.id, "total": rng.choice([150, 240, 380]), "payment_mode": "upi",
                       "log_id": None, "created_at": _at(d, 15, 10)})
    ledger.append({"location_id": location.id, "kind": "advance_deposit", "amount": 2000, "created_at": _at(day, 11, 5)})
    dues.append({"location_id": location.id, "kind": "payment", "amount": -1500, "payment_mode": "cash", "created_at": _at(day, 12, 0)})
    expenses.append({"branch_id": location.id, "date": day.isoformat(), "amount": 650, "payment_mode": "UPI",
                     "category_name": "Shampoo & chemicals"})
    return LocationDataset(
        location=location, first_day=first, last_day=day, logs=logs, payments=payments, vehicles=vehicles,
        local_customers={f"c{i}": {"customer_id": f"c{i}", "first_seen_at": _at(day if i % 9 == 0 else day - timedelta(days=40), 9, 0)}
                         for i in range(60)},
        upi_accounts={"acc1": {"id": "acc1", "account_name": "Main counter GPay"},
                      "acc2": {"id": "acc2", "account_name": "", "upi_id": "luxelane@okhdfc"}},
        service_prices=[{"SERVICE": s, "VEHICLE": v, "PRICE": p} for s, c, b in SERVICES
                        for v, p in (("car", c), ("suv", c), ("sedan", c), ("hatch back", c), ("bike", b)) if p],
        staff_names=staff, retail_sales=retail, customer_ledger=ledger, due_ledger=dues, expenses=expenses,
        staff_expenses=[{"date": day.isoformat(), "amount": 300, "category": "incentive"}],
        salary_payments=[{"payment_date": day.isoformat(), "amount": 1200}],
        cash_balance=18450.0,
    )


def sample_report(template_no: int = 3, locations: int = 1, day: Optional[date] = None,
                  quiet: bool = False) -> OwnerReport:
    day = day or (utc_now().astimezone(IST).date() - timedelta(days=1))
    owner = Owner(id="sample-owner", email="owner@example.com", first_name="Anu", last_name="Thomas")
    names = ["Luxe Lane Car Spa", "Luxe Lane Doorstep", "Luxe Lane Kakkanad"]
    reports = []
    for i in range(locations):
        loc = Location(id=f"sample-{i}", name=names[i % len(names)], city="Kochi")
        data = sample_dataset(loc, day, seed=7 + i, scale=1.0 - i * 0.3)
        if quiet:
            data.logs = [l for l in data.logs if not l["created_at"].startswith(day.isoformat())]
            data.logs = [l for l in data.logs if l["created_at"] < iso_z(datetime(day.year, day.month, day.day, tzinfo=IST))]
            data.retail_sales, data.customer_ledger, data.due_ledger = [], [], []
            data.expenses = [e for e in data.expenses if e["date"] != day.isoformat()]
            data.staff_expenses, data.salary_payments = [], []
        reports.append(build_location_report(data, day))
    return build_owner_report(owner, day, template_no, reports, generated_at=utc_now())
