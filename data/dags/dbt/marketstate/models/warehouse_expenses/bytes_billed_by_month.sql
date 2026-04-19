SELECT
    FORMAT_DATE('%Y-%m', DATE(creation_time)) as creation_month,
    SUM(total_bytes_billed) as total_bytes_billed,
    SUM(total_bytes_billed) / 1e6 as total_bytes_billed_mb,
    SUM(total_bytes_billed) / 1e9 as total_bytes_billed_gb,
    SUM(total_bytes_billed) / 1e12 as total_bytes_billed_tb,
    round(SUM(total_bytes_billed) / 1e12 * 100, 0) as percentage_used_1_TiB
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
GROUP BY FORMAT_DATE('%Y-%m', DATE(creation_time))
ORDER BY creation_month DESC