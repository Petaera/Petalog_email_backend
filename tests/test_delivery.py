import email
import io
from datetime import date, timedelta
from email import policy

import pytest

from petalog_reports.config import Settings
from petalog_reports.deliveries import DeliveryLog
from petalog_reports.exports import build_attachments
from petalog_reports.mailer import SendError, SesMailer, build_message
from petalog_reports.sample import sample_report
from petalog_reports.timeutil import iso_z, utc_now
from tests.fake_supabase import FakeSupabase

D = date(2026, 11, 18)


# ----------------------------------------------------------------- attachments
def test_xlsx_workbook_has_all_sheets():
    from openpyxl import load_workbook

    report = sample_report(3, 2)
    [att] = build_attachments(report, "xlsx")
    assert att.filename.endswith(".xlsx") and "2-locations" in att.filename
    wb = load_workbook(io.BytesIO(att.content))
    assert wb.sheetnames == ["Summary", "Transactions", "Payments", "Services", "Spending"]
    assert wb["Transactions"].max_row > 10
    assert wb["Summary"]["A2"].value == "Collections"


def test_csv_has_bom_and_rows():
    report = sample_report(1, 1)
    files = build_attachments(report, "csv")
    assert {f.filename.split("_")[-1] for f in files} == {"transactions.csv", "summary.csv"}
    assert files[0].content.startswith("﻿".encode("utf-8"))


def test_no_attachments_on_quiet_day_or_none():
    assert build_attachments(sample_report(1, quiet=True), "xlsx") == []
    assert build_attachments(sample_report(1), "none") == []


# --------------------------------------------------------------------- mailer
def test_mime_structure_and_headers():
    raw = build_message(sender="PetaLog <no-reply@petalog.in>", to=["a@b.c"], subject="₹1,850 collected",
                        html="<p>hi</p>", text="hi", attachments=build_attachments(sample_report(1), "xlsx"),
                        headers={"List-Unsubscribe": "<https://x/u>"})
    msg = email.message_from_bytes(raw, policy=policy.default)
    assert msg.get_content_type() == "multipart/mixed"
    assert msg["Subject"] == "₹1,850 collected"
    assert msg["List-Unsubscribe"] == "<https://x/u>"
    parts = [p.get_content_type() for p in msg.walk()]
    assert parts[:4] == ["multipart/mixed", "multipart/alternative", "text/plain", "text/html"]
    assert any(p.get_filename() and p.get_filename().endswith(".xlsx") for p in msg.walk())


class FakeSes:
    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = []

    def send_raw_email(self, **kw):
        self.calls.append(kw)
        if self.failures:
            code = self.failures.pop(0)
            err = Exception(code)
            err.response = {"Error": {"Code": code, "Message": f"{code} happened"}}
            raise err
        return {"MessageId": "msg-1"}


def test_ses_retries_throttling_then_succeeds():
    ses = FakeSes(["Throttling"])
    mailer = SesMailer(Settings(ses_from="PetaLog <no-reply@petalog.in>", ses_configuration_set="reports"),
                       client=ses, sleep=lambda s: None)
    assert mailer.send(to=["a@b.c"], subject="s", html="h", text="t") == "msg-1"
    assert len(ses.calls) == 2 and ses.calls[0]["ConfigurationSetName"] == "reports"


def test_ses_permanent_error_not_retried():
    ses = FakeSes(["MessageRejected"])
    mailer = SesMailer(Settings(ses_from="x@y.z"), client=ses, sleep=lambda s: None)
    with pytest.raises(SendError) as err:
        mailer.send(to=["a@b.c"], subject="s", html="h", text="t")
    assert "MessageRejected" in str(err.value) and len(ses.calls) == 1


# ------------------------------------------------------------------ deliveries
def log_with(rows=None, **settings):
    fake = FakeSupabase({"report_deliveries": rows or []})
    return DeliveryLog(Settings(**settings), fake), fake


def test_claim_once_per_owner_and_day():
    log, fake = log_with()
    first = log.claim("o1", D, "dispatch")
    assert first is not None and first.tracked
    assert log.claim("o1", D, "legacy") is None  # being sent
    log.mark_sent(first, message_id="m", recipient="a@b.c", template_no=1, location_ids=["l"])
    assert log.claim("o1", D, "legacy") is None  # already sent
    assert log.claim("o1", D + timedelta(days=1), "dispatch") is not None
    assert fake.tables["report_deliveries"][0]["status"] == "sent"


def test_failed_send_can_retry_until_limit():
    log, fake = log_with(max_attempts=2)
    c = log.claim("o1", D, "dispatch")
    log.mark_failed(c, "SES down")
    again = log.claim("o1", D, "dispatch")
    assert again is not None and again.attempt == 2
    log.mark_failed(again, "SES down")
    assert log.claim("o1", D, "dispatch") is None  # attempts used up
    assert log.claim("o1", D, "manual", force=True) is not None


def test_stale_sending_is_reclaimed():
    old = iso_z(utc_now() - timedelta(hours=2))
    log, _ = log_with([{"id": "r1", "owner_id": "o1", "report_date": D.isoformat(), "kind": "daily",
                        "status": "sending", "attempts": 1, "claimed_at": old}])
    claim = log.claim("o1", D, "dispatch")
    assert claim is not None and claim.id == "r1" and claim.attempt == 2


def test_without_table_sends_untracked():
    fake = FakeSupabase(broken={"report_deliveries"})
    log = DeliveryLog(Settings(), fake)
    assert not log.available()
    claim = log.claim("o1", D, "legacy")
    assert claim is not None and not claim.tracked
    log.mark_sent(claim, message_id="m", recipient="r", template_no=1, location_ids=[])  # no error


def test_tracking_can_be_switched_off():
    log, _ = log_with(delivery_tracking=False)
    assert not log.available()
