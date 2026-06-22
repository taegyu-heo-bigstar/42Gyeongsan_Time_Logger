# 42Gyeongsan Time Logger

FastAPI, Supabase, and a static calendar UI for recording work time.

## Environment

Create a `.env` file for the API:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
ADMIN_PASSWORD=your-admin-password
```

Install and run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Set `API_BASE` at the top of `app.js` to the deployed API URL when necessary.

## Supabase concurrency constraint

The API relies on a partial unique index to guarantee that only one log can
have `RUNNING` status. In the Supabase dashboard, open **SQL Editor**, copy all
of `supabase_running_constraint.sql`, and run it.

The first query lists current `RUNNING` records. If it returns multiple rows,
manually change all obsolete rows to `AUTO_STOPPED` or `COMPLETED`, then run
the `create unique index` statement. The script intentionally does not modify
or delete existing records.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```
