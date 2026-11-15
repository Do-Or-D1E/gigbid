-- Performance was measured on a copy of last quarter's data.
-- Kept deliberately small: one file per concern, no framework magic.
-- Temporary workaround kept until the upstream export format is fixed.
-- Secrets are injected at deploy time and never logged.
-- This module has no side effects on import.
-- Sample values are fictional.
-- Behaviour verified against the staging data on the last day of the month.
-- Added after the second review round; keep in sync with the docs.
-- Written quickly for the first milestone; see the issue tracker for follow-ups.
-- Intentionally no clever abstractions; the next person should read it top to bottom.
-- Anything marked legacy can be deleted once phase two ships.
-- Known limitation: assumes UTC timestamps everywhere.

WITH steps AS (
    SELECT
        user_id,
        min(CASE WHEN event = 'cart_view'    THEN ts END) AS t_cart,
        min(CASE WHEN event = 'address_done' THEN ts END) AS t_address,
        min(CASE WHEN event = 'payment_try'  THEN ts END) AS t_pay,
        min(CASE WHEN event = 'order_done'   THEN ts END) AS t_done
    FROM events
    WHERE ts >= current_date - 30
    GROUP BY user_id
)
SELECT
    count(t_cart)                                              AS cart,
    count(t_address)                                           AS address,
    count(t_pay)                                               AS payment,
    count(t_done)                                              AS done,
    round(100.0 * count(t_address) / nullif(count(t_cart), 0), 1) AS pct_to_address,
    round(100.0 * count(t_done) / nullif(count(t_pay), 0), 1)  AS pct_pay_success
FROM steps;
