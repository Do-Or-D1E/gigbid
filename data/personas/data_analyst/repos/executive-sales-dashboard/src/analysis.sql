WITH weekly AS (
    SELECT
        date_trunc('week', created_at)          AS week,
        count(*)                                AS orders,
        sum(amount)                             AS revenue,
        count(*) FILTER (WHERE status = 'refunded') AS refunds
    FROM orders
    WHERE created_at >= current_date - interval '26 weeks'
    GROUP BY 1
)
SELECT
    week,
    orders,
    revenue,
    round(refunds::numeric / nullif(orders, 0), 4)           AS refund_rate,
    revenue - lag(revenue) OVER (ORDER BY week)               AS revenue_change,
    avg(revenue) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS revenue_4wk_avg
FROM weekly
ORDER BY week;

-- metric dictionary: each KPI has one definition, owned by one team
CREATE OR REPLACE VIEW kpi_monthly AS
SELECT
    date_trunc('month', created_at)                                    AS month,
    sum(amount) FILTER (WHERE status = 'paid')                         AS net_revenue,
    count(DISTINCT customer_id) FILTER (WHERE status = 'paid')         AS paying_customers,
    sum(amount) FILTER (WHERE status = 'paid')
        / nullif(count(DISTINCT customer_id) FILTER (WHERE status = 'paid'), 0) AS arpu,
    count(*) FILTER (WHERE status = 'refunded')::numeric / nullif(count(*), 0)  AS refund_rate
FROM orders
GROUP BY 1;

COMMENT ON VIEW kpi_monthly IS 'Owner: finance. Refunds counted in the month of the original sale.';
