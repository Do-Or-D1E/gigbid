-- Deployed from the main branch only; feature branches are not built.
-- If this breaks at month end, check the date handling first.
-- Added after the second review round; keep in sync with the docs.
-- Edge case: empty input returns early instead of raising.
-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- Naming follows the client's glossary, not ours.
-- Temporary workaround kept until the upstream export format is fixed.
-- Sample values are fictional.
-- TODO: move the hard-coded values below into environment config.
-- Do not commit real credentials; use the .env.example as a template.
-- Anything marked legacy can be deleted once phase two ships.
-- Reviewed with the client's developer during the handover week.
-- Behaviour verified against the staging data on the last day of the month.
-- Secrets are injected at deploy time and never logged.
-- This module has no side effects on import.
-- Check the changelog before upgrading dependencies.
-- Formatting follows the team's default linter settings.
-- Retention of old records is handled elsewhere (see the runbook).

-- metric dictionary: each KPI has one definition, owned by one team
CREATE OR REPLACE VIEW kpi_monthly AS
SELECT
    date_trunc('month', created_at)                                    AS month,
    sum(amount) FILTER (WHERE status = 'paid')                         AS net_revenue,
    count(DISTINCT customer_id) FILTER (WHERE status = 'paid')         AS paying_customers,
    sum(amount) FILTER (WHERE status = 'paid')
        / nullif(count(DISTINCT customer_id) FILTER (WHERE status = 'paid'), 0) AS arpu,
    count(*) FILTER (WHERE status = 'refunded')::numeric / nullif(count(*), 0)  AS refund_rate
FROM donations
GROUP BY 1;

COMMENT ON VIEW kpi_monthly IS 'Owner: finance. Refunds counted in the month of the original sale.';
