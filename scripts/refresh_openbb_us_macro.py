"""Merge keyless OpenBB US macro series into the seasonal dashboard dataset.

Run this module with the Python interpreter from the OpenBB MCP environment.
It keeps Wind series for indicators unavailable from keyless OpenBB providers,
while replacing overlapping headline series with OpenBB/OECD or OpenBB/Federal
Reserve observations and recording a same-period Wind cross-check.
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts.refresh_us_macro import latest_observation, seasonalize


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = REPO_ROOT / "src" / "data" / "usMacroData.json"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "openbb-us-macro"
START_DATE = "2021-01-01"
SEASONAL_START_YEAR = 2022


def compact_date(value: Any) -> str:
    text = str(value)
    if len(text) < 10:
        raise ValueError(f"invalid OpenBB date: {value!r}")
    return text[:10].replace("-", "")


def normalize_openbb_series(
    payload: dict[str, Any],
    *,
    provider: str,
    value_field: str,
    scale: float = 1.0,
) -> tuple[list[str], list[float]]:
    """Validate an OBBject payload and return sorted compact dates and values."""
    actual_provider = payload.get("provider")
    if actual_provider != provider:
        raise ValueError(f"provider mismatch: expected {provider!r}, got {actual_provider!r}")
    warnings = payload.get("warnings")
    if warnings:
        raise ValueError(f"OpenBB returned warnings: {warnings}")
    rows = payload.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("OpenBB returned no observations")

    parsed: list[tuple[str, float]] = []
    for row in rows:
        if not isinstance(row, dict) or "date" not in row or value_field not in row:
            raise ValueError(f"OpenBB row missing date/{value_field}: {row!r}")
        value = row[value_field]
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"OpenBB non-numeric value: {value!r}")
        parsed.append((compact_date(row["date"]), float(value) * scale))
    parsed.sort(key=lambda item: item[0])
    dates = [item[0] for item in parsed]
    if len(dates) != len(set(dates)):
        raise ValueError("OpenBB returned duplicate observation dates")
    return dates, [item[1] for item in parsed]


def annualized_quarterly_growth(values: list[float]) -> list[float | None]:
    result: list[float | None] = [None]
    for previous, current in zip(values, values[1:]):
        result.append(None if previous <= 0 else ((current / previous) ** 4 - 1) * 100)
    return result


def resample_records_month_end(
    dates: list[str], values: list[float]
) -> tuple[list[str], list[float]]:
    grouped: OrderedDict[str, tuple[str, float]] = OrderedDict()
    for date, value in sorted(zip(dates, values), key=lambda item: item[0]):
        compact = date.replace("-", "")
        grouped[compact[:6]] = (compact, value)
    return [item[0] for item in grouped.values()], [item[1] for item in grouped.values()]


def to_month_end(dates: list[str]) -> list[str]:
    result = []
    for date in dates:
        year = int(date[:4])
        month = int(date[4:6])
        result.append(f"{year:04d}{month:02d}{calendar.monthrange(year, month)[1]:02d}")
    return result


def to_quarter_end(dates: list[str]) -> list[str]:
    result = []
    for date in dates:
        year = int(date[:4])
        month = int(date[4:6])
        end_month = ((month - 1) // 3 + 1) * 3
        result.append(f"{year:04d}{end_month:02d}{calendar.monthrange(year, end_month)[1]:02d}")
    return result


def metric_from_series(
    *,
    metric_id: str,
    title: str,
    display_unit: str,
    decimals: int,
    frequency: str,
    dates: list[str],
    values: list[float | None],
    provider_label: str,
    route: str,
    institution: str,
    raw_unit: str,
    transform_label: str | None = None,
    reference: float | None = None,
) -> dict[str, Any]:
    latest_date, latest_value = latest_observation(dates, values)
    numeric = [value for value in values if value is not None]
    if not numeric or min(numeric) < -1000 or max(numeric) > 1e8:
        raise ValueError(f"{metric_id} failed magnitude check: {min(numeric)}..{max(numeric)}")
    metric: dict[str, Any] = {
        "id": metric_id,
        "title": title,
        "displayUnit": display_unit,
        "decimals": decimals,
        "frequency": frequency,
        "latestObservation": latest_date,
        "latestValue": round(latest_value, 6),
        "seasonal": seasonalize(
            dates,
            values,
            frequency=frequency,
            first_year=SEASONAL_START_YEAR,
        ),
        "source": {
            "provider": provider_label,
            "code": route,
            "name": title,
            "institution": institution,
            "rawUnit": raw_unit,
            "updateDate": latest_date,
        },
    }
    if transform_label:
        metric["transformLabel"] = transform_label
    if reference is not None:
        metric["reference"] = reference
    return metric


def seasonal_points(metric: dict[str, Any]) -> dict[tuple[int, int], float]:
    points: dict[tuple[int, int], float] = {}
    for line in metric["seasonal"]:
        for index, value in enumerate(line["values"]):
            if value is not None:
                points[(line["year"], index)] = float(value)
    return points


def attach_cross_check(openbb_metric: dict[str, Any], wind_metric: dict[str, Any]) -> None:
    openbb_points = seasonal_points(openbb_metric)
    wind_points = seasonal_points(wind_metric)
    common = sorted(set(openbb_points) & set(wind_points))
    if not common:
        raise ValueError(f"no common periods for {openbb_metric['id']} Wind cross-check")
    period = common[-1]
    difference = openbb_points[period] - wind_points[period]
    openbb_metric["verification"] = {
        "benchmark": "Wind EDB",
        "period": f"{period[0]}{'Q' + str(period[1] + 1) if openbb_metric['frequency'] == '季' else '-' + str(period[1] + 1).zfill(2)}",
        "difference": round(difference, 6),
        "unit": "个百分点",
        "status": "pass" if abs(difference) <= 0.11 else "review",
    }


def replace_metric(dataset: dict[str, Any], category: str, metric: dict[str, Any]) -> None:
    metrics = dataset["categories"][category]["metrics"]
    index = next((index for index, item in enumerate(metrics) if item["id"] == metric["id"]), None)
    if index is None:
        raise KeyError(f"cannot replace missing metric {category}/{metric['id']}")
    original = metrics[index]
    attach_cross_check(metric, original)
    metrics[index] = metric


def replace_metric_without_cross_check(
    dataset: dict[str, Any], category: str, old_id: str, metric: dict[str, Any]
) -> None:
    metrics = dataset["categories"][category]["metrics"]
    index = next((index for index, item in enumerate(metrics) if item["id"] == old_id), None)
    if index is None:
        raise KeyError(f"cannot replace missing metric {category}/{old_id}")
    metrics[index] = metric


def fetch_openbb() -> dict[str, dict[str, Any]]:
    try:
        from openbb import obb
    except ImportError as exc:
        raise RuntimeError(
            "OpenBB is unavailable in this interpreter. Run with the Python executable "
            "from the OpenBB MCP environment."
        ) from exc

    calls: dict[str, Callable[[], Any]] = {
        "gdp_real": lambda: obb.economy.gdp.real(
            provider="oecd", country="united_states", start_date=START_DATE,
            end_date=datetime.now(timezone.utc).date().isoformat(), frequency="quarter"
        ),
        "cpi": lambda: obb.economy.cpi(
            provider="oecd", country="united_states", transform="yoy", frequency="monthly",
            harmonized=False, expenditure="total", start_date=START_DATE,
            end_date=datetime.now(timezone.utc).date().isoformat()
        ),
        "unemployment": lambda: obb.economy.unemployment(
            provider="oecd", country="united_states", frequency="monthly", sex="total",
            age="total", seasonal_adjustment=True, start_date=START_DATE,
            end_date=datetime.now(timezone.utc).date().isoformat()
        ),
        "inflation_expectations": lambda: obb.economy.survey.inflation_expectations(
            provider="federal_reserve", start_date=START_DATE,
            end_date=datetime.now(timezone.utc).date().isoformat()
        ),
        "effr": lambda: obb.fixedincome.rate.effr(
            provider="federal_reserve", start_date=START_DATE,
            end_date=datetime.now(timezone.utc).date().isoformat()
        ),
    }
    return {name: result.model_dump() for name, call in calls.items() for result in [call()]}


def build_openbb_metrics(raw: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    gdp_dates, gdp_levels = normalize_openbb_series(raw["gdp_real"], provider="oecd", value_field="value")
    gdp_dates = to_quarter_end(gdp_dates)
    gdp_growth = annualized_quarterly_growth(gdp_levels)

    cpi_dates, cpi_values = normalize_openbb_series(
        raw["cpi"], provider="oecd", value_field="value", scale=100
    )
    cpi_dates = to_month_end(cpi_dates)

    unemployment_dates, unemployment_values = normalize_openbb_series(
        raw["unemployment"], provider="oecd", value_field="value", scale=100
    )
    unemployment_dates = to_month_end(unemployment_dates)

    expectation_dates, expectation_1y = normalize_openbb_series(
        raw["inflation_expectations"],
        provider="federal_reserve",
        value_field="infcpi1yr",
    )
    _, expectation_10y = normalize_openbb_series(
        raw["inflation_expectations"],
        provider="federal_reserve",
        value_field="infcpi10yr",
    )
    effr_dates, effr_values = normalize_openbb_series(
        raw["effr"], provider="federal_reserve", value_field="rate", scale=100
    )
    effr_dates, effr_values = resample_records_month_end(effr_dates, effr_values)

    return {
        "real-gdp-growth": metric_from_series(
            metric_id="real-gdp-growth", title="实际GDP环比折年率", display_unit="%",
            decimals=1, frequency="季", dates=gdp_dates, values=gdp_growth,
            provider_label="OpenBB · OECD", route="/economy/gdp/real", institution="OECD",
            raw_unit="实际GDP水平（美元）", transform_label="OpenBB/OECD 实际GDP水平计算环比折年率"
        ),
        "unemployment-rate": metric_from_series(
            metric_id="unemployment-rate", title="失业率", display_unit="%", decimals=1,
            frequency="月", dates=unemployment_dates, values=unemployment_values,
            provider_label="OpenBB · OECD", route="/economy/unemployment", institution="OECD",
            raw_unit="小数", transform_label="OpenBB/OECD 小数值 × 100；季调，总人口"
        ),
        "cpi-yoy": metric_from_series(
            metric_id="cpi-yoy", title="CPI同比", display_unit="%", decimals=1,
            frequency="月", dates=cpi_dates, values=cpi_values,
            provider_label="OpenBB · OECD", route="/economy/cpi", institution="OECD",
            raw_unit="小数", transform_label="OpenBB/OECD yoy 小数值 × 100", reference=2
        ),
        "spf-inflation-1y": metric_from_series(
            metric_id="spf-inflation-1y", title="专业预测者1年CPI预期", display_unit="%",
            decimals=1, frequency="季", dates=expectation_dates, values=expectation_1y,
            provider_label="OpenBB · Federal Reserve", route="/economy/survey/inflation_expectations",
            institution="费城联储 SPF", raw_unit="%", reference=2
        ),
        "spf-inflation-10y": metric_from_series(
            metric_id="spf-inflation-10y", title="专业预测者10年CPI预期", display_unit="%",
            decimals=1, frequency="季", dates=expectation_dates, values=expectation_10y,
            provider_label="OpenBB · Federal Reserve", route="/economy/survey/inflation_expectations",
            institution="费城联储 SPF", raw_unit="%", reference=2
        ),
        "effective-fed-funds": metric_from_series(
            metric_id="effective-fed-funds", title="有效联邦基金利率", display_unit="%",
            decimals=2, frequency="月", dates=effr_dates, values=effr_values,
            provider_label="OpenBB · Federal Reserve", route="/fixedincome/rate/effr",
            institution="纽约联储", raw_unit="小数", transform_label="OpenBB/纽约联储日频 EFFR 月末值 × 100"
        ),
    }


def merge_dataset(dataset: dict[str, Any], raw: dict[str, dict[str, Any]], generated_at: str) -> dict[str, Any]:
    metrics = build_openbb_metrics(raw)
    replace_metric(dataset, "growth", metrics["real-gdp-growth"])
    replace_metric(dataset, "employment", metrics["unemployment-rate"])
    replace_metric(dataset, "inflation", metrics["cpi-yoy"])
    replace_metric_without_cross_check(
        dataset, "inflation", "michigan-inflation-1y", metrics["spf-inflation-1y"]
    )
    replace_metric_without_cross_check(
        dataset, "inflation", "michigan-inflation-5y", metrics["spf-inflation-10y"]
    )
    replace_metric(dataset, "policy", metrics["effective-fed-funds"])
    dataset["schemaVersion"] = 2
    dataset["generatedAt"] = generated_at
    dataset["source"] = "OpenBB + Wind EDB"
    dataset["sourceProviders"] = ["OpenBB/OECD", "OpenBB/Federal Reserve", "Wind EDB"]
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--input", type=Path, help="Use a saved OpenBB OBBject bundle instead of fetching.")
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    raw = json.loads(args.input.read_text(encoding="utf-8")) if args.input else fetch_openbb()

    args.raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = generated_at.replace(":", "").replace("-", "")
    raw_path = args.raw_dir / f"{stamp}_openbb.json"
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    dataset = merge_dataset(dataset, raw, generated_at)
    dataset.setdefault("rawSnapshots", {})["openbb"] = str(raw_path.relative_to(REPO_ROOT)).replace("\\", "/")
    args.dataset.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"wrote {args.dataset}")
    for category, payload in dataset["categories"].items():
        providers = sorted({metric["source"]["provider"] for metric in payload["metrics"]})
        print(f"{category}: {len(payload['metrics'])} metrics; {', '.join(providers)}")


if __name__ == "__main__":
    main()
