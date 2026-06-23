# 42Gyeongsan Time Logger

FastAPI, Supabase, and a static calendar UI for recording work time.

## Environment

Generate the admin password hash from the repository root:

```bash
python -m scripts.hash_password
```

Generate a separate session signing secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create a `.env` file for the API. Never store the plain admin password:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
ADMIN_PASSWORD_HASH=pbkdf2_sha256$...
SESSION_SECRET=your-random-session-secret
SESSION_TTL_SECONDS=28800
ALLOWED_ORIGINS=
COOKIE_SECURE=true
```

Install and run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The frontend uses same-origin API paths by default.

The production frontend and API are expected to use the same origin. For a
separate local frontend, set `ALLOWED_ORIGINS` to the exact origin and set
`COOKIE_SECURE=false` only while using local HTTP.

## Authentication rollout

1. Add `ADMIN_PASSWORD_HASH` and `SESSION_SECRET` to Vercel environment variables.
2. Remove the old `ADMIN_PASSWORD` environment variable.
3. Redeploy, log in, and confirm that the browser stores an HttpOnly
   `time_logger_session` cookie rather than the password.
4. Rotating `SESSION_SECRET` signs every active session out immediately.

The application does not keep a reusable password in browser storage. Session
cookies expire after `SESSION_TTL_SECONDS` and are `HttpOnly`, `Secure`, and
`SameSite=Lax` in production.

Authenticated write requests also require the `X-Requested-With: time-logger`
header. This gives the cookie-based session a small CSRF guard while keeping the
single-user deployment simple.

## Supabase concurrency constraint

The API relies on a partial unique index to guarantee that only one log can
have `RUNNING` status. In the Supabase dashboard, open **SQL Editor**, copy all
of `supabase_running_constraint.sql`, and run it.

The first query lists current `RUNNING` records. If it returns multiple rows,
manually change all obsolete rows to `AUTO_STOPPED` or `COMPLETED`, then run
the `create unique index` statement. The script intentionally does not modify
or delete existing records.

Then copy and run `supabase_data_constraints.sql`. Its first query is a
diagnostic; correct any returned rows before running the constraint block.
RLS is intentionally outside this project's current single-user scope.

## Login rate limiting

Process-local counters are unreliable on Vercel serverless instances. Configure
a Vercel Firewall rate-limit rule for `POST /login`, for example 5 requests per
minute per IP. The API also keeps a small in-process failed-login limiter as a
backup, but the Vercel Firewall rule should remain the production control.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```
