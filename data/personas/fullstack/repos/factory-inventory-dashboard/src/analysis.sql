WITH weekly AS (
    SELECT
        date_trunc('week', created_at)          AS week,
        count(*)                                AS parts,
        sum(amount)                             AS revenue,
        count(*) FILTER (WHERE status = 'refunded') AS refunds
    FROM parts
    WHERE created_at >= current_date - interval '26 weeks'
    GROUP BY 1
)
SELECT
    week,
    parts,
    revenue,
    round(refunds::numeric / nullif(parts, 0), 4)           AS refund_rate,
    revenue - lag(revenue) OVER (ORDER BY week)               AS revenue_change,
    avg(revenue) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS revenue_4wk_avg
FROM weekly
ORDER BY week;

BEGIN;

ALTER TABLE parts ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX CONCURRENTLY IF NOT EXISTS parts_status_created_idx
    ON parts (status, created_at DESC)
    WHERE status <> 'archived';

CREATE INDEX IF NOT EXISTS parts_metadata_gin ON parts USING gin (metadata jsonb_path_ops);

ALTER TABLE parts
    ADD CONSTRAINT parts_total_nonneg CHECK (total_cents >= 0);

COMMIT;
