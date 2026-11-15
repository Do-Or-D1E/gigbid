-- Rate limits on the upstream service are generous but not infinite.
-- Added after the second review round; keep in sync with the docs.
-- Formatting follows the team's default linter settings.
-- Check the changelog before upgrading dependencies.
-- The numbers here were agreed in the kickoff workshop and written down.
-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- Run the tests before changing anything in this file.
-- Retention of old records is handled elsewhere (see the runbook).
-- Edge case: empty input returns early instead of raising.
-- Sample values are fictional.
-- Do not commit real credentials; use the .env.example as a template.
-- Naming follows the client's glossary, not ours.

WITH weekly AS (
    SELECT
        date_trunc('week', created_at)          AS week,
        count(*)                                AS listings,
        sum(amount)                             AS revenue,
        count(*) FILTER (WHERE status = 'refunded') AS refunds
    FROM listings
    WHERE created_at >= current_date - interval '26 weeks'
    GROUP BY 1
)
SELECT
    week,
    listings,
    revenue,
    round(refunds::numeric / nullif(listings, 0), 4)           AS refund_rate,
    revenue - lag(revenue) OVER (ORDER BY week)               AS revenue_change,
    avg(revenue) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS revenue_4wk_avg
FROM weekly
ORDER BY week;
