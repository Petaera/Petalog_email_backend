from datetime import datetime, timezone

import pytest

from petalog_reports.builder import build_owner_report, location_insights, subject_for
from petalog_reports.metrics import build_location_report
from petalog_reports.models import Owner
from petalog_reports.render import render_email
from petalog_reports.sample import sample_report
from tests.factories import DAY, worked_example

KW = dict(app_url="https://petalog.in", logo_url="https://petalog.in/logo.png")


@pytest.mark.parametrize("template", [1, 2, 3])
@pytest.mark.parametrize("locations", [1, 3])
def test_every_template_renders(template, locations):
    email = render_email(sample_report(template, locations), **KW)
    assert email.html.startswith("<!DOCTYPE html>")
    assert "https://petalog.in/dashboard" in email.html
    assert "display:grid" not in email.html and "linear-gradient" not in email.html
    assert email.text.strip()
    assert "₹" in email.subject


def test_template_features_differ():
    t1 = render_email(sample_report(1), **KW).html
    t3 = render_email(sample_report(3), **KW).html
    assert "Highlights" not in t1 and "Highlights" in t3
    assert "Compared with" in t3 and "Last 7 days" in t3
    assert "Through the day" not in t1


def test_quiet_day():
    email = render_email(sample_report(1, quiet=True), **KW)
    assert "No entries recorded" in email.html
    assert "No entries recorded" in email.subject


def test_user_text_is_escaped():
    data = worked_example()
    data.location.name = '<script>alert("x")</script> & Co'
    data.logs[0]["service"] = "<b>Wash</b>"
    report = build_owner_report(Owner(id="o", email="o@x.y"), DAY, 3,
                                [build_location_report(data, DAY)], datetime(2026, 11, 18, 16, tzinfo=timezone.utc))
    html = render_email(report, **KW).html
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<b>Wash</b>" not in html


def test_worked_example_numbers_in_email():
    report = build_owner_report(Owner(id="o", email="o@x.y", first_name="Anu"), DAY, 1,
                                [build_location_report(worked_example(), DAY)],
                                datetime(2026, 11, 18, 16, tzinfo=timezone.utc))
    email = render_email(report, **KW, unsubscribe_url="https://svc/v1/unsubscribe?t=1")
    assert "₹1,850" in email.html and "₹1,850" in email.text
    assert "1 ticket (₹600) waiting for approval" in email.html
    assert "Cash in hand (now)" in email.html and "₹4,321.50" in email.html
    assert "Stop these emails" in email.html and "https://svc/v1/unsubscribe?t=1" in email.text
    assert subject_for(report) == "Luxe Lane daily report · Wed 18 Nov · ₹1,850 collected, 4 vehicles"


def test_missing_sources_are_named_in_footer():
    data = worked_example()
    data.warnings = ["old dues"]
    report = build_owner_report(Owner(id="o", email="o@x.y"), DAY, 2, [build_location_report(data, DAY)],
                                datetime(2026, 11, 18, 16, tzinfo=timezone.utc))
    assert "could not be loaded): old dues" in render_email(report, **KW).html


def test_insights_mention_pending_and_pay_later():
    text = " ".join(location_insights(build_location_report(worked_example(), DAY)))
    assert "waiting for approval" in text and "Pay Later" in text
