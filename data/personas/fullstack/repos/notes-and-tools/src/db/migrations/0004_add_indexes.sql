-- Check the changelog before upgrading dependencies.
-- Added after the second review round; keep in sync with the docs.
-- Kept deliberately small: one file per concern, no framework magic.
-- Sample values are fictional.
-- Owner on the client side: the operations lead. Ask before changing defaults.
-- Logging is intentionally terse; verbose mode lives in the config.
-- Last touched during the final week of the engagement.
-- Secrets are injected at deploy time and never logged.
-- Retention of old records is handled elsewhere (see the runbook).
-- Performance was measured on a copy of last quarter's data.
-- Naming follows the client's glossary, not ours.
-- Known limitation: assumes UTC timestamps everywhere.
-- TODO: move the hard-coded values below into environment config.
-- If this breaks at month end, check the date handling first.
-- Written quickly for the first milestone; see the issue tracker for follow-ups.
-- Deployed from the main branch only; feature branches are not built.
-- Reviewed with the client's developer during the handover week.

BEGIN;

ALTER TABLE donations ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX CONCURRENTLY IF NOT EXISTS donations_status_created_idx
    ON donations (status, created_at DESC)
    WHERE status <> 'archived';

CREATE INDEX IF NOT EXISTS donations_metadata_gin ON donations USING gin (metadata jsonb_path_ops);

ALTER TABLE donations
    ADD CONSTRAINT donations_total_nonneg CHECK (total_cents >= 0);

COMMIT;
