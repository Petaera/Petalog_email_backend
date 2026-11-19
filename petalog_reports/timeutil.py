"""Time helpers.

The PetaLog app's business day is the India (IST, UTC+05:30) calendar day
whatever the owner's timezone: every dashboard and report function in the
database uses [date 00:00 IST, next date 00:00 IST). The emails use the same
day. The owner's timezone only decides *when* the email is sent.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

try:  # Python 3.9+
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # type: ignore

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def ist_today(now: Optional[datetime] = None) -> date:
    return to_ist(now or utc_now()).date()


def safe_zone(name: Optional[str]) -> ZoneInfo:
    """The named timezone, or IST when it is missing or unknown."""
    if not name:
        return IST
    try:
        return ZoneInfo(str(name).strip())
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return IST


def day_bounds(day: date) -> Tuple[datetime, datetime]:
    """[start, end) of an IST business day, as aware UTC datetimes."""
    start = datetime.combine(day, time(0, 0), tzinfo=IST)
    end = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=IST)
    return start.astimezone(UTC), end.astimezone(UTC)


def range_bounds(first_day: date, last_day: date) -> Tuple[datetime, datetime]:
    """[start of first_day, end of last_day) in UTC."""
    start, _ = day_bounds(first_day)
    _, end = day_bounds(last_day)
    return start, end


def iso_z(dt: datetime) -> str:
    """UTC ISO string with a 'Z' suffix: safe inside PostgREST filters
    (a '+00:00' offset would be read as a space in a query string)."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_ts(value) -> Optional[datetime]:
    """Parse a Supabase timestamp (or date) into an aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip().replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    # Python < 3.11 needs exactly 6 fractional digits.
    if "." in text:
        head, _, rest = text.partition(".")
        digits = ""
        i = 0
        while i < len(rest) and rest[i].isdigit():
            digits += rest[i]
            i += 1
        text = f"{head}.{(digits + '000000')[:6]}{rest[i:]}"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            # A bare date compares like Postgres casting date -> timestamptz
            # in the database's UTC session: midnight UTC.
            dt = datetime.combine(date.fromisoformat(text[:10]), time(0, 0), tzinfo=UTC)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def parse_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_clock(value, default: time = time(21, 0)) -> time:
    """'21:00', '21:00:00' or '9:5' -> time. Anything else -> default."""
    if value is None:
        return default
    if isinstance(value, time):
        return value
    parts = str(value).strip().split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
    except (ValueError, IndexError):
        pass
    return default


def in_window(dt: Optional[datetime], start: datetime, end: datetime) -> bool:
    return dt is not None and start <= dt < end
