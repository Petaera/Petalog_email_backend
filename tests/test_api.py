import email
from datetime import date, datetime, time, timedelta, timezone

import pytest

import petalog_reports.scheduler as scheduler_mod
from petalog_reports.api import create_app
from petalog_reports.auth import unsubscribe_url
from petalog_reports.config import Settings
from petalog_reports.deliveries import DeliveryLog
from petalog_reports.mailer import SesMailer
from petalog_reports.models import Schedule
from petalog_reports.repository import SupabaseRepository
from petalog_reports.scheduler import due_owners, nearest_report_date, report_date_for
from petalog_reports.service import ReportService
from petalog_reports.timeutil import IST
from tests.factories import DAY
from tests.fake_supabase import FakeSupabase
from tests.test_delivery import FakeSes
from tests.test_repository import tables_from_example

SERVICE, ANON, SECRET = "service-key", "anon-key", "api-secret"
# 21:05 IST on the report day: owner o-1's 21:00 report is due and covers DAY.
NOW = datetime(DAY.year, DAY.month, DAY.day, 21, 5, tzinfo=IST).astimezone(timezone.utc)


def make(tables=None, broken=(), **overrides):
    settings = Settings(supabase_url="https://x", supabase_service_role_key=SERVICE, supabase_anon_key=ANON,
                        reports_api_secret=SECRET, ses_from="PetaLog <no-reply@petalog.in>",
                        public_url="https://reports.example", unsubscribe_secret="u-secret", **overrides)
    tables = tables if tables is not None else tables_from_example()
    tables.setdefault("report_deliveries", [])
    fake = FakeSupabase(tables, broken=broken)
    ses = FakeSes([])
    service = ReportService(settings, SupabaseRepository(settings, client=fake),
                            SesMailer(settings, client=ses, sleep=lambda s: None), DeliveryLog(settings, fake))
    app = create_app(settings, service)
    app.testing = True
    return app.test_client(), fake, ses, service


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(scheduler_mod, "utc_now", lambda: NOW)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def sent_messages(ses):
    return [email.message_from_bytes(c["RawMessage"]["Data"]) for c in ses.calls]


# --------------------------------------------------------------- scheduler
def test_report_day_rule():
    s = Settings()
    assert report_date_for(datetime(2026, 11, 20, 1, 0, tzinfo=IST), s) == date(2026, 11, 19)
    assert report_date_for(datetime(2026, 11, 20, 10, 30, tzinfo=IST), s) == date(2026, 11, 19)
    assert report_date_for(datetime(2026, 11, 20, 12, 0, tzinfo=IST), s) == date(2026, 11, 20)
    assert report_date_for(datetime(2026, 11, 20, 21, 0, tzinfo=IST), s) == date(2026, 11, 20)


def test_due_window_and_catch_up():
    s = Settings(catchup_minutes=180)
    sched = [Schedule("a", preferred_time=time(21, 0)), Schedule("b", preferred_time=time(22, 0)),
             Schedule("c", preferred_time=time(23, 30)), Schedule("d", preferred_time=time(21, 0), is_active=False)]
    at = lambda h, m, d=DAY: datetime(d.year, d.month, d.day, h, m, tzinfo=IST)  # noqa: E731
    assert [x.owner_id for x in due_owners(sched, s, at(20, 59))] == []
    assert [x.owner_id for x in due_owners(sched, s, at(21, 0))] == ["a"]
    assert [x.owner_id for x in due_owners(sched, s, at(23, 45))] == ["a", "b", "c"]
    # After midnight: c (23:30 yesterday) is still within its window and reports yesterday.
    late = due_owners(sched, s, at(0, 20, DAY + timedelta(days=1)))
    assert [(x.owner_id, x.report_date) for x in late] == [("b", DAY), ("c", DAY)]
    assert due_owners(sched, s, at(2, 31, DAY + timedelta(days=1))) == []


def test_nearest_report_date_around_send_time():
    s = Settings()
    sched = Schedule("a", preferred_time=time(21, 0))
    assert nearest_report_date(sched, s, datetime(2026, 11, 18, 20, 55, tzinfo=IST)) == date(2026, 11, 18)
    morning = Schedule("b", preferred_time=time(1, 0))
    assert nearest_report_date(morning, s, datetime(2026, 11, 19, 0, 55, tzinfo=IST)) == date(2026, 11, 18)


# ------------------------------------------------------------ legacy route
def test_legacy_contract_with_anon_key_sends_once():
    client, fake, ses, _ = make()
    body = {"users": [{"user_id": "o-1"}], "trigger": "cron"}
    resp = client.post("/send-reports", json=body, headers=auth(ANON))
    data = resp.get_json()
    assert resp.status_code == 200 and data["success"] is True
    for key in ("emailsSent", "emailsFailed", "emailsSkipped", "totalOwners", "totalRevenue", "results", "reportDate"):
        assert key in data
    assert data["emailsSent"] == 1 and data["reportDate"] == DAY.isoformat()
    msg = sent_messages(ses)[0]
    assert msg["To"] == "owner@example.com"
    assert "Luxe Lane" in str(email.header.make_header(email.header.decode_header(msg["Subject"])))
    assert msg["List-Unsubscribe"].startswith("<https://reports.example/v1/unsubscribe?u=o-1")
    # o-1 owns loc-1 (own_id) and loc-2 (co-owner) but loc-2 is read_only: one location only.
    assert data["results"][0]["locations"] == 1
    assert any("read_only" in n for n in data["results"][0]["skippedLocations"])
    # Second trigger for the same day: no duplicate.
    again = client.post("/send-reports", json=body, headers=auth(ANON)).get_json()
    assert again["emailsSent"] == 0 and again["results"][0]["reason"] == "Already sent"
    assert len(ses.calls) == 1
    assert fake.tables["report_deliveries"][0]["status"] == "sent"


def test_auth_rules():
    client, _, ses, _ = make()
    assert client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}).status_code == 401
    assert client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}, headers=auth("nope")).status_code == 401
    for body in ({"email_override": "x@evil.test", "users": [{"user_id": "o-1"}]},
                 {"email_override": "x@evil.test", "location_ids": ["loc-1"]},
                 {"users": [{"user_id": "o-1"}], "location_ids": ["loc-1"]},
                 {"users": [{"user_id": "o-1"}], "templateno": 3},
                 {"trigger": "everyone"}):
        assert client.post("/send-reports", json=body, headers=auth(ANON)).status_code == 403
    assert ses.calls == []


def test_anon_key_can_be_switched_off():
    client, _, _, _ = make(allow_anon_key_auth=False)
    assert client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}, headers=auth(ANON)).status_code == 401


def test_trusted_test_send_to_override_is_not_tracked():
    client, fake, ses, _ = make()
    body = {"users": [{"user_id": "o-1"}], "email_override": "qa@example.com", "templateno": 2}
    data = client.post("/send-reports", json=body, headers=auth(SERVICE)).get_json()
    assert data["emailsSent"] == 1 and data["results"][0]["templateUsed"] == 2
    assert sent_messages(ses)[0]["To"] == "qa@example.com"
    assert fake.tables["report_deliveries"] == []
    # The real send for the day still happens afterwards.
    assert client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}, headers=auth(ANON)).get_json()["emailsSent"] == 1


def test_override_never_means_all_locations():
    client, _, ses, _ = make()
    resp = client.post("/send-reports", json={"email_override": "qa@example.com"}, headers=auth(SERVICE))
    assert resp.status_code == 400 and ses.calls == []


def test_override_with_locations():
    client, _, ses, _ = make()
    body = {"email_override": "qa@example.com", "location_ids": ["loc-1"], "date": DAY.isoformat()}
    data = client.post("/send-reports", json=body, headers=auth(SECRET)).get_json()
    assert data["emailsSent"] == 1 and data["results"][0]["revenue"] == 1850


def test_disabled_owner_and_turned_off_schedule_are_skipped():
    tables = tables_from_example()
    tables["users"][1]["status"] = False
    client, _, ses, _ = make(tables)
    data = client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}, headers=auth(ANON)).get_json()
    assert data["results"][0]["reason"] == "Inactive user status"
    tables = tables_from_example()
    tables["user_schedules"][0]["is_active"] = False
    client, _, ses, _ = make(tables)
    data = client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}, headers=auth(ANON)).get_json()
    assert data["results"][0]["reason"] == "Daily reports turned off" and ses.calls == []


def test_admin_summary_only_on_failure():
    client, _, ses, service = make(admin_summary_mode="failures")
    client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}, headers=auth(ANON))
    assert len(ses.calls) == 1  # report only, no admin email
    client, _, ses, _ = make(admin_summary_mode="always")
    data = client.post("/send-reports", json={"users": [{"user_id": "o-1"}]}, headers=auth(ANON)).get_json()
    assert len(ses.calls) == 2 and data["summaryEmailSent"] is True


# ---------------------------------------------------------------- dispatch
def test_dispatch_sends_due_reports_once():
    client, fake, ses, service = make()
    assert client.post("/v1/dispatch?wait=1", headers=auth(ANON)).status_code == 403
    data = service.dispatch(NOW)
    assert data["sent"] == 1 and data["reportDates"] == [DAY.isoformat()]
    again = service.dispatch(NOW + timedelta(minutes=5))
    assert again["sent"] == 0 and again["results"] == []
    assert len(ses.calls) == 1


def test_dispatch_route_sync_mode():
    client, _, ses, _ = make()
    resp = client.post("/v1/dispatch?wait=1", headers=auth(SECRET))
    assert resp.status_code == 200 and resp.get_json()["sent"] == 1


def test_dispatch_requires_delivery_table():
    client, _, _, _ = make(broken={"report_deliveries"})
    resp = client.post("/v1/dispatch", headers=auth(SECRET))
    assert resp.status_code == 503


def test_dispatch_skips_owner_whose_locations_all_lapsed():
    tables = tables_from_example()
    tables["view_locations_billing"][0]["status"] = "archived"
    tables["location_owners"] = []
    client, fake, ses, service = make(tables)
    data = service.dispatch(NOW)
    assert data["sent"] == 0 and data["skipped"] == 1 and ses.calls == []
    assert fake.tables["report_deliveries"][0]["status"] == "skipped"


def test_failed_send_is_recorded_and_retried():
    client, fake, ses, service = make()
    ses.failures = ["MessageRejected"]
    first = service.dispatch(NOW)
    assert first["failed"] == 1 and fake.tables["report_deliveries"][0]["status"] == "failed"
    second = service.dispatch(NOW + timedelta(minutes=5))
    assert second["sent"] == 1


# ------------------------------------------------------------- one-offs etc
def test_send_one_and_preview():
    client, _, ses, _ = make()
    resp = client.post("/v1/reports/send", json={"user_id": "o-1", "date": DAY.isoformat(),
                                                 "email_override": "qa@example.com", "templateno": 1},
                       headers=auth(SECRET))
    assert resp.get_json()["success"] is True
    page = client.get(f"/v1/reports/preview?user_id=o-1&date={DAY.isoformat()}&template=3", headers=auth(SECRET))
    assert page.status_code == 200 and b"Business Intelligence" in page.data
    assert client.get("/v1/reports/preview?user_id=o-1", headers=auth(ANON)).status_code == 403


def test_unsubscribe_flow():
    client, fake, _, service = make()
    url = unsubscribe_url(service.settings, "o-1").replace("https://reports.example", "")
    assert client.get(url).status_code == 200  # confirmation page, nothing changed yet
    assert fake.tables["user_schedules"][0]["is_active"] is True
    assert client.post(url).status_code == 200
    assert fake.tables["user_schedules"][0]["is_active"] is False
    assert client.post("/v1/unsubscribe?u=o-1&t=forged").status_code == 400


def test_health_and_dev_routes_locked():
    client, _, _, _ = make()
    assert client.get("/health").get_json()["status"] == "healthy"
    assert client.get("/dev").status_code == 404
    client, _, _, _ = make(enable_dev_route=True)
    assert client.get("/dev/preview?template=2").status_code == 200
    assert client.get("/dev", environ_base={"REMOTE_ADDR": "10.0.0.5"}).status_code == 403
