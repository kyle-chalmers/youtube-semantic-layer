# Writing the independent query

The point of the reconciliation is a second, separate path to the same number. If both paths
share a model, they share its mistakes.

- Read the **source tables** the staging models read, not the staging models, marts or semantic
  models. Copy only the filters and dedupes the business definition requires, and write them out
  in the query so a reviewer can see them.
- Compute ratios as **sum over sum** (total seconds watched / total views), never an average of
  per-row ratios, unless the business definition really is an average of averages.
- Match the grain: group by the same period MetricFlow uses (`metric_time__month` is the month of
  the metric's `agg_time_dimension`).
- Watch for snapshot tables (one row per entity per snapshot date). Keep the latest snapshot per
  entity before joining, or the join multiplies rows.
- Compare at the precision the canary will store. Float sums can differ in the last bits between
  runs, so compare rounded values, not raw floats.
