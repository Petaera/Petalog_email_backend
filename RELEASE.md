# Releasing email backend v2

Four phases. Each phase can be checked before the next one starts, and each can be undone on its own. Owners keep getting reports the whole time: the old trigger stays on until the new one has proved itself.

| Phase | What | Time | Owner-visible? |
|---|---|---|---|
| 1 | Database: `report_deliveries` table | 5 min | No |
| 2 | Render: environment variables + deploy v2 | 15 min | Yes: the next report uses the new design |
| 3 | New trigger: edge function + cron, old cron off | 20 min + a day of watching | No |
| 4 | Hardening: turn off anon-key access | 2 min, a few days later | No |

You need:

- Access to the Supabase dashboard and the Render dashboard.
- The Supabase CLI for phase 3 (`npm i -g supabase`, then `supabase login`).
- **The Render service URL:** `https://petalog-email-backend.onrender.com`. Render deploys `main`, and deploys are started by hand.

---

## Before you start

1. **In Render**, open the service, then **Settings**. Note:
   - **Branch.** Note which branch the service deploys (`main` or `location`). This work is on `feature/reports-v2`, which branched from `location`, the newest branch.
   - **Start Command.** It should be `gunicorn main:app`, or `python main.py`. Either keeps working. The recommended command for the free tier is:
     ```
     gunicorn main:app --workers 1 --threads 4 --timeout 120
     ```
   - **Python version.** v2 needs Python 3.9 or newer. v1 already required 3.9. If a build fails on Python, add the environment variable `PYTHON_VERSION=3.11.9`.
2. **In Render**, open **Deploys** and note the live deploy. It is your rollback point (each deploy has a **Rollback** button).
3. Generate the shared secret and keep it for phases 2 and 3:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

---

## Phase 1: Database

1. In Supabase, open **SQL Editor** and run all of [sql/001_report_deliveries.sql](sql/001_report_deliveries.sql).
2. Run [sql/001_verify.sql](sql/001_verify.sql). Every row should say `PASS`. The cash-balance row may say `SKIPPED` if the cash book feature isn't installed; emails then leave out "Cash in hand".

Nothing in the PetaLog app uses this table, so nothing changes for anyone yet.

---

## Phase 2: Deploy the new backend

### 2.1 Environment variables (Render, then Environment)

Keep every existing variable. Add these:

| Variable | Value |
|---|---|
| `REPORTS_API_SECRET` | the secret you generated |
| `REPORTS_PUBLIC_URL` | `https://petalog-email-backend.onrender.com` (used for unsubscribe links) |
| `ADMIN_REPORT_EMAIL` | optional: where failure summaries go. Default is the `SES_VERIFIED_FROM` address. |

Leave `ALLOW_ANON_KEY_AUTH` unset (it defaults to `true`) until phase 4. The current edge function may be using the anon key.

The other variables in [.env.example](.env.example) are optional, and their defaults are the agreed behaviour.

### 2.2 Deploy

Render deploys `main`. Bring local `main` up to date with GitHub, merge, and push:

```powershell
git checkout main
```
```powershell
git pull --ff-only origin main
```
```powershell
git merge --no-ff feature/reports-v2
```
```powershell
git push origin main
```

Then in Render choose **Manual Deploy → Deploy latest commit**. The build is faster than before because matplotlib and numpy are gone.

### 2.3 Check it

The examples use these PowerShell variables. Set them first:

```powershell
$base = "https://petalog-email-backend.onrender.com"; $secret = "<REPORTS_API_SECRET>"; $h = @{ Authorization = "Bearer $secret" }
```

1. **Health.** Expect `"version": "2.0.0"`.
   ```powershell
   Invoke-RestMethod "$base/health"
   ```
2. **Send a test report to yourself.** Use an owner id from `public.users` and yesterday's date. This doesn't count as that owner's real send.
   ```powershell
   Invoke-RestMethod -Method Post "$base/v1/reports/send" -Headers $h -ContentType "application/json" -Body '{"user_id":"<owner-uuid>","date":"2026-11-19","email_override":"you@petaera.com","templateno":3}'
   ```
   Repeat with `templateno` 1 and 2. Open each one in Gmail on the web, Gmail on a phone and Outlook. Open the Excel attachment.
3. **Compare the numbers.** Open the PetaLog dashboard for the same location and date. Collections, the Cash/UPI/Card split, vehicles, Pay Later, pending and expenses should match exactly.
4. **Preview without sending:**
   ```powershell
   Invoke-WebRequest "$base/v1/reports/preview?user_id=<owner-uuid>&date=2026-11-19" -Headers $h -OutFile preview.html
   ```
   ```powershell
   Start-Process preview.html
   ```
5. **After the next scheduled time** (most owners use 21:00), run this in the SQL Editor:
   ```sql
   SELECT left(content::text, 200), created FROM net._http_response ORDER BY created DESC LIMIT 10;
   SELECT report_date, status, count(*) FROM public.report_deliveries GROUP BY 1, 2 ORDER BY 1 DESC;
   ```
   Responses from the old trigger should contain `"version": "2"`, and `report_deliveries` should show `sent` rows.

   If a response is `403 Forbidden`, the old edge function sends more than a list of owners while using the public anon key, which v2 no longer allows, so those reports are not going out. Go straight to phase 3: the new trigger doesn't use the anon key. If you can't do phase 3 now, roll back as below.

**Rollback:** Render, then **Deploys**, then **Rollback** on the previous deploy. The table from phase 1 is harmless to the old version.

---

## Phase 3: Switch to the new trigger

Run these from the backend repository root.

1. Set the edge function's secrets and deploy it:
   ```powershell
   supabase secrets set REPORTS_BACKEND_URL=https://petalog-email-backend.onrender.com REPORTS_API_SECRET=<secret> --project-ref poqzxjhsdbwfnooftiwe
   ```
   ```powershell
   supabase functions deploy report-dispatch --project-ref poqzxjhsdbwfnooftiwe
   ```
2. Try it once by hand with the service role key. Expect `{"ok": true, "backendStatus": 202, ...}`. A `504` means Render was asleep; call it again.
   ```powershell
   Invoke-RestMethod -Method Post "https://poqzxjhsdbwfnooftiwe.supabase.co/functions/v1/report-dispatch" -Headers @{ Authorization = "Bearer <SERVICE_ROLE_KEY>" } -ContentType "application/json" -Body '{}'
   ```
3. In the SQL Editor, open [sql/002_cron_report_dispatch.sql](sql/002_cron_report_dispatch.sql). Replace `<SERVICE_ROLE_KEY>` in **STEP 1** and run STEP 1 only.
4. Watch it for 15 minutes with the STEP 1 check queries. Each run should answer `200` with `"ok": true`.
5. **Leave both triggers on until the next evening's sends are done.** `report_deliveries` makes sure nobody gets two emails. Check the monitoring queries at the end of the 002 file the next morning.
6. Then run **STEP 2**. It turns the old `send_reports` job off without deleting it.

From now on, a send missed while Render is asleep goes out on the next 5-minute run instead of being lost. That 503 failure at 21:00 is what silently cost the 12 owners at 21:00 their reports on 19 Nov.

**Rollback:** the two commented lines at the end of the 002 file turn the old job back on and remove the new one.

---

## Phase 4: Hardening (a few days later)

1. In Render, set `ALLOW_ANON_KEY_AUTH=false`. The public anon key can then no longer reach `/send-reports` at all.
2. Optionally, delete the old edge functions `send_reports`, `send_daily_reports` and `cron-job` in Supabase (their code is empty in the dashboard), and the old `send_reports` cron job:
   ```sql
   SELECT cron.unschedule('send_reports');
   ```

---

## What owners will notice

- **New design.** It is in the PetaLog blue, in the template they picked, and readable on phones.
- **Numbers match the dashboard.** Old emails counted Pay Later as income and ignored discounts, so new totals can be lower and are now correct. Split payments and Pay Later money settled later are counted properly.
- **Morning send times** (before 12:00) now report the previous full day instead of a few hours of today.
- **More detail:** UPI by account, pending approvals, expenses and net, cash in hand, team activity, and new vs returning customers. Business Intelligence adds comparisons and a 7-day trend.
- **One Excel file** instead of three CSV files per location. To get CSV back, set `REPORT_ATTACHMENT_FORMAT=csv`.
- **Unsubscribe.** A "Stop these emails" link appears in the footer once `REPORTS_PUBLIC_URL` is set.
- **Lapsed locations.** Locations whose subscription is read-only or archived no longer get reports. An owner with only such locations gets none.
- **Admin email.** You (the admin address) only get an email when something fails.

## Day-to-day

- **Resend a day:**
  ```powershell
  Invoke-RestMethod -Method Post "$base/v1/reports/send" -Headers $h -ContentType "application/json" -Body '{"user_id":"<uuid>","date":"YYYY-MM-DD","force":true}'
  ```
- **Failures:** use the queries at the end of `sql/002_cron_report_dispatch.sql`.
- **Render logs:** each send logs `Sent <date> report for <owner> to <email> (<SES message id>)`.
