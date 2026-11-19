# PetaLog Email Backend (v2)

A Flask service that sends each PetaLog owner a daily report email through AWS SES. It reads Supabase with the service-role key, uses the same rules as the PetaLog dashboard to compute each location's day, and renders the template the owner chose in **Profile Settings → Daily Reports**.

For deployment, see [RELEASE.md](RELEASE.md).

## How a report gets sent

```
pg_cron (every 5 min) ──► edge function report-dispatch ──► POST /v1/dispatch
                                                               │
     user_schedules: preferred_time + timezone + template ─────┤ who is due now (with catch-up)
     report_deliveries: claim (owner, day) ────────────────────┤ never twice
     log-man, ticket_payments, retail_sales, ledgers, ... ─────┤ figures = dashboard rules
     Jinja2 template 1 / 2 / 3 + Excel workbook ───────────────┘ AWS SES
```

During the switch-over the old trigger (cron `send_reports` → edge function `send_reports` → `POST /send-reports`) keeps working. Both triggers share `report_deliveries`, so an owner gets each day's report once.

## Rules

| Rule | Behaviour |
|---|---|
| Who | Owners (`users.role = 'owner'`) with an active `user_schedules` row. Owners who never saved report settings are left out unless `INCLUDE_OWNERS_WITHOUT_SCHEDULE=true`. |
| When | At `preferred_time` in the owner's `timezone`. A send missed while the service was asleep or down goes out on the next run, up to `DISPATCH_CATCHUP_MINUTES` (default 180) later. |
| Which day | The India (IST) business day, as in the app. A send before 12:00 covers the **previous full day**; a later send covers the same day. |
| Locations | `locations.own_id` plus `location_owners` (co-owners). Inactive locations and those whose PetaLog subscription is `read_only` or `archived` (`view_locations_billing`) are left out. |
| Skipped | Disabled users (`users.status = false`), turned-off schedules, owners with no usable location. Recorded with a reason. |
| Once | `report_deliveries` keeps one row per owner and day. Failed sends retry, up to `DELIVERY_MAX_ATTEMPTS` (default 3). |

## Figures (same as the dashboard)

`petalog_reports/metrics.py` reproduces the database functions behind the Dashboard and Reports. Each one is named in that module's docstring.

- **Collections:** approved tickets paid that day, not on Pay Later, dated by `payment_date`, else `exit_time`, else `created_at`. Split payments count each part on its own date, so Pay Later money settled today counts today. Counter sales and old dues collected are added. The amount is `COALESCE(total, amount − discount)`.
- **Payment modes:** Cash, UPI (broken down by UPI account), Card, Bank Transfer, and From advance.
- **Other figures:** vehicles served (4W / 2W / other), Pay Later given, tickets waiting for approval, expenses.
- **Services:** the day's work, with combined services shared out by catalogue price.
- **Money in & out:** expenses, staff expenses, salaries and staff advances, the net for the day, and cash in hand (when the cash book is installed).
- **Customers and team:** new vs returning customers, and entries recorded per staff member.

## Templates

| No. | Name in the app | Email |
|---|---|---|
| 1 | Classic Business | Every figure in clear tables |
| 2 | Modern Analytics | Adds bar charts and activity through the day |
| 3 | Business Intelligence | Adds highlights, a comparison with yesterday and the same weekday last week, and a 7-day trend |

Every template supports multiple locations (consolidated figures, a location table, then each location), a quiet-day version, a plain-text version, and an Excel attachment.

To preview with sample data, run `python scripts/render_previews.py` (writes `previews/*.html`) or open `/dev/preview?template=1..3&locations=1..3` locally.

## Endpoints

| Route | Auth | Purpose |
|---|---|---|
| `POST /v1/dispatch` | secret or service key | Send everything due. Returns 202 and runs in the background; `?wait=1` runs it synchronously. |
| `POST /v1/reports/send` | secret or service key | `{"user_id", "date"?, "email_override"?, "templateno"?, "force"?}`: one owner, now. |
| `GET /v1/reports/preview` | secret or service key | `?user_id=&date=&template=`: the owner's email as HTML. Nothing is sent. |
| `GET/POST /v1/unsubscribe` | signed link | Footer link and one-click unsubscribe. Sets `user_schedules.is_active = false`. |
| `POST /send-reports` | secret, service key, or anon key | The v1 contract, unchanged. The anon key may only send the normal report to listed owners. |
| `GET /health` | none | Liveness check, with the version. |
| `/dev`, `/dev/preview`, `/dev/send-reports` | localhost, `ENABLE_DEV_ROUTE=true` | Local tools. |

Bearer tokens are `REPORTS_API_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`, or (only while `ALLOW_ANON_KEY_AUTH=true`) `SUPABASE_ANON_KEY`.

## Configuration

All v1 variable names keep their meaning. [.env.example](.env.example) lists every variable with its default.

## Project layout

```text
main.py                      entry point (gunicorn main:app), CLI test mode
petalog_reports/
  config.py                  settings
  repository.py              Supabase reads, paged
  metrics.py                 dashboard-equivalent figures
  builder.py                 owner report, insights, subject, preview text
  render/                    Jinja2 templates (macros, sections, report) + admin summary
  exports.py                 Excel / CSV
  mailer.py                  MIME + SES with retries
  deliveries.py              report_deliveries claims
  scheduler.py               due times and the report-day rule
  service.py                 orchestration
  api.py                     Flask routes
  sample.py                  made-up data for previews
sql/                         001 table (+verify, rollback), 002 cron switch-over
supabase/functions/report-dispatch/   the new trigger
scripts/render_previews.py
tests/                       pytest; no network
```

## Development

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt pytest
.venv\Scripts\python -m pytest
.venv\Scripts\python scripts\render_previews.py
```

To send a one-off from the command line (to a test address), set `CLI_TEST=true`, `CLI_UUID=<owner>` and `CLI_EMAIL=<you>`, then run `python main.py`. You can also set `CLI_TEMPLATE`, `CLI_DATE`, or `CLI_LOCATIONS` (when `CLI_UUID` is not set).
