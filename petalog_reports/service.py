"""Orchestration: load data, build, render, send, record."""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .auth import Caller, unsubscribe_url
from .builder import build_owner_report
from .config import Settings
from .deliveries import DeliveryLog
from .exports import attachment_note, build_attachments
from .mailer import SesMailer
from .metrics import build_location_report
from .models import Location, Owner, OwnerReport, Schedule
from .render import render_email
from .render.admin import render_admin_summary
from .repository import SupabaseRepository
from .scheduler import default_schedule, due_owners, nearest_report_date, with_defaults
from .timeutil import parse_date, utc_now

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TRACKED_KIND = "daily"


class ServiceError(Exception):
    def __init__(self, message: str, status: int = 500):
        super().__init__(message)
        self.status = status


def _result(owner: Owner, status: str, **extra) -> Dict[str, Any]:
    out = {"owner": owner.display_name, "ownerId": owner.id, "email": owner.email or "No email", "status": status}
    out.update(extra)
    return out


class ReportService:
    def __init__(self, settings: Settings, repo: SupabaseRepository, mailer: SesMailer, deliveries: DeliveryLog):
        self.settings = settings
        self.repo = repo
        self.mailer = mailer
        self.deliveries = deliveries

    # ---------------------------------------------------------------- build
    def build_report(self, owner: Owner, location_ids: Sequence[str], report_date: date,
                     template_no: int, timezone: str = "Asia/Kolkata") -> Tuple[Optional[OwnerReport], List[str]]:
        """The owner's report, or (None, reasons) when there is nothing to send."""
        locations = self.repo.get_locations(list(location_ids))
        usable: List[Location] = []
        notes: List[str] = []
        for loc in locations.values():
            if not loc.is_active:
                notes.append(f"{loc.name}: inactive")
            elif loc.is_billing_lapsed:
                notes.append(f"{loc.name}: subscription {loc.billing_status}")
            else:
                usable.append(loc)
        if not usable:
            return None, notes or ["No locations"]
        first_day = report_date - timedelta(days=7)
        reports, failed = [], []
        for loc in sorted(usable, key=lambda l: l.name.lower()):
            try:
                data = self.repo.load_location_dataset(loc, first_day, report_date)
                reports.append(build_location_report(data, report_date))
            except Exception as exc:  # noqa: BLE001 - one bad location must not block the others
                logger.exception("Could not load %s (%s): %s", loc.name, loc.id, exc)
                failed.append(loc.name)
        if not reports:
            raise ServiceError(f"Could not load data for {', '.join(failed)}")
        for r in reports:
            r.warnings.extend(f"{name} (data could not be loaded)" for name in failed)
        return build_owner_report(owner, report_date, template_no, reports, utc_now(), timezone), notes

    def compose(self, report: OwnerReport, owner_id: Optional[str]):
        unsub = unsubscribe_url(self.settings, owner_id) if owner_id and owner_id != "override" else None
        attachments = build_attachments(report, self.settings.attachment_format)
        email = render_email(
            report, app_url=self.settings.app_url, logo_url=self.settings.brand_logo_url,
            brand_name=self.settings.brand_name, unsubscribe_url=unsub,
            attachment_note=attachment_note(self.settings.attachment_format, report.has_activity),
        )
        headers = {"X-PetaLog-Report": f"daily; date={report.day.isoformat()}"}
        if unsub:
            headers["List-Unsubscribe"] = f"<{unsub}>"
            headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        return email, attachments, headers

    # ---------------------------------------------------------------- send
    def deliver(self, owner: Owner, schedule: Schedule, report_date: date, *, trigger: str,
                recipient: Optional[str] = None, location_ids: Optional[Sequence[str]] = None,
                track: bool = True, force: bool = False, require_active: bool = True) -> Dict[str, Any]:
        template = schedule.templateno if schedule.templateno in (1, 2, 3) else 1
        base = {"templateUsed": template, "timezone": schedule.timezone, "reportDate": report_date.isoformat(),
                "trigger": trigger}
        to = recipient or owner.email
        if not to:
            return _result(owner, "skipped", reason="No email address", **base)
        if owner.id != "override":
            if not owner.is_enabled:
                return _result(owner, "skipped", reason="Inactive user status", **base)
            if require_active and schedule.has_row and not schedule.is_active:
                return _result(owner, "skipped", reason="Daily reports turned off", **base)

        claim = self.deliveries.claim(owner.id, report_date, trigger, TRACKED_KIND, force=force) if track else None
        if track and claim is None:
            return _result(owner, "skipped", reason="Already sent", **base)
        try:
            if location_ids is None:
                location_ids = self.repo.get_owner_location_ids([owner.id]).get(owner.id, [])
            if not location_ids:
                if claim:
                    self.deliveries.mark_skipped(claim, "No locations assigned")
                return _result(owner, "skipped", reason="No active locations assigned", **base)
            report, notes = self.build_report(owner, location_ids, report_date, template, schedule.timezone)
            if report is None:
                reason = "No active locations (" + "; ".join(notes) + ")"
                if claim:
                    self.deliveries.mark_skipped(claim, reason)
                return _result(owner, "skipped", reason=reason, **base)
            email, attachments, headers = self.compose(report, owner.id)
            message_id = self.mailer.send(to=[to], subject=email.subject, html=email.html, text=email.text,
                                          attachments=attachments, headers=headers)
            if claim:
                self.deliveries.mark_sent(claim, message_id=message_id, recipient=to, template_no=template,
                                          location_ids=[r.location.id for r in report.locations])
            logger.info("Sent %s report for %s to %s (%s)", report_date, owner.id, to, message_id)
            return _result(
                owner, "success", email=to, messageId=message_id,
                recordCount=sum(len(r.transactions) for r in report.locations),
                revenue=report.total("collections"),
                locations=len(report.locations),
                locationNames=", ".join(r.location.name for r in report.locations),
                attachments=len(attachments),
                emailType="no-data" if not report.has_activity else (
                    "multi-location" if report.is_multi else "single-location"),
                skippedLocations=notes,
                **base,
            )
        except Exception as exc:  # noqa: BLE001 - reported per owner, others continue
            logger.exception("Report for %s failed: %s", owner.id, exc)
            if claim:
                self.deliveries.mark_failed(claim, str(exc))
            return _result(owner, "failed", error=str(exc), **base)

    # ------------------------------------------------------------- dispatch
    def dispatch(self, now=None) -> Dict[str, Any]:
        """Send every report that is due (called every few minutes)."""
        if not self.deliveries.available():
            raise ServiceError("report_deliveries is missing: run sql/001_report_deliveries.sql first "
                               "(dispatch needs it to avoid duplicate emails)", status=503)
        schedules = self.repo.get_schedules(active_only=True)
        if self.settings.include_owners_without_schedule:
            all_schedules = self.repo.get_schedules(active_only=False)
            owners_all = self.repo.get_owners()
            missing = [o for o in owners_all if o not in all_schedules]
            schedules = with_defaults(missing, schedules)
        due = due_owners(schedules.values(), self.settings, now)
        owners = self.repo.get_owners([d.owner_id for d in due]) if due else {}
        results: List[Dict[str, Any]] = []
        for item in due:
            if len(results) >= self.settings.dispatch_max_owners:
                break
            owner = owners.get(item.owner_id)
            if owner is None:
                continue  # not an owner (any more)
            res = self.deliver(owner, item.schedule, item.report_date, trigger="dispatch")
            if res["status"] == "skipped" and res.get("reason") == "Already sent":
                continue
            results.append(res)
        summary = self._summary(results, "dispatch", len(due))
        self._maybe_admin_summary(summary)
        return summary

    # ------------------------------------------------------- legacy endpoint
    def legacy_send(self, payload: Dict[str, Any], caller: Caller) -> Tuple[Dict[str, Any], int]:
        """POST /send-reports, with the request and response shape the
        previous version used (the existing edge function relies on it)."""
        users = payload.get("users") or []
        trigger = str(payload.get("trigger") or "manual")[:40]
        override = (payload.get("email_override") or payload.get("email") or "").strip() or None
        loc_override = payload.get("location_ids") or None
        tmpl_override = payload.get("templateno")
        tz_override = payload.get("timezone")
        date_override = parse_date(payload.get("date")) if payload.get("date") else None

        if not caller.trusted:
            # The anon key is public: never let it redirect mail or widen what is sent.
            if override or loc_override or not users:
                return {"success": False, "error": "Forbidden",
                        "message": "This key can only send the normal report to listed owners."}, 403
            # Harmless fields an older trigger may send: ignored, owners get their own settings.
            tmpl_override = tz_override = date_override = None
        if override and not EMAIL_RE.match(override):
            return {"success": False, "error": f"Invalid email_override: {override}"}, 400
        if not isinstance(users, list):
            return {"success": False, "error": "users must be a list"}, 400
        ids = [str(u.get("user_id")) for u in users if isinstance(u, dict) and u.get("user_id")]
        if users and not ids:
            return {"success": False, "error": "No valid user_id values found in request payload"}, 400
        if loc_override is not None and not isinstance(loc_override, list):
            return {"success": False, "error": "location_ids must be a list"}, 400

        def apply_overrides(schedule: Schedule) -> Schedule:
            changes = {}
            if tmpl_override not in (None, ""):
                try:
                    t = int(tmpl_override)
                    changes["templateno"] = t if t in (1, 2, 3) else 1
                except (TypeError, ValueError):
                    changes["templateno"] = 1
            if tz_override:
                changes["timezone"] = str(tz_override)
            return replace(schedule, **changes) if changes else schedule

        results: List[Dict[str, Any]] = []
        if override and not ids:
            if not loc_override:
                return {"success": False, "error": "email_override needs users or location_ids"}, 400
            owner = Owner(id="override", email=override, first_name=payload.get("first_name"),
                          last_name=payload.get("last_name"))
            schedule = apply_overrides(default_schedule("override"))
            day = date_override or nearest_report_date(schedule, self.settings)
            results.append(self.deliver(owner, schedule, day, trigger=trigger, recipient=override,
                                        location_ids=[str(x) for x in loc_override], track=False))
        else:
            if ids:
                owners = self.repo.get_owners(ids)
                order = [i for i in ids if i in owners]
                schedules = self.repo.get_schedules(order)
            else:  # trusted "everyone" run: owners with report settings turned on
                schedules = self.repo.get_schedules(active_only=True)
                owners = self.repo.get_owners(list(schedules))
                order = sorted(owners)
            for owner_id in order:
                owner = owners[owner_id]
                schedule = apply_overrides(schedules.get(owner_id) or default_schedule(owner_id))
                day = date_override or nearest_report_date(schedule, self.settings)
                results.append(self.deliver(
                    owner, schedule, day, trigger=trigger, recipient=override,
                    location_ids=[str(x) for x in loc_override] if loc_override else None,
                    track=not override and not loc_override, require_active=not override,
                ))

        summary = self._summary(results, trigger, len(ids))
        admin_sent = self._maybe_admin_summary(summary)
        response = {
            "success": True,
            "message": "Daily reports processed",
            "trigger": trigger,
            "scheduledUsersCount": len(users),
            "emailsSent": summary["sent"],
            "emailsFailed": summary["failed"],
            "emailsSkipped": summary["skipped"],
            "totalOwners": len(results),
            "totalRevenue": summary["totalRevenue"],
            "totalRecords": summary["totalRecords"],
            "reportDate": summary["reportDates"][0] if summary["reportDates"] else None,
            "summaryEmailSent": admin_sent,
            "summaryEmailTo": self.settings.admin_recipient if admin_sent else None,
            "deliveryMethod": "AWS SES API",
            "multiLocationSupport": "Enabled",
            "schedulingSupport": "Enabled",
            "templateSource": "user_schedules table",
            "version": "2",
            "results": results,
        }
        return response, 200

    # ------------------------------------------------------------ summaries
    @staticmethod
    def _summary(results: List[Dict[str, Any]], trigger: str, requested: int) -> Dict[str, Any]:
        return {
            "trigger": trigger,
            "requested": requested,
            "sent": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
            "totalRevenue": sum(r.get("revenue", 0) or 0 for r in results),
            "totalRecords": sum(r.get("recordCount", 0) or 0 for r in results),
            "reportDates": sorted({r["reportDate"] for r in results if r.get("reportDate")}),
            "results": results,
        }

    def _maybe_admin_summary(self, summary: Dict[str, Any]) -> bool:
        mode = self.settings.admin_summary_mode
        to = self.settings.admin_recipient
        if mode == "off" or not to or not summary["results"]:
            return False
        if mode == "failures" and not summary["failed"]:
            return False
        try:
            subject, html, text = render_admin_summary(summary)
            self.mailer.send(to=[to], subject=subject, html=html, text=text)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Admin summary not sent: %s", exc)
            return False

    # ------------------------------------------------------------- one-offs
    def send_one(self, user_id: str, *, report_date: Optional[date] = None, recipient: Optional[str] = None,
                 template_no: Optional[int] = None, force: bool = False, trigger: str = "manual") -> Dict[str, Any]:
        owners = self.repo.get_owners([user_id])
        owner = owners.get(user_id)
        if owner is None:
            raise ServiceError("Owner not found", status=404)
        schedule = self.repo.get_schedules([user_id]).get(user_id) or default_schedule(user_id)
        if template_no in (1, 2, 3):
            schedule = replace(schedule, templateno=template_no)
        day = report_date or nearest_report_date(schedule, self.settings)
        return self.deliver(owner, schedule, day, trigger=trigger, recipient=recipient,
                            track=recipient is None, force=force, require_active=recipient is None and not force)

    def preview(self, user_id: str, report_date: Optional[date] = None, template_no: Optional[int] = None) -> str:
        owner = self.repo.get_owners([user_id]).get(user_id)
        if owner is None:
            raise ServiceError("Owner not found", status=404)
        schedule = self.repo.get_schedules([user_id]).get(user_id) or default_schedule(user_id)
        template = template_no if template_no in (1, 2, 3) else schedule.templateno
        day = report_date or nearest_report_date(schedule, self.settings)
        ids = self.repo.get_owner_location_ids([user_id]).get(user_id, [])
        report, notes = self.build_report(owner, ids, day, template, schedule.timezone)
        if report is None:
            raise ServiceError("Nothing to report: " + "; ".join(notes), status=404)
        email, _, _ = self.compose(report, None)
        return email.html

