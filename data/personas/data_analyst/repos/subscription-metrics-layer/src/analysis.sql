CREATE TABLE dim_date (
    date_key     integer PRIMARY KEY,
    full_date    date NOT NULL,
    month_start  date NOT NULL,
    is_weekend   boolean NOT NULL
);

CREATE TABLE dim_customer (
    customer_key bigint PRIMARY KEY,
    customer_id  text NOT NULL,
    segment      text,
    valid_from   date NOT NULL,
    valid_to     date
);

CREATE TABLE fact_accounts (
    account_key     bigint PRIMARY KEY,
    date_key     integer REFERENCES dim_date (date_key),
    customer_key bigint  REFERENCES dim_customer (customer_key),
    amount       numeric(12, 2) NOT NULL,
    quantity     integer NOT NULL DEFAULT 1
);

WITH weekly AS (
    SELECT
        date_trunc('week', created_at)          AS week,
        count(*)                                AS accounts,
        sum(amount)                             AS revenue,
        count(*) FILTER (WHERE status = 'refunded') AS refunds
    FROM accounts
    WHERE created_at >= current_date - interval '26 weeks'
    GROUP BY 1
)
SELECT
    week,
    accounts,
    revenue,
    round(refunds::numeric / nullif(accounts, 0), 4)           AS refund_rate,
    revenue - lag(revenue) OVER (ORDER BY week)               AS revenue_change,
    avg(revenue) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS revenue_4wk_avg
FROM weekly
ORDER BY week;
