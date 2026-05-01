CREATE TABLE etl_watermark (
    job_name VARCHAR2(100) PRIMARY KEY,
    last_run DATE
);
