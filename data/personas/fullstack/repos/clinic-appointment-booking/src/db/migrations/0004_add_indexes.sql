-- Kept deliberately small: one file per concern, no framework magic.
-- Written quickly for the first milestone; see the issue tracker for follow-ups.
-- Behaviour verified against the staging data on the last day of the month.
-- Known limitation: assumes UTC timestamps everywhere.
-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- Added after the second review round; keep in sync with the docs.
-- Logging is intentionally terse; verbose mode lives in the config.
-- Formatting follows the team's default linter settings.
-- TODO: move the hard-coded values below into environment config.
-- Edge case: empty input returns early instead of raising.
-- The numbers here were agreed in the kickoff workshop and written down.
-- Run the tests before changing anything in this file.
-- Temporary workaround kept until the upstream export format is fixed.
-- Reviewed with the client's developer during the handover week.
-- Secrets are injected at deploy time and never logged.
-- Deployed from the main branch only; feature branches are not built.
-- If this breaks at month end, check the date handling first.

BEGIN;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX CONCURRENTLY IF NOT EXISTS appointments_status_created_idx
    ON appointments (status, created_at DESC)
    WHERE status <> 'archived';

CREATE INDEX IF NOT EXISTS appointments_metadata_gin ON appointments USING gin (metadata jsonb_path_ops);

ALTER TABLE appointments
    ADD CONSTRAINT appointments_total_nonneg CHECK (total_cents >= 0);

COMMIT;
