"""Send history and duplicate protection (public.report_deliveries).

One row per (owner, report day, kind). A send first *claims* the row; a
second claim for the same owner and day is refused, so an owner never gets
the same daily report twice even when the old and the new trigger both run,
a cron fires twice, or a request is retried.

Failed sends can be claimed again (up to DELIVERY_MAX_ATTEMPTS), and a row
stuck in 'sending' (the process died mid-send) is reclaimed after
DELIVERY_STALE_MINUTES.

Requires sql/001_report_deliveries.sql. Without the table the service still
sends (legacy behaviour) but cannot prevent duplicates; /v1/dispatch refuses
to run without it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from .config import Settings
from .timeutil import iso_z, parse_ts, utc_now

logger = logging.getLogger(__name__)

TABLE = "report_deliveries"


@dataclass
class Claim:
    id: Optional[str]
    owner_id: str
    report_date: date
    attempt: int = 1
    tracked: bool = True


class DeliveryLog:
    def __init__(self, settings: Settings, client):
        self.settings = settings
        self.client = client
        self._available: Optional[bool] = None

    def available(self) -> bool:
        if not self.settings.delivery_tracking:
            return False
        if not self._available:  # remember success only: a table created later is picked up
            try:
                self.client.table(TABLE).select("id").limit(1).execute()
                self._available = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("report_deliveries is not available (%s): duplicates cannot be prevented", exc)
                self._available = False
        return bool(self._available)

    def _get(self, owner_id: str, report_date: date, kind: str):
        rows = (self.client.table(TABLE).select("id,status,attempts,claimed_at")
                .eq("owner_id", owner_id).eq("report_date", report_date.isoformat()).eq("kind", kind)
                .execute().data or [])
        return rows[0] if rows else None

    def _reclaim(self, row, trigger: str) -> Optional[int]:
        attempts = int(row.get("attempts") or 1)
        resp = (self.client.table(TABLE)
                .update({"status": "sending", "attempts": attempts + 1, "trigger": trigger,
                         "claimed_at": iso_z(utc_now()), "updated_at": iso_z(utc_now()), "error": None})
                .eq("id", row["id"]).eq("status", row["status"]).eq("attempts", attempts)
                .execute())
        return attempts + 1 if resp.data else None

    def claim(self, owner_id: str, report_date: date, trigger: str, kind: str = "daily",
              force: bool = False) -> Optional[Claim]:
        """A Claim to go ahead, or None when this report is sent / being sent."""
        if not self.available():
            return Claim(id=None, owner_id=owner_id, report_date=report_date, tracked=False)
        now = iso_z(utc_now())
        inserted = (self.client.table(TABLE)
                    .upsert({"owner_id": owner_id, "report_date": report_date.isoformat(), "kind": kind,
                             "status": "sending", "attempts": 1, "trigger": trigger,
                             "claimed_at": now, "updated_at": now},
                            on_conflict="owner_id,report_date,kind", ignore_duplicates=True)
                    .execute().data or [])
        if inserted:
            return Claim(id=str(inserted[0]["id"]), owner_id=owner_id, report_date=report_date)
        row = self._get(owner_id, report_date, kind)
        if row is None:  # deleted in between: try once more
            return self.claim(owner_id, report_date, trigger, kind, force) if not force else None
        status = row.get("status")
        retry = False
        if force:
            retry = status != "sending" or self._stale(row)
        elif status == "failed":
            retry = int(row.get("attempts") or 1) < self.settings.max_attempts
        elif status == "sending":
            retry = self._stale(row)
        if not retry:
            return None
        attempt = self._reclaim(row, trigger)
        if attempt is None:
            return None  # someone else reclaimed it first
        return Claim(id=str(row["id"]), owner_id=owner_id, report_date=report_date, attempt=attempt)

    def _stale(self, row) -> bool:
        claimed = parse_ts(row.get("claimed_at"))
        return claimed is None or claimed < utc_now() - timedelta(minutes=self.settings.stale_sending_minutes)

    def _finish(self, claim: Claim, values: dict) -> None:
        if not claim.tracked or not claim.id:
            return
        values["updated_at"] = iso_z(utc_now())
        try:
            self.client.table(TABLE).update(values).eq("id", claim.id).execute()
        except Exception as exc:  # noqa: BLE001 - the email outcome must not depend on bookkeeping
            logger.error("Could not record delivery %s: %s", claim.id, exc)

    def mark_sent(self, claim: Claim, *, message_id: str, recipient: str, template_no: int,
                  location_ids: List[str]) -> None:
        self._finish(claim, {"status": "sent", "ses_message_id": message_id, "recipient": recipient,
                             "template_no": template_no, "location_ids": location_ids,
                             "sent_at": iso_z(utc_now()), "error": None})

    def mark_failed(self, claim: Claim, error: str) -> None:
        self._finish(claim, {"status": "failed", "error": error[:1000]})

    def mark_skipped(self, claim: Claim, reason: str) -> None:
        self._finish(claim, {"status": "skipped", "error": reason[:1000]})

    def release(self, claim: Claim) -> None:
        """Undo a claim that did not lead to a send attempt (e.g. a test send)."""
        if claim.tracked and claim.id and claim.attempt == 1:
            try:
                self.client.table(TABLE).delete().eq("id", claim.id).eq("status", "sending").execute()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not release claim %s: %s", claim.id, exc)
