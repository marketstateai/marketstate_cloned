SELECT
    date(creation_time) as creation_time,
    count(total_bytes_billed) as queries_run,
    sum(total_bytes_billed) as total_bytes_billed,
    sum(total_bytes_billed) / 1e6 as total_bytes_billed_mb,
    sum(total_bytes_billed) / 1e9 as total_bytes_billed_gb,
    sum(total_bytes_billed) / 1e12 as total_bytes_billed_tb
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
group by date(creation_time) 
ORDER BY date(creation_time)  DESC

