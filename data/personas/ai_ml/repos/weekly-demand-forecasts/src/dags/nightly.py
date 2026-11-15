from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {"owner": "data", "retries": 3, "retry_delay": timedelta(minutes=10)}

with DAG(
    dag_id="shipments_nightly",
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    default_args=default_args,
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_shipments)
    transform = PythonOperator(task_id="transform", python_callable=transform_shipments)
    load = PythonOperator(task_id="load", python_callable=load_shipments)
    extract >> transform >> load


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
