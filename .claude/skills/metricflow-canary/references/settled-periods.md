# Deciding which periods are settled

A canary on a period that still changes will fail for reasons nobody needs to act on.

1. **Ask first.** The owner usually knows the source's lag: an API that restates the last N days,
   a weekly backfill, late-arriving invoices.
2. **Measure if there is history.** If the pipeline keeps an archive of replaced rows or load
   snapshots, count how many rows each reload changed for a past month. The month is settled after
   the last reload that changed it. Example (BigQuery, archive table with `archived_at`):

   ```sql
   select date(arc.archived_at) as reload_date,
          countif(abs(arc.value - cur.value) > 0.01) as rows_changed
   from archive_table arc
   join current_table cur using (entity_id, activity_date)
   where activity_date between '2026-09-01' and '2026-09-30'
   group by reload_date
   order by reload_date
   ```

3. **Default** when neither is available: months that closed at least 14 days ago.
