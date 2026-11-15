# Listing price estimator

Internal tooling from a real estate engagement. Goal: estimate a fair asking price for new listings from comparable recent sales.

## Stack

- PostgreSQL
- pandas
- scikit-learn

## Getting started

```
pip install -r requirements.txt
python pipeline.py
```

## Layout

- `src/pipeline.py`
- `src/queries/weekly_summary.sql`
