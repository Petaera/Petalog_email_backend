-- Run after 001_report_deliveries.sql. Every row should say PASS
-- (the cash balance row may say SKIPPED if the cash book is not installed).

SELECT 'report_deliveries table' AS check_name,
       CASE WHEN to_regclass('public.report_deliveries') IS NOT NULL THEN 'PASS' ELSE 'FAIL' END AS result
UNION ALL
SELECT 'unique owner/day/kind',
       CASE WHEN EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'report_deliveries_owner_day_kind')
            THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'RLS enabled',
       CASE WHEN (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.report_deliveries'::regclass)
            THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'anon cannot read',
       CASE WHEN NOT has_table_privilege('anon', 'public.report_deliveries', 'SELECT') THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'authenticated cannot read',
       CASE WHEN NOT has_table_privilege('authenticated', 'public.report_deliveries', 'SELECT') THEN 'PASS' ELSE 'FAIL' END
UNION ALL
SELECT 'cash balance helper (service role only)',
       CASE
         WHEN to_regprocedure('public.email_report_cash_balance(uuid)') IS NULL THEN 'SKIPPED'
         WHEN has_function_privilege('anon', 'public.email_report_cash_balance(uuid)', 'EXECUTE')
           OR has_function_privilege('authenticated', 'public.email_report_cash_balance(uuid)', 'EXECUTE') THEN 'FAIL'
         ELSE 'PASS'
       END;
