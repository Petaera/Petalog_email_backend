from datetime import date, datetime, time, timezone

from petalog_reports import formatting as fmt
from petalog_reports.config import Settings, email_address_of
from petalog_reports.timeutil import day_bounds, iso_z, parse_clock, parse_ts, safe_zone


def test_indian_money_grouping():
    assert fmt.money(0) == "₹0"
    assert fmt.money(999) == "₹999"
    assert fmt.money(1000) == "₹1,000"
    assert fmt.money(123456) == "₹1,23,456"
    assert fmt.money(12345678) == "₹1,23,45,678"
    assert fmt.money(1500.5) == "₹1,500.50"
    assert fmt.money(-2500) == "-₹2,500"
    assert fmt.money(None) == "₹0"
    assert fmt.money("abc") == "₹0"


def test_compact_and_percent():
    assert fmt.compact_money(48200) == "₹48.2K"
    assert fmt.compact_money(120000) == "₹1.2L"
    assert fmt.signed_percent(12.4) == "+12%"
    assert fmt.signed_percent(-3.6) == "−4%"
    assert fmt.signed_percent(None) == "–"
    assert fmt.change_ratio(110, 100) == 10.0
    assert fmt.change_ratio(5, 0) is None


def test_dates():
    assert fmt.long_date(date(2026, 11, 18)) == "Wednesday, 18 November 2026"
    assert fmt.short_date(date(2026, 11, 18)) == "Wed 18 Nov"
    assert fmt.hour_label(0) == "12 AM"
    assert fmt.hour_label(13) == "1 PM"


def test_ist_day_bounds():
    start, end = day_bounds(date(2026, 11, 19))
    assert start == datetime(2026, 11, 18, 18, 30, tzinfo=timezone.utc)
    assert end == datetime(2026, 11, 19, 18, 30, tzinfo=timezone.utc)
    assert iso_z(start) == "2026-11-18T18:30:00.000000Z"


def test_parse_ts_variants():
    assert parse_ts("2026-11-19T10:00:00Z") == datetime(2026, 11, 19, 10, tzinfo=timezone.utc)
    assert parse_ts("2026-11-19T15:30:00.12+05:30") == datetime(2026, 11, 19, 10, 0, 0, 120000, tzinfo=timezone.utc)
    assert parse_ts("2026-11-19 10:00:00.123456789+00:00").microsecond == 123456
    assert parse_ts(None) is None
    assert parse_ts("") is None


def test_parse_clock_and_zone():
    assert parse_clock("21:00:00") == time(21, 0)
    assert parse_clock("9:05") == time(9, 5)
    assert parse_clock("bad") == time(21, 0)
    assert parse_clock(None, time(8, 0)) == time(8, 0)
    assert str(safe_zone("Nope/Zone")) == "Asia/Kolkata"
    assert str(safe_zone("Asia/Dubai")) == "Asia/Dubai"


def test_settings_defaults(monkeypatch):
    for name in ("REPORT_ATTACHMENT_FORMAT", "ALLOW_ANON_KEY_AUTH", "ADMIN_SUMMARY_MODE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SES_VERIFIED_FROM", "PetaLog <no-reply@petalog.in>")
    settings = Settings.from_env()
    assert settings.allow_anon_key_auth is True
    assert settings.attachment_format == "xlsx"
    assert settings.admin_summary_mode == "failures"
    assert settings.admin_recipient == "no-reply@petalog.in"
    assert email_address_of("x@y.z") == "x@y.z"
