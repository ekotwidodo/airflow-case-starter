"""
mart_dag.py - Airflow DAG: Data Mart Pipeline (MART Layer)
Schedule: Every 1 hour (0 * * * *)
SLA: 60 minutes

Tasks:
  extract_staging -> upsert_dim_book -> insert_fact

Purpose: Extract from db_staging, sync dim_book (add new, remove orphans),
then TRUNCATE+RELOAD fact_books. Full sync ensures dashboard always reflects
the current staging state.
"""
import sys
sys.path.insert(0, "/opt/airflow/plugins")

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from etl_tasks import extract_staging_fn, upsert_dim_book_fn, insert_fact_fn

default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "owner": "data_engineer"
}

with DAG(
    dag_id="mart_dag",
    schedule_interval="0 * * * *",
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=default_args,
    sla_miss_callback=lambda *a, **kw: print("SLA missed: mart_dag > 60min"),
    tags=["etl", "mart"],
    max_active_runs=1,
) as dag:

    extract_staging = PythonOperator(task_id="extract_staging", python_callable=extract_staging_fn)
    upsert_dim_book = PythonOperator(task_id="upsert_dim_book", python_callable=upsert_dim_book_fn)
    insert_fact = PythonOperator(task_id="insert_fact", python_callable=insert_fact_fn)

    extract_staging >> upsert_dim_book >> insert_fact
