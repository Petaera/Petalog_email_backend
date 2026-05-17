# Petalog Email Backend

Petalog Email Backend is a Flask service that generates and sends daily transaction reports to scheduled owners through AWS SES. It reads data from Supabase, builds per-location analysis, attaches CSV exports, and renders one of three HTML email templates depending on the user schedule.

The service is aligned to India Standard Time (IST, UTC+05:30) for query windows, report labels, and timestamps.

## What it does

- Fetches approved transaction data from Supabase for the current IST day.
- Groups reports by owner and assigned location.
- Sends one email per owner, with support for single-location and multi-location reporting.
- Uses three template styles, including CID-embedded images in templates 2 and 3.
- Exports CSV attachments for the main report, payment breakdown, and service breakdown.
- Supports owner-specific schedules for template number and timezone.
- Skips inactive users and ignores inactive locations.

## Current business rules

- If `users.status` is `false`, the user does not receive email.
- If `users.status` is `true`, email is sent only for locations where `locations.is_active` is `true`.
- Owners with no email are skipped.
- Owners with no active assigned locations are skipped.
- Reports are based on approved records only.

## Project Structure

```text
Petalog_email_backend/
  main.py         Flask app, Supabase access, analysis, email sending
  template1.py    HTML-only template
  template2.py    HTML template with embedded charts
  template3.py    HTML template with embedded charts
  requirements.txt Python dependencies
```

## Tech Stack

- Flask
- Supabase Python client
- AWS SES via boto3
- Matplotlib and NumPy for chart generation
- Python-dotenv for local configuration

## Key Endpoints

### `POST /send-reports`

Protected endpoint that generates and sends reports.

Authentication:
- Send a Bearer token in the `Authorization` header.
- The token must match `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_ANON_KEY`.

Example body:

```json
{
  "users": [{ "user_id": "<uuid>" }],
  "trigger": "manual",
  "email_override": "test@example.com",
  "templateno": 1,
  "timezone": "Asia/Kolkata",
  "location_ids": ["<location-id-1>", "<location-id-2>"]
}
```

Notes:
- `users` is optional. If omitted, the service can process all owners in the database.
- `email_override` bypasses the Supabase user lookup and sends to the provided address.
- `templateno`, `timezone`, and `location_ids` are useful for testing and controlled runs.

### `GET /health`

Simple health endpoint that confirms the service is running.

### Dev-only routes

Available only when `ENABLE_DEV_ROUTE=true`:

- `GET /dev`
- `GET` or `POST /dev/send-reports`

These are intended for local testing and proxy to the main send flow.

## Data Model

The service expects a Supabase schema with at least these tables.

### `public.users`

Relevant fields used by the app:

```sql
create table public.users (
  id uuid not null default auth.uid(),
  email text not null,
  role text not null,
  assigned_location uuid null,
  created_at timestamp with time zone null default now(),
  own_id uuid null,
  status boolean null default true,
  first_name text null,
  last_name text null,
  phone text null,
  constraint users_pkey primary key (id),
  constraint users_email_key unique (email),
  constraint users_phone_key unique (phone)
);
```

### `public.locations`

Relevant fields used by the app:

```sql
create table public.locations (
  id uuid not null default extensions.uuid_generate_v4(),
  name text not null,
  address text null,
  created_at timestamp with time zone null default now(),
  own_id uuid null,
  migration_completed boolean null default false,
  logo_url text null,
  address_line1 text null,
  address_line2 text null,
  city text null,
  state text null,
  postal_code text null,
  country text null,
  location_phone_no text null,
  location_email text null,
  authorised_signature_url text null,
  avg_rating numeric null default 0,
  rating_count integer null default 0,
  is_active boolean null default true,
  constraint locations_pkey primary key (id)
);
```

The `locations.is_active` flag is used to exclude inactive locations from report delivery.

### Logs table

The transaction table defaults to `log-man`, but can be overridden with `SUPABASE_LOGS_TABLE`.

The service expects fields such as:

- `created_at`
- `approval_status`
- `loc_id`
- `veh_id`
- `cust_id`
- `payment_mode`
- `service`
- `entry_type`
- transaction amount fields such as `Amount`, `amount`, or `total`

## Timezone Handling

All daily report windows are computed for the current IST day.

Implementation helpers in [main.py](main.py):

- `IST_TZ`
- `now_ist()`
- `format_now_ist()`
- `ist_day_utc_bounds()`
- `parse_iso_to_ist()`
- `format_iso_as_ist()`

## Email Templates

- Template 1 returns plain HTML content.
- Template 2 returns a related MIME message with embedded images.
- Template 3 returns a related MIME message with embedded images and BI-style charts.

Template selection is driven by user schedule data or a request override.

## CSV Attachments

Each location in a report can produce three CSV files:

- `report_<date>_<location>.csv`
- `payment_<date>_<location>.csv`
- `service_<date>_<location>.csv`

They contain transaction rows, payment summaries, and service breakdowns respectively.

## Configuration

### Required environment variables

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SES_VERIFIED_FROM`

### Optional environment variables

- `SUPABASE_ANON_KEY`
- `SUPABASE_LOGS_TABLE`
- `ENABLE_DEV_ROUTE`
- `PORT`
- `CLI_TEST`
- `CLI_UUID`
- `CLI_EMAIL`
- `CLI_TEMPLATE`
- `CLI_TIMEZONE`
- `CLI_LOCATIONS`

## Install and Run

```powershell
cd Petalog_email_backend

$env:SUPABASE_URL="https://<project>.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="<service_role_key>"
$env:AWS_REGION="us-east-1"
$env:AWS_ACCESS_KEY_ID="<aws_access_key_id>"
$env:AWS_SECRET_ACCESS_KEY="<aws_secret_access_key>"
$env:SES_VERIFIED_FROM="Your Name <verified@yourdomain.com>"
$env:ENABLE_DEV_ROUTE="true"

python -m pip install -r requirements.txt
python main.py
```

The app listens on `PORT` if provided, otherwise it uses `5000`.

## CLI Test Mode

When `CLI_TEST=true`, the app can prompt for a user UUID and/or email address, then run a one-off report send from the command line.

This is useful for local validation without exposing the dev routes.

## Deployment Notes

- The app runs as a standard Flask service and works well behind Gunicorn.
- Make sure the SES sender address is verified.
- Confirm AWS SES is allowed to send from the chosen region.
- Set all required environment variables in your host platform.

## Troubleshooting

- Unauthorized error: confirm the Bearer token matches one of the Supabase keys.
- No email sent: check `users.status`, assigned locations, and whether the location is active.
- Empty report: verify the log table has approved records for the current IST day.
- SES failure: confirm the sender address, AWS credentials, region, and SES sending quota.
- Missing charts: confirm `matplotlib` and `Pillow` are installed.

## License

Internal or proprietary use unless stated otherwise.
