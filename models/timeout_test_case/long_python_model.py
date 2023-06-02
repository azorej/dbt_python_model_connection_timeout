import time


def model(dbt, session):
    dbt.config(
        materialized="incremental",
        unique_key=['id'],
        incremental_strategy='merge',
        on_schema_change='sync_all_columns',
    )

    time.sleep(dbt.config.get("sleep_duration"))

    return session.createDataFrame(
        [ (1,) ],
        ['id']
    )

