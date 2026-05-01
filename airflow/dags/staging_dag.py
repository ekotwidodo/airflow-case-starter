"""
staging_dag.py - Airflow DAG: Staging Pipeline (STG Layer)
Schedule: Every 40 minutes (*/40 * * * *)
SLA: 45 minutes

Tasks:
  extract_raw -> validate_data -> deduplicate -> load_staging

Purpose: Extract books from BOTH db_scraping_raw AND db_library, merge them,
validate, deduplicate by SK=SHA-256(title+price), then TRUNCATE+RELOAD db_staging.
Full sync ensures deletes/edits in source databases propagate downstream.
"""
import sys
sys.path.insert(0, "/opt/airflow/plugins")

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from etl_tasks import extract_raw_fn, validate_data_fn, deduplicate_fn, load_staging_fn

default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "owner": "data_engineer"
}

with DAG(
    dag_id="staging_dag",
    schedule_interval="*/40 * * * *",
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=default_args,
    sla_miss_callback=lambda *a, **kw: print("SLA missed: staging_dag > 45min"),
    tags=["etl", "staging"],
    max_active_runs=1,
) as dag:

    extract_raw = PythonOperator(task_id="extract_raw", python_callable=extract_raw_fn)
    validate_data = PythonOperator(task_id="validate_data", python_callable=validate_data_fn)
    deduplicate = PythonOperator(task_id="deduplicate", python_callable=deduplicate_fn)
    load_staging = PythonOperator(task_id="load_staging", python_callable=load_staging_fn)

    extract_raw >> validate_data >> deduplicate >> load_staging
