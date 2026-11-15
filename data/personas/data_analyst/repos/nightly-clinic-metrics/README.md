# Nightly clinic metrics pipeline

Code behind a healthcare project. The aim was to load appointment and billing exports every night into one clean reporting database.

## Stack

- PostgreSQL
- Python
- Airflow

## Getting started

```
See the files under src/ in order.
```

## Layout

- `src/db/migrations/0004_add_indexes.sql`
- `src/docker-compose.yml`
- `src/helpers.py`
