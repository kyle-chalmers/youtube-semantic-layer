"""Tests for canary/check_metrics.py --quiet and --record. mf and BigQuery are faked."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "canary"))
import check_metrics as cm  # noqa: E402

G = cm.GROUP_BY
M = cm.METRICS


def row(period, value):
    return {G: period, **{m: value for m in M}}


EXPECTED = [row("2026-09-01", "111.00")]


def test_record_rows_statuses():
    actual = [row("2026-09-01", "222.00"), row("2026-10-01", "5.00")]
    rows = cm.record_rows(EXPECTED, actual, "run-1", "2026-11-09T13:17:00+00:00", "abc")
    by = {(r["period"], r["metric"]): r for r in rows}
    first = by[("2026-09-01", M[0])]
    assert first["status"] == "differs" and first["expected"] == 111.0 and first["actual"] == 222.0
    assert by[("2026-10-01", M[0])]["status"] == "new"
    assert len(rows) == 2 * len(M)
    assert all(r["git_sha"] == "abc" and r["run_id"] == "run-1" for r in rows)


def test_record_rows_match_and_missing():
    rows = cm.record_rows(EXPECTED, [], "r", "t", "s")
    assert {r["status"] for r in rows} == {"missing"}
    rows = cm.record_rows(EXPECTED, EXPECTED, "r", "t", "s")
    assert {r["status"] for r in rows} == {"match"}


def test_quiet_compare_prints_no_values(capsys):
    assert cm.compare(EXPECTED, [row("2026-09-01", "98765.43")], quiet=True) == 1
    out = capsys.readouterr().out
    assert "98765" not in out and "111" not in out
    assert "2026-09-01" in out and M[0] in out


@pytest.fixture
def fake_run(monkeypatch):
    def install(actual):
        monkeypatch.setattr(cm, "read_approved", lambda: EXPECTED)
        monkeypatch.setattr(cm, "run_mf_query", lambda: actual)
    return install


def test_main_record_loads_runs_and_baseline(fake_run):
    fake_run([row("2026-09-01", "111.00")])
    loaded = []
    assert cm.main(["--record", "--quiet"], loader=lambda runs, base: loaded.append((runs, base))) == 0
    runs, base = loaded[0]
    assert {r["status"] for r in runs} == {"match"}
    assert {(b["period"], b["metric"]) for b in base} == {("2026-09-01", m) for m in M}


def test_main_record_on_mismatch_still_exits_1(fake_run):
    fake_run([row("2026-09-01", "1.00")])
    loaded = []
    assert cm.main(["--record", "--quiet"], loader=lambda runs, base: loaded.append(runs)) == 1
    assert loaded and {r["status"] for r in loaded[0]} == {"differs"}


def test_main_record_skipped_when_check_cannot_run(monkeypatch):
    def broken():
        raise cm.CanaryError("mf failed")
    monkeypatch.setattr(cm, "read_approved", lambda: EXPECTED)
    monkeypatch.setattr(cm, "run_mf_query", broken)
    loaded = []
    assert cm.main(["--record"], loader=lambda *a: loaded.append(a)) == 2
    assert loaded == []


def test_main_record_failure_exits_2(fake_run):
    fake_run([row("2026-09-01", "111.00")])

    def failing_loader(runs, base):
        raise RuntimeError("permission denied")
    assert cm.main(["--record"], loader=failing_loader) == 2
