from datetime import datetime, timedelta
import csv

from airflow import DAG
from airflow.operators.python import PythonOperator
import psycopg


def extract(path):
    with open(path, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


def transform(rows):
    for r in rows:
        if not r.get("appointment_id"):
            continue
        yield {
            "appointment_id": r["appointment_id"].strip(),
            "amount": round(float(r["amount"] or 0), 2),
            "day": r["date"][:10],
        }


def load(dsn, rows):
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO stg_appointments (appointment_id, amount, day) VALUES (%(appointment_id)s, %(amount)s, %(day)s)", list(rows))


default_args = {"owner": "data", "retries": 3, "retry_delay": timedelta(minutes=10)}

with DAG(
    dag_id="appointments_nightly",
    start_date=datetime(2024, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    default_args=default_args,
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=extract_appointments)
    transform = PythonOperator(task_id="transform", python_callable=transform_appointments)
    load = PythonOperator(task_id="load", python_callable=load_appointments)
    extract >> transform >> load
