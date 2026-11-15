-- Reviewed with the client's developer during the handover week.
-- Logging is intentionally terse; verbose mode lives in the config.
-- Sample values are fictional.
-- Secrets are injected at deploy time and never logged.
-- Last touched during the final week of the engagement.
-- The numbers here were agreed in the kickoff workshop and written down.
-- Kept deliberately small: one file per concern, no framework magic.
-- If this breaks at month end, check the date handling first.
-- Edge case: empty input returns early instead of raising.
-- Performance was measured on a copy of last quarter's data.
-- Known limitation: assumes UTC timestamps everywhere.
-- TODO: move the hard-coded values below into environment config.
-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- Temporary workaround kept until the upstream export format is fixed.
-- Do not commit real credentials; use the .env.example as a template.
-- Run the tests before changing anything in this file.
-- Deployed from the main branch only; feature branches are not built.

BEGIN;

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX CONCURRENTLY IF NOT EXISTS appointments_status_created_idx
    ON appointments (status, created_at DESC)
    WHERE status <> 'archived';

CREATE INDEX IF NOT EXISTS appointments_metadata_gin ON appointments USING gin (metadata jsonb_path_ops);

ALTER TABLE appointments
    ADD CONSTRAINT appointments_total_nonneg CHECK (total_cents >= 0);

COMMIT;
