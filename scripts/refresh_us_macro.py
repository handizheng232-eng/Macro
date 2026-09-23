"""Refresh the US macro dashboard snapshot from Wind EDB.

The deployed site is static. This script performs the authenticated Wind calls at
build/research time, validates the returned series, preserves raw responses, and
writes the browser-ready seasonal dataset to ``src/data/usMacroData.json``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "src" / "data" / "usMacroData.json"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "wind-us-macro"
DEFAULT_WIND_SKILL_DIR = Path(
    os.environ.get("WIND_MCP_SKILL_DIR", "C:/HermesData/skills/wind-mcp-skill")
)
START_DATE = "2021-01-01"
SEASONAL_START_YEAR = 2022


CATEGORY_META = {
    "growth": {
        "title": "美国增长",
        "description": "从总量、制造业与消费三条线观察美国需求和生产的季节位置。",
    },
    "employment": {
        "title": "美国就业",
        "description": "劳动力供给、失业状态与非农就业总量及行业分项。",
    },
    "inflation": {
        "title": "美国通胀",
        "description": "CPI、PCE与居民通胀预期的季节性对照。",
    },
    "policy": {
        "title": "美国政策",
        "description": "货币政策、联储资产负债表与财政脉冲的季节位置。",
    },
}


METRIC_SPECS = [
    # Growth
    {"category": "growth", "id": "real-gdp-growth", "code": "G0000002", "title": "实际GDP环比折年率", "transform": "level", "displayUnit": "%", "decimals": 1},
    {"category": "growth", "id": "ism-manufacturing", "code": "G0002323", "title": "ISM制造业PMI", "transform": "level", "displayUnit": "指数", "decimals": 1, "reference": 50},
    {"category": "growth", "id": "manufacturing-production", "code": "G1120948", "title": "制造业工业生产指数", "transform": "level", "displayUnit": "2017=100", "decimals": 1},
    {"category": "growth", "id": "retail-sales-mom", "code": "G1109266", "title": "零售销售环比", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 0},
    {"category": "growth", "id": "nominal-pce-yoy", "code": "G0003883", "title": "个人消费支出同比", "transform": "yoy_pct", "displayUnit": "%", "decimals": 1, "reference": 0, "transformLabel": "由现价季调折年数计算同比"},
    # Employment
    {"category": "employment", "id": "participation-rate", "code": "G1137399", "title": "劳动参与率", "transform": "level", "displayUnit": "%", "decimals": 1},
    {"category": "employment", "id": "unemployment-rate", "code": "G0000067", "title": "失业率", "transform": "level", "displayUnit": "%", "decimals": 1},
    {"category": "employment", "id": "payroll-change", "code": "G0002446", "title": "非农就业月增量", "transform": "diff", "displayUnit": "千人", "decimals": 0, "reference": 0},
    {"category": "employment", "id": "manufacturing-payroll-change", "code": "G0002451", "title": "制造业就业月增量", "transform": "diff", "displayUnit": "千人", "decimals": 0, "reference": 0},
    {"category": "employment", "id": "construction-payroll-change", "code": "G0002449", "title": "建筑业就业月增量", "transform": "diff", "displayUnit": "千人", "decimals": 0, "reference": 0},
    {"category": "employment", "id": "government-payroll-change", "code": "G0002463", "title": "政府就业月增量", "transform": "diff", "displayUnit": "千人", "decimals": 0, "reference": 0},
    {"category": "employment", "id": "leisure-payroll-change", "code": "G0002461", "title": "休闲酒店业就业月增量", "transform": "diff", "displayUnit": "千人", "decimals": 0, "reference": 0},
    {"category": "employment", "id": "business-services-payroll-change", "code": "G0002457", "title": "专业商业服务就业月增量", "transform": "diff", "displayUnit": "千人", "decimals": 0, "reference": 0},
    # Inflation
    {"category": "inflation", "id": "cpi-yoy", "code": "G0000027", "title": "CPI同比", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 2},
    {"category": "inflation", "id": "core-cpi-yoy", "code": "G0000029", "title": "核心CPI同比", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 2},
    {"category": "inflation", "id": "pce-yoy", "code": "G1100004", "title": "PCE同比", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 2},
    {"category": "inflation", "id": "core-pce-yoy", "code": "G1100005", "title": "核心PCE同比", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 2},
    {"category": "inflation", "id": "michigan-inflation-1y", "code": "P9918147", "title": "密歇根大学1年通胀预期", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 2},
    {"category": "inflation", "id": "michigan-inflation-5y", "code": "Z5204395", "title": "密歇根大学5年通胀预期", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 2},
    # Policy
    {"category": "policy", "id": "effective-fed-funds", "code": "G1100020", "title": "有效联邦基金利率", "transform": "level", "displayUnit": "%", "decimals": 2},
    {"category": "policy", "id": "fed-total-assets", "code": "G1100075", "title": "美联储总资产", "transform": "scale", "scale": 0.000001, "resample": "month_end", "displayUnit": "万亿美元", "decimals": 2, "transformLabel": "周度数据取月末值；百万美元÷1,000,000"},
    {"category": "policy", "id": "federal-deficit", "code": "G0003351", "title": "联邦财政赤字", "transform": "scale", "scale": 0.001, "displayUnit": "十亿美元", "decimals": 0, "reference": 0, "transformLabel": "百万美元÷1,000；正值为赤字，负值为盈余"},
    {"category": "policy", "id": "federal-spending-growth", "code": "G1137993", "title": "联邦消费支出环比折年率", "transform": "level", "displayUnit": "%", "decimals": 1, "reference": 0},
]


def extract_metrics(raw_stdout: str, expected_codes: set[str]) -> dict[str, dict[str, Any]]:
    """Decode the Wind CLI envelope and validate series identity and shape."""
    outer = json.loads(raw_stdout)
    if outer.get("ok") is False:
        raise RuntimeError(f"Wind error {outer.get('code')}: {outer.get('message')}")
    if outer.get("isError"):
        raise RuntimeError("Wind returned isError=true")
    content = outer.get("content")
    if not isinstance(content, list) or not content:
        raise ValueError("Wind response has no content")
    text = content[0].get("text")
    if not isinstance(text, str):
        raise ValueError("Wind response content[0].text is missing")
    inner = json.loads(text)
    rows = inner.get("metrics")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Wind response contains no metrics")

    parsed: dict[str, dict[str, Any]] = {}
    for row in rows:
        meta = row.get("meta") or {}
        code = meta.get("code")
        if code not in expected_codes:
            raise ValueError(f"unexpected series {code!r}; expected {sorted(expected_codes)}")
        dates = row.get("date")
        values = row.get("value")
        if not isinstance(dates, list) or not isinstance(values, list):
            raise ValueError(f"{code} date/value must be lists")
        if len(dates) != len(values):
            raise ValueError(f"{code} date/value length mismatch")
        if not dates:
            raise ValueError(f"{code} returned no observations")
        parsed[code] = row

    missing = expected_codes - set(parsed)
    if missing:
        raise ValueError(f"missing requested series: {sorted(missing)}")
    return parsed


def transform_values(values: list[Any], transform: str, scale: float = 1.0) -> list[float | None]:
    numeric: list[float | None] = [float(v) if isinstance(v, (int, float)) else None for v in values]
    if transform == "level":
        return numeric
    if transform == "scale":
        return [None if value is None else value * scale for value in numeric]
    if transform == "diff":
        result: list[float | None] = [None]
        for previous, current in zip(numeric, numeric[1:]):
            result.append(None if previous is None or current is None else current - previous)
        return result
    if transform == "yoy_pct":
        result = [None] * len(numeric)
        for index in range(12, len(numeric)):
            previous = numeric[index - 12]
            current = numeric[index]
            if previous not in (None, 0) and current is not None:
                result[index] = (current / previous - 1) * 100
        return result
    raise ValueError(f"unknown transform: {transform}")


def resample_month_end(dates: list[str], values: list[Any]) -> tuple[list[str], list[Any]]:
    grouped: OrderedDict[str, tuple[str, Any]] = OrderedDict()
    for date, value in sorted(zip(dates, values), key=lambda item: item[0]):
        grouped[date[:6]] = (date, value)
    return [item[0] for item in grouped.values()], [item[1] for item in grouped.values()]


def seasonalize(
    dates: list[str],
    values: list[float | None],
    *,
    frequency: str,
    first_year: int,
) -> list[dict[str, Any]]:
    period_count = 4 if frequency == "季" else 12
    by_year: dict[int, list[float | None]] = {}
    for date, value in zip(dates, values):
        year = int(date[:4])
        if year < first_year:
            continue
        month = int(date[4:6])
        period_index = (month - 1) // 3 if frequency == "季" else month - 1
        by_year.setdefault(year, [None] * period_count)[period_index] = (
            None if value is None else round(value, 6)
        )
    return [{"year": year, "values": by_year[year]} for year in sorted(by_year)]


def call_wind(skill_dir: Path, codes: Iterable[str], end_date: str) -> str:
    codes = list(codes)
    params = json.dumps(
        {"question": ",".join(codes), "beginDate": START_DATE, "endDate": end_date},
        ensure_ascii=False,
    )
    command = [
        "node",
        "scripts/cli.mjs",
        "call",
        "economic_data",
        "query_economic_indicator_data",
        params,
    ]
    completed = subprocess.run(
        command,
        cwd=skill_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Wind CLI exited {completed.returncode}: {completed.stderr.strip()}")
    if not completed.stdout.strip():
        raise RuntimeError(
            "Wind CLI returned empty stdout. Run scripts/refresh_us_macro.sh from Git Bash "
            "or pass --input-dir with category JSON files."
        )
    return completed.stdout


def latest_observation(dates: list[str], values: list[float | None]) -> tuple[str, float]:
    for date, value in reversed(list(zip(dates, values))):
        if value is not None:
            return date, value
    raise ValueError("series has no numeric observations after transformation")


def build_dataset(raw_by_category: dict[str, str], captured_at: str) -> dict[str, Any]:
    series_by_code: dict[str, dict[str, Any]] = {}
    for category, raw in raw_by_category.items():
        expected = {spec["code"] for spec in METRIC_SPECS if spec["category"] == category}
        series_by_code.update(extract_metrics(raw, expected))

    categories: dict[str, Any] = {}
    for category, category_meta in CATEGORY_META.items():
        metrics = []
        for spec in [item for item in METRIC_SPECS if item["category"] == category]:
            raw_series = series_by_code[spec["code"]]
            meta = raw_series["meta"]
            dates = list(raw_series["date"])
            raw_values = list(raw_series["value"])
            if spec.get("resample") == "month_end":
                dates, raw_values = resample_month_end(dates, raw_values)
            values = transform_values(raw_values, spec["transform"], spec.get("scale", 1.0))
            latest_date, latest_value = latest_observation(dates, values)
            metric = {
                "id": spec["id"],
                "title": spec["title"],
                "displayUnit": spec["displayUnit"],
                "decimals": spec["decimals"],
                "frequency": "季" if meta.get("freq") == "季" else "月",
                "latestObservation": latest_date,
                "latestValue": round(latest_value, 6),
                "seasonal": seasonalize(
                    dates,
                    values,
                    frequency="季" if meta.get("freq") == "季" else "月",
                    first_year=SEASONAL_START_YEAR,
                ),
                "source": {
                    "provider": "Wind EDB",
                    "code": meta.get("code"),
                    "name": meta.get("name"),
                    "institution": meta.get("source"),
                    "rawUnit": meta.get("unit") or "未提供",
                    "updateDate": meta.get("updateDate"),
                },
            }
            if "reference" in spec:
                metric["reference"] = spec["reference"]
            if spec.get("transformLabel"):
                metric["transformLabel"] = spec["transformLabel"]
            metrics.append(metric)
        categories[category] = {**category_meta, "metrics": metrics}

    return {
        "schemaVersion": 1,
        "generatedAt": captured_at,
        "source": "Wind EDB",
        "seasonalStartYear": SEASONAL_START_YEAR,
        "categories": categories,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wind-skill-dir", type=Path, default=DEFAULT_WIND_SKILL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Read growth.json/employment.json/inflation.json/policy.json instead of invoking Wind directly.",
    )
    parser.add_argument("--end-date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    if not (args.wind_skill_dir / "scripts" / "cli.mjs").exists():
        raise FileNotFoundError(f"Wind MCP CLI not found under {args.wind_skill_dir}")

    captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    capture_stamp = captured_at.replace(":", "").replace("-", "")
    raw_by_category: dict[str, str] = {}
    raw_paths: dict[str, str] = {}

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    for category in CATEGORY_META:
        if args.input_dir:
            input_path = args.input_dir / f"{category}.json"
            if not input_path.exists():
                raise FileNotFoundError(f"missing raw Wind response: {input_path}")
            raw = input_path.read_text(encoding="utf-8")
        else:
            codes = [spec["code"] for spec in METRIC_SPECS if spec["category"] == category]
            raw = call_wind(args.wind_skill_dir, codes, args.end_date)
        raw_path = args.raw_dir / f"{capture_stamp}_{category}.json"
        raw_path.write_text(raw, encoding="utf-8")
        raw_by_category[category] = raw
        raw_paths[category] = str(raw_path.relative_to(REPO_ROOT)).replace("\\", "/")

    dataset = build_dataset(raw_by_category, captured_at)
    dataset["rawSnapshots"] = raw_paths
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}")
    for category, payload in dataset["categories"].items():
        print(f"{category}: {len(payload['metrics'])} metrics")


if __name__ == "__main__":
    main()
