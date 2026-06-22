-- 1. Diagnose invalid rows before adding constraints.
select *
from public.time_logs
where status not in ('RUNNING', 'COMPLETED', 'AUTO_STOPPED')
   or duration_seconds < 0
   or (status = 'RUNNING' and (end_time is not null or duration_seconds is not null))
   or (status <> 'RUNNING' and (end_time is null or duration_seconds is null));

-- Stop here and correct any rows returned above.

-- 2. Add data consistency constraints. These statements are safe to rerun.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'time_logs_status_check'
  ) then
    alter table public.time_logs
      add constraint time_logs_status_check
      check (status in ('RUNNING', 'COMPLETED', 'AUTO_STOPPED'));
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'time_logs_duration_check'
  ) then
    alter table public.time_logs
      add constraint time_logs_duration_check
      check (duration_seconds is null or duration_seconds >= 0);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'time_logs_state_check'
  ) then
    alter table public.time_logs
      add constraint time_logs_state_check
      check (
        (status = 'RUNNING' and end_time is null and duration_seconds is null)
        or
        (status <> 'RUNNING' and end_time is not null and duration_seconds is not null)
      );
  end if;
end $$;

create index if not exists time_logs_work_date_start_idx
on public.time_logs (work_date, start_time);
