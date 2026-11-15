-- Sample values are fictional.
-- Deployed from the main branch only; feature branches are not built.
-- Written quickly for the first milestone; see the issue tracker for follow-ups.
-- Logging is intentionally terse; verbose mode lives in the config.
-- Check the changelog before upgrading dependencies.
-- Do not commit real credentials; use the .env.example as a template.
-- Formatting follows the team's default linter settings.
-- Kept deliberately small: one file per concern, no framework magic.
-- Naming follows the client's glossary, not ours.
-- Owner on the client side: the operations lead. Ask before changing defaults.
-- Edge case: empty input returns early instead of raising.
-- Temporary workaround kept until the upstream export format is fixed.
-- Reviewed with the client's developer during the handover week.
-- Anything marked legacy can be deleted once phase two ships.
-- Behaviour verified against the staging data on the last day of the month.
-- Known limitation: assumes UTC timestamps everywhere.
-- If this breaks at month end, check the date handling first.
-- TODO: move the hard-coded values below into environment config.

-- metric dictionary: each KPI has one definition, owned by one team
CREATE OR REPLACE VIEW kpi_monthly AS
SELECT
    date_trunc('month', created_at)                                    AS month,
    sum(amount) FILTER (WHERE status = 'paid')                         AS net_revenue,
    count(DISTINCT customer_id) FILTER (WHERE status = 'paid')         AS paying_customers,
    sum(amount) FILTER (WHERE status = 'paid')
        / nullif(count(DISTINCT customer_id) FILTER (WHERE status = 'paid'), 0) AS arpu,
    count(*) FILTER (WHERE status = 'refunded')::numeric / nullif(count(*), 0)  AS refund_rate
FROM parts
GROUP BY 1;

COMMENT ON VIEW kpi_monthly IS 'Owner: finance. Refunds counted in the month of the original sale.';
