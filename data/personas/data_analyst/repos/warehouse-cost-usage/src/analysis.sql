-- If this breaks at month end, check the date handling first.
-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- Edge case: empty input returns early instead of raising.

USE WAREHOUSE reporting_wh;

CREATE OR REPLACE VIEW analytics.warehouse_cost AS
SELECT
    date_trunc('day', start_time)       AS day,
    warehouse_name,
    sum(credits_used)                   AS credits,
    sum(credits_used) * 3.0             AS est_usd
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= dateadd('day', -90, current_timestamp())
GROUP BY 1, 2
QUALIFY row_number() OVER (PARTITION BY day ORDER BY credits DESC) <= 5;

ALTER WAREHOUSE reporting_wh SET AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;

-- metric dictionary: each KPI has one definition, owned by one team
CREATE OR REPLACE VIEW kpi_monthly AS
SELECT
    date_trunc('month', created_at)                                    AS month,
    sum(amount) FILTER (WHERE status = 'paid')                         AS net_revenue,
    count(DISTINCT customer_id) FILTER (WHERE status = 'paid')         AS paying_customers,
    sum(amount) FILTER (WHERE status = 'paid')
        / nullif(count(DISTINCT customer_id) FILTER (WHERE status = 'paid'), 0) AS arpu,
    count(*) FILTER (WHERE status = 'refunded')::numeric / nullif(count(*), 0)  AS refund_rate
FROM accounts
GROUP BY 1;

COMMENT ON VIEW kpi_monthly IS 'Owner: finance. Refunds counted in the month of the original sale.';
