-- =============================================================================
-- PetaLog email backend v2: database objects
--
-- 1. public.report_deliveries  send history + duplicate protection
-- 2. public.email_report_cash_balance(location)  optional, read-only helper
--    so the email can show "Cash in hand" (only created when the cash book
--    feature, private.location_cash_balance, exists)
--
-- Run once in Supabase -> SQL Editor. Safe to run again (idempotent).
-- Changes nothing that the PetaLog app uses. Rollback: 001_rollback.sql.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.report_deliveries (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id        uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  report_date     date NOT NULL,
  kind            text NOT NULL DEFAULT 'daily',
  status          text NOT NULL DEFAULT 'sending'
                    CHECK (status IN ('sending', 'sent', 'failed', 'skipped')),
  attempts        integer NOT NULL DEFAULT 1,
  trigger         text,
  recipient       text,
  template_no     integer,
  location_ids    uuid[],
  ses_message_id  text,
  error           text,
  claimed_at      timestamptz NOT NULL DEFAULT now(),
  sent_at         timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT report_deliveries_owner_day_kind UNIQUE (owner_id, report_date, kind)
);

CREATE INDEX IF NOT EXISTS report_deliveries_report_date_idx
  ON public.report_deliveries (report_date DESC);

COMMENT ON TABLE public.report_deliveries IS
  'Daily report emails: one row per owner, day and kind. Written only by the email backend (service role).';

-- Only the service role (which bypasses RLS) may read or write: RLS on, no policies.
ALTER TABLE public.report_deliveries ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.report_deliveries FROM anon, authenticated;
GRANT ALL ON public.report_deliveries TO service_role;


-- Cash in hand for the email. The app's get_location_cash_balance needs a
-- signed-in owner (auth.uid()), so the backend cannot call it; this wrapper
-- returns the same private.location_cash_balance result to the service role only.
DO $do$
BEGIN
  IF to_regprocedure('private.location_cash_balance(uuid)') IS NOT NULL
     AND to_regprocedure('private.is_trusted_backend_caller()') IS NOT NULL THEN
    EXECUTE $fn$
      CREATE OR REPLACE FUNCTION public.email_report_cash_balance(p_location_id uuid)
      RETURNS jsonb
      LANGUAGE plpgsql
      STABLE
      SECURITY DEFINER
      SET search_path TO ''
      AS $body$
      BEGIN
        IF NOT private.is_trusted_backend_caller() THEN
          RAISE EXCEPTION 'Only the report backend may call this' USING ERRCODE = '42501';
        END IF;
        IF p_location_id IS NULL THEN
          RETURN NULL;
        END IF;
        RETURN private.location_cash_balance(p_location_id);
      END;
      $body$;
    $fn$;
    REVOKE ALL ON FUNCTION public.email_report_cash_balance(uuid) FROM PUBLIC, anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.email_report_cash_balance(uuid) TO service_role;
  ELSE
    RAISE NOTICE 'Cash book not installed: email_report_cash_balance not created (emails leave out cash in hand).';
  END IF;
END
$do$;
