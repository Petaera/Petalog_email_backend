"""Who is due for a report, and which business day it covers.

* An owner is due once their preferred time (in their timezone) has passed
  today, for up to DISPATCH_CATCHUP_MINUTES afterwards. A send missed
  because the service was asleep (Render free tier) or down therefore goes
  out on the next dispatch instead of being lost; report_deliveries makes
  sure it goes out only once.
* Report day: a send before REPORT_MORNING_CUTOFF_HOUR (12:00) covers the
  previous full day; a later send covers the same day.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional

from .config import Settings
from .models import Schedule
from .timeutil import safe_zone, utc_now


@dataclass
class Due:
    owner_id: str
    schedule: Schedule
    occurrence: datetime  # aware, owner's timezone
    report_date: date


def report_date_for(occurrence: datetime, settings: Settings) -> date:
    local = occurrence
    if local.hour < settings.morning_cutoff_hour:
        return local.date() - timedelta(days=1)
    return local.date()


def _occurrence(day: date, schedule: Schedule) -> datetime:
    return datetime.combine(day, schedule.preferred_time, tzinfo=safe_zone(schedule.timezone))


def due_owners(schedules: Iterable[Schedule], settings: Settings, now: Optional[datetime] = None) -> List[Due]:
    now = now or utc_now()
    window = timedelta(minutes=settings.catchup_minutes)
    due: List[Due] = []
    for schedule in schedules:
        if not schedule.is_active:
            continue
        local_now = now.astimezone(safe_zone(schedule.timezone))
        for back in (0, 1):  # yesterday's time may still be in its catch-up window after midnight
            occurrence = _occurrence(local_now.date() - timedelta(days=back), schedule)
            if occurrence <= local_now <= occurrence + window:
                due.append(Due(schedule.user_id, schedule, occurrence, report_date_for(occurrence, settings)))
                break
    return sorted(due, key=lambda d: d.occurrence)


def nearest_report_date(schedule: Schedule, settings: Settings, now: Optional[datetime] = None) -> date:
    """Report day for a send requested 'now' by an outside trigger (the
    previous edge function calls a few minutes around the preferred time)."""
    now = now or utc_now()
    local_now = now.astimezone(safe_zone(schedule.timezone))
    candidates = [_occurrence(local_now.date() + timedelta(days=k), schedule) for k in (-1, 0, 1)]
    nearest = min(candidates, key=lambda occ: abs((occ - local_now).total_seconds()))
    return report_date_for(nearest, settings)


def default_schedule(user_id: str) -> Schedule:
    """What the app shows when an owner never saved report settings."""
    return Schedule(user_id=user_id, has_row=False)


def with_defaults(owner_ids: Iterable[str], schedules: Dict[str, Schedule]) -> Dict[str, Schedule]:
    out = dict(schedules)
    for owner_id in owner_ids:
        out.setdefault(owner_id, default_schedule(owner_id))
    return out
