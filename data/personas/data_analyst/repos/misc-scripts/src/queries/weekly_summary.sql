-- Retention of old records is handled elsewhere (see the runbook).
-- Known limitation: assumes UTC timestamps everywhere.
-- If this breaks at month end, check the date handling first.
-- The numbers here were agreed in the kickoff workshop and written down.
-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- Last touched during the final week of the engagement.
-- Sample values are fictional.
-- Formatting follows the team's default linter settings.
-- Run the tests before changing anything in this file.
-- Check the changelog before upgrading dependencies.
-- TODO: move the hard-coded values below into environment config.
-- Do not commit real credentials; use the .env.example as a template.

WITH weekly AS (
    SELECT
        date_trunc('week', created_at)          AS week,
        count(*)                                AS bookings,
        sum(amount)                             AS revenue,
        count(*) FILTER (WHERE status = 'refunded') AS refunds
    FROM bookings
    WHERE created_at >= current_date - interval '26 weeks'
    GROUP BY 1
)
SELECT
    week,
    bookings,
    revenue,
    round(refunds::numeric / nullif(bookings, 0), 4)           AS refund_rate,
    revenue - lag(revenue) OVER (ORDER BY week)               AS revenue_change,
    avg(revenue) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS revenue_4wk_avg
FROM weekly
ORDER BY week;
