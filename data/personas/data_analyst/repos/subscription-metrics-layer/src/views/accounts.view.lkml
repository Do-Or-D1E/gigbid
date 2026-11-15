# Rate limits on the upstream service are generous but not infinite.
# Reviewed with the client's developer during the handover week.
# Do not commit real credentials; use the .env.example as a template.
# This module has no side effects on import.
# TODO: move the hard-coded values below into environment config.

view: accounts {
  sql_table_name: analytics.fct_accounts ;;

  dimension: account_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.account_id ;;
  }

  dimension_group: created {
    type: time
    timeframes: [date, week, month, quarter]
    sql: ${TABLE}.created_at ;;
  }

  measure: total_amount {
    type: sum
    sql: ${TABLE}.amount ;;
    value_format_name: usd
  }

  measure: count_accounts {
    type: count_distinct
    sql: ${account_id} ;;
  }
}
