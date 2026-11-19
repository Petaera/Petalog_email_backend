// report-dispatch: the daily report trigger.
//
// pg_cron calls this every 5 minutes (sql/002_cron_report_dispatch.sql). It
// forwards one POST to the Python backend's /v1/dispatch, which works out
// which owners are due (their preferred time, a catch-up window for missed
// sends) and sends each owner's report once.
//
// Secrets (supabase secrets set ...):
//   REPORTS_BACKEND_URL   e.g. https://petalog-email-backend.onrender.com
//   REPORTS_API_SECRET    the same value as REPORTS_API_SECRET on Render
//
// Deployed with verify_jwt on (supabase/config.toml): the gateway checks the
// token's signature; this function then only accepts the service role, so
// the public anon key cannot trigger sends.

const BACKEND_URL = (Deno.env.get("REPORTS_BACKEND_URL") ?? "").replace(/\/+$/, "");
const API_SECRET = Deno.env.get("REPORTS_API_SECRET") ?? "";
// Render's free tier sleeps: the first call after a quiet spell can take ~50s.
const TIMEOUT_MS = 55_000;

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function roleOf(authorization: string | null): string | null {
  const token = authorization?.startsWith("Bearer ") ? authorization.slice(7).trim() : "";
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const padded = payload.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(payload.length / 4) * 4, "=");
    return (JSON.parse(atob(padded)) as { role?: string }).role ?? null;
  } catch {
    return null;
  }
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ ok: false, error: "POST only" }, 405);
  if (roleOf(req.headers.get("Authorization")) !== "service_role") {
    return json({ ok: false, error: "Forbidden" }, 403);
  }
  if (!BACKEND_URL || !API_SECRET) {
    return json({ ok: false, error: "REPORTS_BACKEND_URL / REPORTS_API_SECRET are not set" }, 500);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${BACKEND_URL}/v1/dispatch`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${API_SECRET}`, "Content-Type": "application/json" },
      body: "{}",
      signal: controller.signal,
    });
    const text = await res.text();
    let backend: unknown = text.slice(0, 500);
    try {
      backend = JSON.parse(text);
    } catch {
      // keep the text
    }
    // A missed run is not lost: the next run (5 minutes later) catches up.
    return json({ ok: res.ok, backendStatus: res.status, backend }, res.ok ? 200 : 502);
  } catch (err) {
    const timedOut = err instanceof DOMException && err.name === "AbortError";
    return json({ ok: false, error: timedOut ? "Backend did not answer in time (waking up?)" : String(err) }, 504);
  } finally {
    clearTimeout(timer);
  }
});
