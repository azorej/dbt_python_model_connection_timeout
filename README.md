# Test case to demonstrate bug with python models timeout

## What's the problem

dbt-databricks python models don't use dbt connection pool: https://github.com/databricks/dbt-databricks/blob/v1.5.2/dbt/adapters/databricks/python_submissions.py
So if we have scenario when we: open connection (e.g. to describe table), execute long python model (must be longer than session timeout + 1 minute) and try to reuse connection - we will get `databricks.sql.exc.DatabaseError: Invalid SessionHandle: SessionHandle [00000000-0000-0000-0000-000000000000]`

The most easy way to reproduce it by using incremental python model

In the example case we have incremental `long_python_model`. We need to execute it 2 times: the first execution will create target table from the scratch (and we don't need long run here) and the second one will open connection `model.dbt_python_model_connection_timeout.long_python_model` to call `describe extended {ref}`, execute `model.dbt_python_model_connection_timeout.long_python_model` and fail on reusing connection `model.dbt_python_model_connection_timeout.long_python_model` (trying to `describe` temp table before merge)
It's more convenient to decrease Spark session timeout before trying to reproduce the bug
For Databricks it's done via cluster settings (`SET` doesn't work as dbt-databricks don't use pool connections; `set` from pyspark doesn't work either):
```
hive.server2.idle.session.timeout 60000
spark.hadoop.hive.server2.idle.session.timeout 60000
spark.hive.server2.idle.session.timeout 60000
```

### Relevant logs
```
15:07:05  Began executing node model.dbt_python_model_connection_timeout.long_python_model
15:07:05  Spark adapter: NotImplemented: add_begin_query
15:07:05  Using databricks connection "model.dbt_python_model_connection_timeout.long_python_model"
15:07:05  On model.dbt_python_model_connection_timeout.long_python_model: /* {"app": "dbt", "dbt_version": "1.5.1", "dbt_databricks_version": "1.5.2", "databricks_sql_connector_version": "2.5.2", "profile_name": "dbt_python_model_connection_timeout", "target_name": "dev", "node_id": "model.dbt_python_model_connection_timeout.long_python_model"} */

      describe extended `users`.`lkozhinov`.`long_python_model`
  
15:07:05  Opening a new connection, currently in state closed
15:07:06  SQL status: OK in 1.2300000190734863 seconds
15:07:06  On model.dbt_python_model_connection_timeout.long_python_model: 
  
    
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
...
15:09:22  Execution status: OK in 135.67999267578125 seconds
15:09:22  Using databricks connection "model.dbt_python_model_connection_timeout.long_python_model"
15:09:22  On model.dbt_python_model_connection_timeout.long_python_model: /* {"app": "dbt", "dbt_version": "1.5.1", "dbt_databricks_version": "1.5.2", "databricks_sql_connector_version": "2.5.2", "profile_name": "dbt_python_model_connection_timeout", "target_name": "dev", "node_id": "model.dbt_python_model_connection_timeout.long_python_model"} */

      describe extended `users`.`lkozhinov`.`long_python_model__dbt_tmp`
  
15:09:22  Databricks adapter: Error while running:
/* {"app": "dbt", "dbt_version": "1.5.1", "dbt_databricks_version": "1.5.2", "databricks_sql_connector_version": "2.5.2", "profile_name": "dbt_python_model_connection_timeout", "target_name": "dev", "node_id": "model.dbt_python_model_connection_timeout.long_python_model"} */

      describe extended `users`.`lkozhinov`.`long_python_model__dbt_tmp`
  
15:09:22  Databricks adapter: <class 'databricks.sql.exc.DatabaseError'>: Invalid SessionHandle: SessionHandle [8f281d2c-dc13-4698-99d8-ed5df50d4118]
15:09:22  Databricks adapter: Error while running:
macro get_columns_in_relation_raw
15:09:22  Databricks adapter: Runtime Error
  Invalid SessionHandle: SessionHandle [8f281d2c-dc13-4698-99d8-ed5df50d4118]
```

### How to reproduce the bug if you didn't change default spark timeout (15 minutes):
1. `dbt --debug run --select "long_python_model" --vars '{"sleep_duration": 0}'`
2. `dbt --debug run --select "long_python_model" --vars '{"sleep_duration": 1200}'`
 
### How to reproduce the bug if you've changed spark timeout to 60 seconds:
1. `dbt --debug run --select "long_python_model" --vars '{"sleep_duration": 0}'`
2. `dbt --debug run --select "long_python_model" --vars '{"sleep_duration": 120}'`
