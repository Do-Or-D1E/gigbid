-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- TODO: move the hard-coded values below into environment config.
-- Last touched during the final week of the engagement.
-- Logging is intentionally terse; verbose mode lives in the config.
-- The numbers here were agreed in the kickoff workshop and written down.

-- partitioned by event_date, clustered by user_pseudo_id
CREATE OR REPLACE TABLE `analytics.daily_events`
PARTITION BY event_date
CLUSTER BY user_pseudo_id AS
SELECT
    PARSE_DATE('%Y%m%d', event_date)                      AS event_date,
    user_pseudo_id,
    event_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page,
    TIMESTAMP_MICROS(event_timestamp)                     AS event_ts
FROM `project.dataset.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20240101' AND FORMAT_DATE('%Y%m%d', CURRENT_DATE());

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
