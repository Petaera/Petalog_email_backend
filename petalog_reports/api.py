"""HTTP routes.

Kept from the previous version (same request / response contract):
    POST /send-reports        the current edge function calls this
    GET  /health
    GET  /dev, /dev/send-reports   local only, ENABLE_DEV_ROUTE=true

New:
    POST /v1/dispatch          every few minutes: sends whatever is due
    POST /v1/reports/send      one owner, now (resend / test)
    GET  /v1/reports/preview   one owner's email as HTML, nothing sent
    GET|POST /v1/unsubscribe   link in the email footer
    GET  /dev/preview          sample-data preview, local only
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from flask import Flask, Response, jsonify, request
from markupsafe import escape

from . import __version__
from .auth import Caller, authenticate, check_unsubscribe
from .config import Settings
from .deliveries import DeliveryLog
from .mailer import SesMailer
from .repository import SupabaseRepository
from .service import ReportService, ServiceError
from .timeutil import parse_date

logger = logging.getLogger(__name__)

LOCAL = ("127.0.0.1", "::1")


def build_service(settings: Settings) -> ReportService:
    repo = SupabaseRepository(settings)
    return ReportService(settings, repo, SesMailer(settings), DeliveryLog(settings, _LazyClient(repo)))


class _LazyClient:
    """Defers creating the Supabase client until first use (keeps imports
    and /health working when the environment is incomplete)."""

    def __init__(self, repo: SupabaseRepository):
        self._repo = repo

    def __getattr__(self, name):
        return getattr(self._repo.client, name)


def create_app(settings: Optional[Settings] = None, service: Optional[ReportService] = None) -> Flask:
    settings = settings or Settings.from_env()
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    state = {"service": service}
    dispatch_lock = threading.Lock()

    def svc() -> ReportService:
        if state["service"] is None:
            state["service"] = build_service(settings)
        return state["service"]

    def caller() -> Optional[Caller]:
        return authenticate(request.headers.get("Authorization"), settings)

    def unauthorized():
        return jsonify({"success": False, "error": "Unauthorized - Missing or invalid Authorization header",
                        "message": "Please provide a valid Authorization header with Bearer token"}), 401

    def forbidden():
        return jsonify({"success": False, "error": "Forbidden"}), 403

    def local_dev_only():
        if not settings.enable_dev_route:
            return jsonify({"success": False, "error": "Dev route disabled"}), 404
        if (request.remote_addr or "").strip() not in LOCAL:
            return jsonify({"success": False, "error": "Forbidden - local only"}), 403
        return None

    # ------------------------------------------------------------ health
    @app.get("/health")
    def health():
        return jsonify({"status": "healthy", "service": "daily-reports", "version": __version__,
                        "delivery": "AWS SES API", "features": "Multi-location + User scheduling enabled"}), 200

    # ------------------------------------------------------------ legacy
    @app.post("/send-reports")
    def send_reports():
        who = caller()
        if who is None:
            return unauthorized()
        missing = [n for n, v in (("SES_VERIFIED_FROM", settings.ses_from),
                                  ("SUPABASE_URL", settings.supabase_url),
                                  ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key)) if not v]
        if missing:
            return jsonify({"success": False, "error": f"Missing required environment variable: {missing[0]}"}), 500
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"success": False, "error": "JSON object expected"}), 400
        try:
            body, status = svc().legacy_send(payload, who)
            return jsonify(body), status
        except ServiceError as exc:
            return jsonify({"success": False, "error": str(exc)}), exc.status
        except Exception as exc:  # noqa: BLE001
            logger.exception("send-reports failed")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ------------------------------------------------------------ dispatch
    def run_dispatch():
        try:
            summary = svc().dispatch()
            logger.info("Dispatch done: %s sent, %s failed, %s skipped",
                        summary["sent"], summary["failed"], summary["skipped"])
        except Exception:  # noqa: BLE001
            logger.exception("Dispatch failed")
        finally:
            dispatch_lock.release()

    @app.post("/v1/dispatch")
    def dispatch():
        who = caller()
        if who is None:
            return unauthorized()
        if not who.trusted:
            return forbidden()
        if not svc().deliveries.available():
            return jsonify({"ok": False, "error": "report_deliveries table missing: run sql/001_report_deliveries.sql"}), 503
        if not dispatch_lock.acquire(blocking=False):
            return jsonify({"ok": True, "started": False, "message": "A dispatch is already running"}), 202
        if request.args.get("wait") in ("1", "true"):
            try:
                summary = svc().dispatch()
            except ServiceError as exc:
                return jsonify({"ok": False, "error": str(exc)}), exc.status
            finally:
                dispatch_lock.release()
            return jsonify({"ok": True, **summary}), 200
        threading.Thread(target=run_dispatch, name="report-dispatch", daemon=True).start()
        return jsonify({"ok": True, "started": True}), 202

    # ------------------------------------------------------------ one owner
    @app.post("/v1/reports/send")
    def send_one():
        who = caller()
        if who is None:
            return unauthorized()
        if not who.trusted:
            return forbidden()
        body = request.get_json(silent=True) or {}
        user_id = str(body.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"success": False, "error": "user_id is required"}), 400
        try:
            template = int(body["templateno"]) if body.get("templateno") not in (None, "") else None
        except (TypeError, ValueError):
            template = None
        try:
            result = svc().send_one(user_id, report_date=parse_date(body.get("date")),
                                    recipient=(body.get("email_override") or None), template_no=template,
                                    force=bool(body.get("force")), trigger=str(body.get("trigger") or "manual"))
        except ServiceError as exc:
            return jsonify({"success": False, "error": str(exc)}), exc.status
        return jsonify({"success": result["status"] == "success", "result": result}), 200

    @app.get("/v1/reports/preview")
    def preview():
        who = caller()
        if who is None:
            return unauthorized()
        if not who.trusted:
            return forbidden()
        user_id = (request.args.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        try:
            template = int(request.args["template"]) if request.args.get("template") else None
        except ValueError:
            template = None
        try:
            html = svc().preview(user_id, parse_date(request.args.get("date")), template)
        except ServiceError as exc:
            return jsonify({"error": str(exc)}), exc.status
        return Response(html, mimetype="text/html")

    # ------------------------------------------------------------ unsubscribe
    def _page(title: str, body: str, status: int = 200) -> Response:
        html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(title)}</title></head><body style=\"margin:0;background:#F1F5F9;font-family:Inter,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;\">"
            "<div style='max-width:480px;margin:48px auto;padding:28px;background:#fff;border:1px solid #E2E8F0;border-top:4px solid #004AC6;border-radius:12px;color:#334155;font-size:15px;line-height:1.6;'>"
            f"<div style='font-size:20px;font-weight:700;color:#0F172A;margin-bottom:8px;'>{escape(title)}</div>{body}</div></body></html>"
        )
        return Response(html, status=status, mimetype="text/html")

    @app.route("/v1/unsubscribe", methods=["GET", "POST"])
    def unsubscribe():
        owner_id = (request.values.get("u") or "").strip()
        token = (request.values.get("t") or "").strip()
        if not owner_id or not check_unsubscribe(settings, owner_id, token):
            return _page("Link not valid", "<p>This link is incomplete or has expired.</p>", 400)
        settings_link = f"{settings.app_url}/profileSettings"
        if request.method == "GET":
            # A confirmation step: link scanners open links but do not submit forms.
            return _page("Stop daily report emails?", (
                "<p>You will no longer receive the PetaLog daily report email.</p>"
                f"<form method='post' action='?u={escape(owner_id)}&t={escape(token)}'>"
                "<button type='submit' style='background:#004AC6;color:#fff;border:0;border-radius:8px;padding:10px 18px;font-size:15px;font-weight:600;cursor:pointer;'>Stop the emails</button></form>"
                f"<p style='font-size:13px;color:#64748B;'>Or <a href='{escape(settings_link)}'>change the time or template</a> instead.</p>"))
        try:
            svc().repo.set_schedule_active(owner_id, False)
        except Exception:  # noqa: BLE001
            logger.exception("Unsubscribe failed for %s", owner_id)
            return _page("Something went wrong", "<p>Please try again in a minute.</p>", 500)
        return _page("Daily reports stopped", (
            "<p>You will not receive the daily report email any more.</p>"
            f"<p>To turn it back on, save your report settings in <a href='{escape(settings_link)}'>Profile Settings &rarr; Daily Reports</a>.</p>"))

    # ------------------------------------------------------------ dev
    @app.get("/dev/preview")
    def dev_preview():
        blocked = local_dev_only()
        if blocked:
            return blocked
        from .render import render_email
        from .sample import sample_report

        try:
            template = int(request.args.get("template", 3))
            locations = int(request.args.get("locations", 1))
        except ValueError:
            template, locations = 3, 1
        report = sample_report(template, max(1, min(locations, 3)), quiet=request.args.get("quiet") == "1")
        email = render_email(report, app_url=settings.app_url, logo_url=settings.brand_logo_url,
                             attachment_note="Every entry of the day is in the attached Excel workbook.")
        return Response(email.html, mimetype="text/html")

    @app.route("/dev/send-reports", methods=["GET", "POST"])
    def dev_send_reports():
        blocked = local_dev_only()
        if blocked:
            return blocked
        token = settings.reports_api_secret or settings.supabase_service_role_key
        if not token:
            return jsonify({"success": False, "error": "Missing REPORTS_API_SECRET / SUPABASE_SERVICE_ROLE_KEY"}), 500
        payload = request.get_json(silent=True) if request.is_json else {}
        payload = payload or {}
        payload.setdefault("trigger", "dev")
        with app.test_request_context("/send-reports", method="POST", json=payload,
                                      headers={"Authorization": f"Bearer {token}"}):
            return send_reports()

    @app.get("/dev")
    def dev_ui():
        blocked = local_dev_only()
        if blocked:
            return blocked
        return Response(DEV_PAGE, mimetype="text/html")

    return app


DEV_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dev: daily reports</title>
<style>
body{font-family:Inter,-apple-system,'Segoe UI',Arial,sans-serif;background:#F1F5F9;margin:0;color:#334155}
.wrap{max-width:920px;margin:32px auto;background:#fff;border:1px solid #E2E8F0;border-top:4px solid #004AC6;border-radius:12px;overflow:hidden}
header{padding:20px 24px;border-bottom:1px solid #E2E8F0}h1{margin:0;font-size:20px;color:#0F172A}
main{padding:24px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
label{display:block;font-size:12px;color:#64748B;margin:12px 0 4px;text-transform:uppercase;letter-spacing:.04em}
input,textarea{width:100%;box-sizing:border-box;padding:9px 11px;border:1px solid #CBD5E1;border-radius:8px;font-size:14px}
button{background:#004AC6;color:#fff;border:0;border-radius:8px;padding:9px 14px;font-weight:600;cursor:pointer;margin:14px 8px 0 0}
pre{background:#0F172A;color:#E2E8F0;border-radius:10px;padding:14px;overflow:auto;max-height:420px;font-size:12px}
a{color:#004AC6}.note{font-size:12px;color:#64748B}
</style></head><body><div class="wrap"><header><h1>Daily reports: dev tools</h1>
<div class="note">Local only. Previews with sample data: <a href="/dev/preview?template=1" target="_blank">Classic</a> ·
<a href="/dev/preview?template=2" target="_blank">Modern</a> · <a href="/dev/preview?template=3" target="_blank">Business Intelligence</a> ·
<a href="/dev/preview?template=3&locations=3" target="_blank">3 locations</a> · <a href="/dev/preview?template=1&quiet=1" target="_blank">quiet day</a></div></header>
<main><div>
<label>Owner IDs (comma separated)</label><textarea id="ids" rows="2" placeholder="uuid-1, uuid-2"></textarea>
<label>Send to this address instead (test)</label><input id="email" placeholder="you@example.com">
<label>Template (1-3)</label><input id="tpl" placeholder="from settings">
<label>Report date (YYYY-MM-DD)</label><input id="date" placeholder="automatic">
<label>Location IDs (with test address, no owners)</label><input id="locs" placeholder="loc-1, loc-2">
<button onclick="go()">Send</button>
<div class="note">Without a test address, owners get their real report (once per day).</div>
</div><div><label>Response</label><pre id="out">(nothing yet)</pre></div></main></div>
<script>
async function go(){
 const v=id=>document.getElementById(id).value.trim();
 const ids=v('ids').split(',').map(s=>s.trim()).filter(Boolean);
 const body={trigger:'dev'}; if(ids.length) body.users=ids.map(user_id=>({user_id}));
 if(v('email')) body.email_override=v('email'); if(v('tpl')) body.templateno=v('tpl'); if(v('date')) body.date=v('date');
 const locs=v('locs').split(',').map(s=>s.trim()).filter(Boolean); if(locs.length) body.location_ids=locs;
 const r=await fetch('/dev/send-reports',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2);
}
</script></body></html>"""
