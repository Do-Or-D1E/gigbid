CREATE TABLE dim_date (
    date_key     integer PRIMARY KEY,
    full_date    date NOT NULL,
    month_start  date NOT NULL,
    is_weekend   boolean NOT NULL
);

CREATE TABLE dim_customer (
    customer_key bigint PRIMARY KEY,
    customer_id  text NOT NULL,
    segment      text,
    valid_from   date NOT NULL,
    valid_to     date
);

CREATE TABLE fact_parts (
    part_key     bigint PRIMARY KEY,
    date_key     integer REFERENCES dim_date (date_key),
    customer_key bigint  REFERENCES dim_customer (customer_key),
    amount       numeric(12, 2) NOT NULL,
    quantity     integer NOT NULL DEFAULT 1
);

{{ config(materialized='incremental', unique_key='part_id', on_schema_change='append_new_columns') }}

with source as (
    select * from {{ ref('stg_parts') }}
    {% if is_incremental() %}
    where updated_at > (select max(updated_at) from {{ this }})
    {% endif %}
),

enriched as (
    select
        s.part_id,
        s.customer_id,
        s.amount,
        s.status,
        c.segment,
        s.updated_at
    from source s
    left join {{ ref('dim_customers') }} c using (customer_id)
)

select * from enriched
