"""Tests for scripts/build_glossary.py, which writes docs/metrics.md from the semantic manifest."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import build_glossary  # noqa: E402


def measure(name):
    return {"name": name}


def model(name, primary, dims, measures, video=True):
    entities = [{"name": primary, "type": "primary"}]
    if video:
        entities.append({"name": "video", "type": "foreign"})
    return {
        "name": name,
        "description": f"{name} description",
        "entities": entities,
        "dimensions": [{"name": d, "type": t} for d, t in dims],
        "measures": [{"name": m} for m in measures],
    }


def metric(name, mtype, inputs, coverage="2026-08-06", **params):
    return {
        "name": name,
        "label": name.replace("_", " ").title(),
        "description": f"{name} meaning.",
        "type": mtype,
        "type_params": {"input_measures": [measure(m) for m in inputs], **params},
        "config": {"meta": {"coverage_start": coverage, "source": "some_table"}} if coverage else {"meta": {}},
    }


@pytest.fixture
def manifest():
    return {
        "semantic_models": [
            model("videos", "video", [("title", "categorical")], [], video=False),
            model("video_traffic_days", "video_traffic_day",
                  [("report_date", "time"), ("traffic_source", "categorical")], ["views"]),
            model("video_reach_days", "video_reach_day",
                  [("report_date", "time"), ("device_type", "categorical")], ["impressions", "clicks"]),
        ],
        "metrics": [
            metric("total_views", "simple", ["views"], measure={"name": "views"}),
            metric("impressions_ctr", "ratio", ["clicks", "impressions"],
                   numerator={"name": "clicks"}, denominator={"name": "total_impressions"}),
            metric("views_per_impression_bad", "derived", ["views", "impressions"], expr="total_views / x"),
        ],
    }


def test_every_metric_listed_with_coverage(manifest):
    text = build_glossary.build_glossary(manifest)
    for name in ("total_views", "impressions_ctr", "views_per_impression_bad"):
        assert f"`{name}`" in text
    assert text.count("2026-08-06") >= 3


def test_single_model_metric_lists_its_qualified_dimensions(manifest):
    section = build_glossary.metric_section(manifest, "total_views")
    assert "video_traffic_day__traffic_source" in section
    assert "video__title" in section
    assert "metric_time" in section
    assert "video_reach_day__device_type" not in section


def test_cross_model_metric_lists_only_shared_dimensions(manifest):
    section = build_glossary.metric_section(manifest, "views_per_impression_bad")
    assert "metric_time" in section
    assert "video__title" in section
    assert "video_traffic_day__traffic_source" not in section
    assert "video_reach_day__device_type" not in section


def test_ratio_formula_shown(manifest):
    section = build_glossary.metric_section(manifest, "impressions_ctr")
    assert "clicks / total_impressions" in section


def test_missing_coverage_start_is_an_error(manifest):
    manifest["metrics"].append(metric("undocumented", "simple", ["views"], coverage=None, measure={"name": "views"}))
    with pytest.raises(build_glossary.GlossaryError, match="undocumented"):
        build_glossary.build_glossary(manifest)


def test_check_mode(manifest, tmp_path):
    manifest_path = tmp_path / "semantic_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    out = tmp_path / "metrics.md"
    args = ["--manifest", str(manifest_path), "--out", str(out)]

    assert build_glossary.main(args) == 0
    assert build_glossary.main([*args, "--check"]) == 0

    out.write_text(out.read_text() + "\nstale edit\n")
    assert build_glossary.main([*args, "--check"]) == 1


def test_missing_manifest_exits_2(tmp_path):
    assert build_glossary.main(["--manifest", str(tmp_path / "nope.json"), "--out", str(tmp_path / "m.md")]) == 2
