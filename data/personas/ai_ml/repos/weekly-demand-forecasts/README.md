# Weekly demand forecasts for regional warehouses

Internal tooling from a logistics engagement. Goal: predict weekly demand per product and warehouse so buyers stop over-ordering.

Built with pandas, XGBoost, and Airflow.

### Run

```
pip install -r requirements.txt
python core.py
```

### Notes

Config lives in environment variables. See `.env.example` (not committed).
