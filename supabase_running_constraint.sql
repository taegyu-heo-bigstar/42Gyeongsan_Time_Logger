-- Run the diagnostic query first. If it returns more than one row, stop the
-- duplicate RUNNING records manually before creating the index.
select id, work_date, start_time, status
from public.time_logs
where status = 'RUNNING'
order by start_time;

-- PostgreSQL partial unique index: only one RUNNING log may exist at a time.
create unique index if not exists time_logs_single_running_idx
on public.time_logs ((1))
where status = 'RUNNING';
