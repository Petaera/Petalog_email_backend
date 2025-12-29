# Petalog Email Backend

Daily reports email service built with Flask, Supabase, and AWS SES. It fetches approved transactions per owner and location, generates rich HTML emails using templates, and attaches CSV breakdowns. Time handling is aligned to India Standard Time (IST, UTC+05:30).

## Features
- Multi-location daily reports per owner (single or consolidated multi-location emails)
- Three email templates (inline images supported via CID in template 2 & 3)
- CSV attachments: main report, payment breakdown, service breakdown
- Owner-specific scheduling support (template number, timezone)
- Supabase-backed data with explicit joins to `vehicle` and `cust`
- Vehicle model resolution via `veh_det` → `Vehicles_in_india`.`Models`
- Delivery via AWS SES API (no SMTP), with raw MIME preserving inline images
- Dev-only local UI to trigger and test runs

## Repository Structure
```
Petalog_email_backend/
  main.py               # Flask app + core logic (fetch, analyze, render, send)
  requirements.txt      # Python dependencies
  template1.py          # Template 1 (returns HTML string)
  template2.py          # Template 2 (returns MIMEMultipart with images)
  template3.py          # Template 3 (returns MIMEMultipart with images)
```

See [Petalog_email_backend/main.py](Petalog_email_backend/main.py) for full implementation.

## Tech Stack
- Flask 3
- Supabase Python client 2.21
- AWS SES (boto3)
- Matplotlib/Numpy for charts (used by templates)

## Data Model (Key Tables)
Below are the relevant tables and relationships used by the service:

- `log-man` (main transaction table; renamed/configurable via `SUPABASE_LOGS_TABLE`)
  - Foreign keys: `veh_id` → `vehicle.id`, `cust_id` → `cust.id`, `loc_id` → `locations.id`
  - Important columns used: `created_at`, `approval_status`, `Amount/amount/total`, `payment_mode`, `service`, `entry_type`, optional `upi_account_name`

- `vehicle`
```
create table public.vehicle (
  id uuid not null default extensions.uuid_generate_v4(),
  number_plate text not null,
  type text null,
  owner_id uuid null,
  created_at timestamp without time zone null default CURRENT_TIMESTAMP,
  veh_det uuid null,
  constraint vehicle_pkey primary key (id),
  constraint vehicle_number_plate_key unique (number_plate),
  constraint vehicle_owner_id_fkey foreign key (owner_id) references cust (id) on delete cascade,
  constraint vehicle_veh_det_fkey foreign key (veh_det) references "Vehicles_in_india" (id) on delete set null
);
```

- `Vehicles_in_india`
```
create table public."Vehicles_in_india" (
  "Vehicle Brands" text null,
  "Models" text null,
  id uuid not null default gen_random_uuid(),
  type text null,
  constraint Vehicles_in_india_pkey primary key (id),
  constraint Vehicles_in_india_id_key unique (id)
);
```

- `cust`
```
create table public.cust (
  id uuid not null default extensions.uuid_generate_v4(),
  phone text null,
  name text null,
  email text null,
  dob date null,
  constraint cust_pkey primary key (id),
  constraint cust_email_key unique (email),
  constraint cust_phone_key unique (phone)
);
```

### How lookups work
- Owner details: `cust:cust_id(id,name,phone)` joined and mapped to `Name` and `Phone_no`.
- Vehicle details: `vehicle:veh_id(id,number_plate,type,veh_det)` joined; then a batch query fetches models from `Vehicles_in_india` using the `veh_det` IDs and maps to `vehicle_model` using the quoted column `"Models"`.

## Timezone Handling (IST)
Daily windows and all displayed times are aligned to IST (UTC+05:30):
- Query window uses IST midnight→midnight converted to UTC before filtering in Supabase.
- Email footers and plain-text sections show "Generated on" in IST.
- CSV dates and hourly analysis use IST.

Implementation helpers in [Petalog_email_backend/main.py](Petalog_email_backend/main.py):
- `IST_TZ`, `now_ist()`, `format_now_ist()`
- `ist_day_utc_bounds()` to compute UTC bounds for the IST calendar day
- `parse_iso_to_ist()`, `format_iso_as_ist()` for parsing/rendering timestamps

## Environment Variables
Required:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `AWS_REGION`: AWS region for SES (e.g., `us-east-1`)
- `AWS_ACCESS_KEY_ID`: AWS key with SES send permission
- `AWS_SECRET_ACCESS_KEY`: AWS secret for the above
- `SES_VERIFIED_FROM`: Verified sender (e.g., `Your Name <verified@domain.com>`) 

Optional:
- `SUPABASE_ANON_KEY`: Used if you want to authorize using anon key
- `SUPABASE_LOGS_TABLE`: Default `log-man`
- `ENABLE_DEV_ROUTE`: `true` to enable `/dev` local helper UI
- `PORT`: Flask port (default 5000)

## Install & Run (Windows PowerShell)
```powershell
cd Petalog_email_backend

# 1) Set env vars (example)
$env:SUPABASE_URL="https://<project>.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="<service_role_key>"
$env:AWS_REGION="us-east-1"
$env:AWS_ACCESS_KEY_ID="<aws_access_key_id>"
$env:AWS_SECRET_ACCESS_KEY="<aws_secret_access_key>"
$env:SES_VERIFIED_FROM="Your Name <verified@yourdomain.com>"
$env:ENABLE_DEV_ROUTE="true"    # optional
$env:PORT="5000"                # optional

# 2) Install dependencies
python -m pip install -r requirements.txt

# 3) Run
python main.py
```

## API Endpoints
### POST /send-reports
- Auth: Bearer token in `Authorization` header; token must match `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_ANON_KEY`.
- Body (JSON):
```
{
  "users": [{ "user_id": "<uuid>" }],   # optional; if omitted, processes all owners
  "trigger": "manual|schedule|dev",      # optional, for logs
  "email_override": "test@domain.com",   # optional; bypass user lookup and send to this email
  "templateno": 1,                         # optional; override template number
  "timezone": "Asia/Kolkata",            # optional; override user timezone
  "location_ids": ["loc-1","loc-2"]     # optional; restrict locations
}
```
- Response: JSON summary including success/failed/skipped counts, totals, and per-owner results.

Example (PowerShell):
```powershell
$token = $env:SUPABASE_SERVICE_ROLE_KEY
$body = '{ "trigger": "manual", "email_override": "test@example.com", "templateno": 1, "timezone": "Asia/Kolkata" }'
curl -Method POST `
  -Uri http://127.0.0.1:5000/send-reports `
  -Headers @{ Authorization = "Bearer $token"; 'Content-Type' = 'application/json' } `
  -Body $body
```

### Dev routes (local only)
- GET `/dev`: Simple UI to trigger runs (must set `ENABLE_DEV_ROUTE=true`).
- POST `/dev/send-reports`: Proxies to `/send-reports` with a locally-generated token.

## Email Templates
- Template 1: returns HTML string (wrapped into a related MIME for sending)
- Template 2 & 3: return `MIMEMultipart('related')` with embedded images via CID
- Selection: per-user `templateno` (from `user_schedules`) or override via request body

## CSV Attachments
For each location included in an email:
- `report_<YYYY-MM-DD>_<location>.csv`: Vehicle number, Owner name/phone, Vehicle model, Service, Price, Payment mode, UPI account, Entry type, Date (IST), Location
- `payment_<YYYY-MM-DD>_<location>.csv`: Payment mode breakdown with UPI account details
- `service_<YYYY-MM-DD>_<location>.csv`: Service breakdown with counts and revenue

## Deployment Notes
- The app is a standard Flask server suitable for Render, Azure App Service, etc.
- Ensure your SES sender is verified and the region supports SES out of sandbox for production.
- Configure environment variables in your hosting platform.

## Troubleshooting
- "Unauthorized - Invalid token": Check `Authorization: Bearer <key>` matches one of your Supabase keys.
- SES send error: Confirm AWS credentials, `SES_VERIFIED_FROM`, region, and that the address is verified. Check sending quotas.
- No data in emails: Verify `log-man` has `approval_status='approved'` records within the IST day window for the specified locations and owners.
- Time appears 5:30h behind: Confirm you are looking at the updated build; code uses IST for query windows and rendering.
- Vehicle model missing: Ensure `vehicle.veh_det` is populated and corresponding `Vehicles_in_india` rows exist; column name is `"Models"`.

## Contributing
- Open issues/PRs for bugs and enhancements.

## License
- Proprietary/internal unless stated otherwise.
