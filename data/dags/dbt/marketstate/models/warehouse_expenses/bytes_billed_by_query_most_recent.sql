SELECT
    creation_time,
    user_email,
    query,
    total_bytes_billed
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
ORDER BY creation_time DESC