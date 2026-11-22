"""PetaLog daily reports service: entry point.

Run locally:     python main.py
Run on Render:   gunicorn main:app   (unchanged; `app` is the Flask app)

All logic lives in the petalog_reports package. This file only builds the
app and keeps the CLI test mode of the previous version:

    CLI_TEST=true CLI_UUID=<owner uuid> CLI_EMAIL=<test address> python main.py
"""

import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from petalog_reports.api import create_app  # noqa: E402
from petalog_reports.config import Settings  # noqa: E402

settings = Settings.from_env()
app = create_app(settings)


def _cli_test() -> int:
    """One-off send from the command line (CLI_* variables or prompts)."""
    uuid = (os.getenv("CLI_UUID") or "").strip()
    email = (os.getenv("CLI_EMAIL") or "").strip()
    if not uuid:
        try:
            uuid = input("Enter user UUID (optional, press Enter to skip): ").strip()
        except EOFError:
            uuid = ""
    if not email:
        try:
            email = input("Enter email to send report to: ").strip()
        except EOFError:
            email = ""
    payload = {"trigger": "cli"}
    if uuid:
        payload["users"] = [{"user_id": uuid}]
    if email:
        payload["email_override"] = email
    for env_name, key in (("CLI_TEMPLATE", "templateno"), ("CLI_TIMEZONE", "timezone"), ("CLI_DATE", "date")):
        if os.getenv(env_name):
            payload[key] = os.getenv(env_name).strip()
    locations = [s.strip() for s in (os.getenv("CLI_LOCATIONS") or "").split(",") if s.strip()]
    if locations:
        payload["location_ids"] = locations
    token = settings.reports_api_secret or settings.supabase_service_role_key
    if not token:
        print("Missing REPORTS_API_SECRET / SUPABASE_SERVICE_ROLE_KEY in environment")
        return 1
    client = app.test_client()
    resp = client.post("/send-reports", json=payload, headers={"Authorization": f"Bearer {token}"})
    print(f"CLI Test completed with status {resp.status_code}")
    print(json.dumps(resp.get_json(), indent=2, ensure_ascii=False))
    return 0 if resp.status_code == 200 else 1


if __name__ == "__main__":
    if os.getenv("CLI_TEST", "false").lower() == "true":
        sys.exit(_cli_test())
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
