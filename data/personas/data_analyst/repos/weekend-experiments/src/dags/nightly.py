from datetime import datetime, timedelta
import time

from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {"owner": "data", "retries": 3, "retry_delay": timedelta(minutes=10)}

with DAG(
    dag_id="parts_nightly",
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    default_args=default_args,
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_parts)
    transform = PythonOperator(task_id="transform", python_callable=transform_parts)
    load = PythonOperator(task_id="load", python_callable=load_parts)
    extract >> transform >> load


def retry(fn, attempts=3, delay=1.0):
    for n in range(attempts):
        try:
            return fn()
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(delay * (2 ** n))


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]
