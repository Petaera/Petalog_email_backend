-- Undo 001_report_deliveries.sql. Deletes the send history.
-- Only needed if the backend is rolled back to the old version for good.

DROP FUNCTION IF EXISTS public.email_report_cash_balance(uuid);
DROP TABLE IF EXISTS public.report_deliveries;
