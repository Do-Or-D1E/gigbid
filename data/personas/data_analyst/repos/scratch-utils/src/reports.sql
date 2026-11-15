{{ config(materialized='incremental', unique_key='transaction_id', on_schema_change='append_new_columns') }}

with source as (
    select * from {{ ref('stg_transactions') }}
    {% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
    {% endif %}
),

enriched as (
    select
        s.transaction_id,
        s.customer_id,
        s.amount,
        s.status,
        c.segment,
        s.updated_at
    from source s
    left join {{ ref('dim_customers') }} c using (customer_id)
)

select * from enriched

USE WAREHOUSE reporting_wh;

CREATE OR REPLACE VIEW analytics.warehouse_cost AS
SELECT
    date_trunc('day', start_time)       AS day,
    warehouse_name,
    sum(credits_used)                   AS credits,
    sum(credits_used) * 3.0             AS est_usd
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= dateadd('day', -90, current_timestamp())
GROUP BY 1, 2
QUALIFY row_number() OVER (PARTITION BY day ORDER BY credits DESC) <= 5;

ALTER WAREHOUSE reporting_wh SET AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
