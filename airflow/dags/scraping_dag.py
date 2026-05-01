"""
scraping_dag.py - Airflow DAG: Scraping Pipeline (RAW Layer)
Schedule: Every 20 minutes (*/20 * * * *)
SLA: 30 minutes

Random scraping strategy:
  1. Pick a random page from 1-50 on books.toscrape.com
  2. Scrape all 20 books from that page
  3. Randomly select 8 books from the 20
  4. Load selected books into db_scraping_raw

Tasks:
  fetch_html -> parse_books -> validate_schema -> load_raw

Purpose: Fetch books from books.toscrape.com, extract categories from detail pages,
validate, and append to db_scraping_raw (append-only, scraper is source of truth).
"""
import sys
sys.path.insert(0, "/opt/airflow/plugins")

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from etl_tasks import fetch_html_fn, parse_books_fn, validate_schema_fn, load_raw_fn

default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "owner": "data_engineer"
}

with DAG(
    dag_id="scraping_dag",
    schedule_interval="*/20 * * * *",
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=default_args,
    sla_miss_callback=lambda *a, **kw: print("SLA missed: scraping_dag > 30min"),
    tags=["etl", "scraping"],
    max_active_runs=1,
    concurrency=2
) as dag:

    fetch_html = PythonOperator(task_id="fetch_html", python_callable=fetch_html_fn)
    parse_books = PythonOperator(task_id="parse_books", python_callable=parse_books_fn)
    validate_schema = PythonOperator(task_id="validate_schema", python_callable=validate_schema_fn)
    load_raw = PythonOperator(task_id="load_raw", python_callable=load_raw_fn)

    fetch_html >> parse_books >> validate_schema >> load_raw
