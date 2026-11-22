-- =============================================================================
-- Switch the daily report trigger to report-dispatch.
-- Run in Supabase -> SQL Editor, ONE STEP AT A TIME, in the order given in
-- RELEASE.md. Before running step 1, replace <SERVICE_ROLE_KEY> with the
-- project's service_role key (Project Settings -> API), the same way the
-- existing jobs (e.g. daily-reminders-job) carry it.
-- =============================================================================


-- STEP 1. New job: every 5 minutes, call report-dispatch. --------------------
-- Safe to run while the old send_reports job is still on: every owner/day is
-- sent once (report_deliveries), whichever trigger gets there first.
SELECT cron.schedule(
  'report-dispatch',
  '*/5 * * * *',
  $job$
  SELECT net.http_post(
    url := 'https://poqzxjhsdbwfnooftiwe.supabase.co/functions/v1/report-dispatch',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer <SERVICE_ROLE_KEY>'
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 60000
  );
  $job$
);


-- STEP 1 check: the new job's runs and what the edge function answered. ------
-- Expect status 200/202 with {"ok":true,...}. A 502/504 right after a quiet
-- spell means Render was waking up; the next run catches up.
SELECT j.jobname, d.status, d.start_time AT TIME ZONE 'Asia/Kolkata' AS start_ist
FROM cron.job_run_details d JOIN cron.job j USING (jobid)
WHERE j.jobname = 'report-dispatch'
ORDER BY d.start_time DESC
LIMIT 12;

SELECT id, status_code, left(content::text, 300) AS content_start,
       created AT TIME ZONE 'Asia/Kolkata' AS created_ist
FROM net._http_response
ORDER BY created DESC
LIMIT 20;


-- STEP 2. Turn the old trigger OFF (kept, not deleted, for rollback). --------
SELECT cron.alter_job(
  job_id := (SELECT jobid FROM cron.job WHERE jobname = 'send_reports'),
  active := false
);


-- Monitoring: today's and yesterday's sends. ----------------------------------
SELECT report_date, status, count(*) AS owners, max(updated_at) AT TIME ZONE 'Asia/Kolkata' AS last_update_ist
FROM public.report_deliveries
WHERE report_date >= current_date - 1
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- Failures with their error:
SELECT d.report_date, u.email, d.status, d.attempts, d.error, d.updated_at AT TIME ZONE 'Asia/Kolkata' AS at_ist
FROM public.report_deliveries d JOIN public.users u ON u.id = d.owner_id
WHERE d.status IN ('failed', 'skipped')
ORDER BY d.updated_at DESC
LIMIT 50;


-- ROLLBACK (only if needed). ---------------------------------------------------
-- SELECT cron.alter_job(job_id := (SELECT jobid FROM cron.job WHERE jobname = 'send_reports'), active := true);
-- SELECT cron.unschedule('report-dispatch');
