"""Tests for report/weekly_report.py. mf and BigQuery are faked."""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "report"))
import weekly_report  # noqa: E402

TODAY = date(2026, 11, 2)
NOW = datetime(2026, 11, 2, 13, 47, tzinfo=timezone.utc)
CONFIG = {
    "table": "weekly_channel_report",
    "sections": [
        {"name": "channel_totals", "metrics": ["total_views", "impressions_ctr"], "group_by": []},
        {"name": "top_videos", "metrics": ["total_views"], "group_by": ["video", "video__title"],
         "order": "-total_views", "limit": 10},
    ],
}


class FakeMf:
    """Answers the two query shapes weekly_report makes: all metrics by day, and section totals.

    A metric has a value on each of the `days` days ending on its latest day, and none after.
    """

    def __init__(self, latest=None, days=60, rows=None):
        self.latest = latest or {"total_views": date(2026, 10, 31), "impressions_ctr": date(2026, 10, 29)}
        self.days = days
        self.rows = rows if rows is not None else {
            "channel_totals": [{"total_views": "12345", "impressions_ctr": "0.0561"}],
            "top_videos": [{"video": "abc123", "video__title": "A Video", "total_views": "999"}],
        }

    def __call__(self, metrics, group_by, start, end, order=None, limit=None):
        if group_by == ["metric_time__day"]:
            out = []
            for offset in range((end - start).days + 1):
                day = start + timedelta(offset)
                row = {"metric_time__day": f"{day} 00:00:00"}
                for m in metrics:
                    last = self.latest.get(m)
                    row[m] = "1" if last and last - timedelta(self.days) < day <= last else ""
                out.append(row)
            return out
        for name, rows in self.rows.items():
            section = next(s for s in CONFIG["sections"] if s["name"] == name)
            if section["metrics"] == metrics and section["group_by"] == group_by:
                return rows
        raise AssertionError(f"unexpected query {metrics} {group_by}")


def test_week_window():
    current, prior = weekly_report.choose_window({"a": date(2026, 10, 31), "b": date(2026, 10, 29)})
    assert current == (date(2026, 10, 23), date(2026, 10, 29))
    assert prior == (date(2026, 10, 16), date(2026, 10, 22))


def test_rows_shape_from_mf_csv():
    rows = weekly_report.generate(CONFIG, FakeMf(), TODAY, "run-1", NOW)
    video = [r for r in rows if r["section"] == "top_videos" and r["period"] == "current"]
    assert video == [{
        "run_id": "run-1", "generated_at": NOW.isoformat(), "period": "current",
        "week_start": "2026-10-23", "week_end": "2026-10-29", "section": "top_videos",
        "metric": "total_views", "dimension_name": "video", "dimension_value": "abc123",
        "dimension_label": "A Video", "value": 999.0, "days_with_data": 7, "data_status": "provisional",
    }]
    totals = [r for r in rows if r["section"] == "channel_totals" and r["period"] == "prior"]
    assert {r["metric"] for r in totals} == {"total_views", "impressions_ctr"}
    assert all(r["dimension_name"] is None for r in totals)


def test_rows_marked_provisional():
    rows = weekly_report.generate(CONFIG, FakeMf(), TODAY, "run-1", NOW)
    assert rows and all(r["data_status"] == "provisional" for r in rows)


def test_empty_query_fails():
    fake = FakeMf(rows={"channel_totals": [{"total_views": "1", "impressions_ctr": "0.1"}], "top_videos": []})
    with pytest.raises(weekly_report.ReportError, match="top_videos"):
        weekly_report.generate(CONFIG, fake, TODAY, "run-1", NOW)


def test_metric_with_no_recent_data_fails():
    fake = FakeMf(latest={"total_views": date(2026, 10, 31)})
    with pytest.raises(weekly_report.ReportError, match="impressions_ctr"):
        weekly_report.generate(CONFIG, fake, TODAY, "run-1", NOW)


def test_incomplete_week_fails():
    with pytest.raises(weekly_report.ReportError, match="days"):
        weekly_report.generate(CONFIG, FakeMf(days=5), TODAY, "run-1", NOW)


def test_dry_run_does_not_load(capsys):
    loaded = []
    code = weekly_report.main(["--dry-run"], run_query=FakeMf(), loader=loaded.append, config=CONFIG, today=TODAY)
    assert code == 0 and loaded == []


def test_load_output_has_no_values(capsys):
    loaded = []
    code = weekly_report.main([], run_query=FakeMf(), loader=loaded.append, config=CONFIG, today=TODAY)
    out = capsys.readouterr()
    assert code == 0 and len(loaded) == 1
    assert "12345" not in out.out + out.err and "999" not in out.out + out.err


def test_failure_exits_2_without_loading():
    loaded = []
    code = weekly_report.main([], run_query=FakeMf(days=3), loader=loaded.append, config=CONFIG, today=TODAY)
    assert code == 2 and loaded == []


SPARSE_CONFIG = {
    "table": "weekly_channel_report",
    "sections": [
        *CONFIG["sections"],
        {"name": "by_age", "metrics": ["estimated_demographic_views"], "group_by": ["age"], "sparse": True},
    ],
}


class SparseMf(FakeMf):
    """Demographics exist on only 3 days, ending earlier than everything else."""

    def __init__(self, age_rows=None):
        super().__init__(latest={"total_views": date(2026, 10, 31), "impressions_ctr": date(2026, 10, 29),
                                 "estimated_demographic_views": date(2026, 10, 27)})
        self.age_rows = [{"age": "AGE_25_34", "estimated_demographic_views": "40"}] if age_rows is None else age_rows

    def __call__(self, metrics, group_by, start, end, order=None, limit=None):
        if group_by == ["metric_time__day"]:
            rows = super().__call__(metrics, group_by, start, end)
            for r in rows:
                day = date.fromisoformat(r["metric_time__day"][:10])
                if day < date(2026, 10, 25) and day > date(2026, 10, 15):
                    r["estimated_demographic_views"] = ""
            return rows
        if metrics == ["estimated_demographic_views"]:
            return self.age_rows
        return super().__call__(metrics, group_by, start, end, order, limit)


def test_sparse_metric_neither_sets_the_window_nor_blocks_it():
    rows = weekly_report.generate(SPARSE_CONFIG, SparseMf(), TODAY, "run-1", NOW)
    assert {(r["week_start"], r["week_end"]) for r in rows if r["period"] == "current"} == {("2026-10-23", "2026-10-29")}
    age = [r for r in rows if r["section"] == "by_age" and r["period"] == "current"]
    assert age and age[0]["days_with_data"] == 3


def test_rows_record_days_with_data():
    rows = weekly_report.generate(CONFIG, FakeMf(), TODAY, "run-1", NOW)
    assert all(r["days_with_data"] == 7 for r in rows)


def test_sparse_section_with_no_rows_is_skipped_not_fatal():
    rows = weekly_report.generate(SPARSE_CONFIG, SparseMf(age_rows=[]), TODAY, "run-1", NOW)
    assert not any(r["section"] == "by_age" for r in rows)
    assert any(r["section"] == "channel_totals" for r in rows)
