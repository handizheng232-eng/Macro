"""Build a US inflation workspace from iFinD 经济数据库 (EDB).

Reads the local iFinD client session token from its logs, fetches the US
inflation indicators via the gateway HTTP API, validates identity/units, and
writes ``src/data/usInflationData.json``.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import string
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "src" / "data" / "usInflationData.json"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "ifind-us-inflation"
START_DATE = "2000-01-01"

SEARCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/search/associate"
FETCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/fetch_data/search"
REFERER = "https://ft.51ifind.com/standardgwapi/bff/macro_bff/edb_web/index?pluginVersion=excel_win64"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 Chrome/84.0.4147.105 Safari/537.36"
LOG_TOKEN = re.compile(r'jgbsession["\'\:= ]+([0-9a-fA-F]{32})')
_HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")
_CODE_PREFIX = re.compile(r"^[A-Za-z]+0*")

# indicator -> (displayid, label, color, group)
SERIES_SPEC: dict[str, tuple[str, str, str]] = {
    "cpi_yoy": ("G002600362", "CPI同比", "#c94c4c"),
    "core_cpi_yoy": ("G002600363", "核心CPI同比", "#765a9b"),
    "cpi_food_yoy": ("G004754697", "食品同比", "#ba7a2e"),
    "cpi_energy_yoy": ("G002600364", "能源同比", "#2f7fa3"),
    "pce_yoy": ("G003586802", "PCE同比", "#c94c4c"),
    "core_pce_yoy": ("G003586807", "核心PCE同比", "#765a9b"),
    "pce_goods_yoy": ("G003586803", "PCE商品同比", "#ba7a2e"),
    "pce_services_yoy": ("G003586806", "PCE服务同比", "#2f7fa3"),
    "cpi_mom": ("G002600387", "CPI环比", "#c94c4c"),
    "core_cpi_mom": ("G002600388", "核心CPI环比", "#765a9b"),
    "cpi_food_mom": ("G004765340", "食品环比", "#ba7a2e"),
    "cpi_energy_mom": ("G004765461", "能源环比", "#2f7fa3"),
    "cpi_goods_mom": ("G004765476", "商品(不含食品能源)环比", "#3c8b6d"),
    "cpi_services_mom": ("G004765593", "服务(不含能源)环比", "#1c3557"),
    "cpi_housing_mom": ("G004765795", "住房环比", "#6f7883"),
    "cpi_housing_yoy": ("G004765751", "住房同比", "#6f7883"),
    "cpi_goods_yoy": ("G004754833", "商品(不含食品能源)同比", "#3c8b6d"),
    "cpi_services_yoy": ("G004754950", "服务(不含能源)同比", "#1c3557"),
    "cpi_supercore_yoy": ("G005419378", "超级核心服务同比", "#6b4a9e"),
    "cpi_supercore_mom": ("G005464099", "超级核心服务环比", "#6b4a9e"),
    "pce_supercore_index": ("G040632725", "PCE超级核心服务指数", "#2f7fa3"),
    "eci_wage_yoy": ("G005349376", "ECI私营企业工资同比", "#c94c4c"),
    "unit_labor_cost_index": ("G038490818", "非农商业单位劳动力成本指数", "#ba7a2e"),
    "contrib_core_services": ("G025044051", "核心服务", "#6b4a9e"),
    "contrib_core_goods": ("G025043937", "核心商品", "#2f7fa3"),
    "contrib_food": ("G025043803", "食品", "#ba7a2e"),
    "contrib_energy": ("G025043922", "能源", "#c94c4c"),
    "food_home_yoy": ("G004754698", "家庭食品同比", "#ba7a2e"),
    "food_home_mom": ("G004764993", "家庭食品环比", "#ba7a2e"),
    "food_away_yoy": ("G005419489", "外出就餐同比", "#ba7a2e"),
    "food_away_mom": ("G005464202", "外出就餐环比", "#ba7a2e"),
    "energy_goods_yoy": ("G004754819", "能源商品同比", "#c94c4c"),
    "energy_goods_mom": ("G004765114", "能源商品环比", "#c94c4c"),
    "energy_services_yoy": ("G005419525", "能源服务同比", "#c94c4c"),
    "energy_services_mom": ("G005464228", "能源服务环比", "#c94c4c"),
    "electricity_yoy": ("G005419526", "电力同比", "#c94c4c"),
    "electricity_mom": ("G005464229", "电力环比", "#c94c4c"),
    "utility_gas_yoy": ("G005419527", "管道燃气同比", "#c94c4c"),
    "utility_gas_mom": ("G005464230", "管道燃气环比", "#c94c4c"),
    "apparel_yoy": ("G002600368", "服饰同比", "#2f7fa3"),
    "apparel_mom": ("G005464045", "服饰环比", "#2f7fa3"),
    "edu_goods_yoy": ("G005419343", "教育通信商品同比", "#2f7fa3"),
    "edu_goods_mom": ("G005464059", "教育通信商品环比", "#2f7fa3"),
    "other_goods_yoy": ("G005419356", "其他商品同比", "#2f7fa3"),
    "other_goods_mom": ("G005464075", "其他商品环比", "#2f7fa3"),
    "rent_yoy": ("G005419515", "主要住所租金同比", "#765a9b"),
    "rent_mom": ("G005464219", "主要住所租金环比", "#765a9b"),
    "oer_yoy": ("G004754958", "业主等价租金同比", "#765a9b"),
    "oer_mom": ("G004765253", "业主等价租金环比", "#765a9b"),
    "medical_services_yoy": ("G002600370", "医疗服务同比", "#6b4a9e"),
    "medical_services_mom": ("G005464082", "医疗服务环比", "#6b4a9e"),
    "transport_services_yoy": ("G004754981", "运输服务同比", "#6b4a9e"),
    "transport_services_mom": ("G004765276", "运输服务环比", "#6b4a9e"),
    "airfare_yoy": ("G005419622", "机票同比", "#6b4a9e"),
    "airfare_mom": ("G005464299", "机票环比", "#6b4a9e"),
    "edu_services_yoy": ("G004755020", "教育通信服务同比", "#6b4a9e"),
    "edu_services_mom": ("G004765315", "教育通信服务环比", "#6b4a9e"),
    "personal_services_yoy": ("G005419508", "其他个人服务同比", "#6b4a9e"),
    "personal_services_mom": ("G005464213", "其他个人服务环比", "#6b4a9e"),
    "weight_food": ("G019184577", "食品权重", "#888888"),
    "weight_food_home": ("G019184578", "家庭食品权重", "#888888"),
    "weight_food_away": ("G019184655", "外出就餐权重", "#888888"),
    "weight_energy": ("G019184661", "能源权重", "#888888"),
    "weight_energy_goods": ("G019184662", "能源商品权重", "#888888"),
    "weight_energy_services": ("G019184669", "能源服务权重", "#888888"),
    "weight_electricity": ("G019184670", "电力权重", "#888888"),
    "weight_utility_gas": ("G019184671", "管道燃气权重", "#888888"),
    "weight_core_goods": ("G019184673", "核心商品权重", "#888888"),
    "weight_apparel": ("G019184698", "服饰权重", "#888888"),
    "weight_edu_goods": ("G019184750", "教育通信商品权重", "#888888"),
    "weight_other_goods": ("G019184762", "其他商品权重", "#888888"),
    "weight_core_services": ("G019184770", "核心服务权重", "#888888"),
    "weight_shelter": ("G019184772", "住房权重", "#888888"),
    "weight_rent": ("G019184773", "主要住所租金权重", "#888888"),
    "weight_oer": ("G019184777", "业主等价租金权重", "#888888"),
    "weight_medical_services": ("G019184786", "医疗服务权重", "#888888"),
    "weight_transport_services": ("G019184797", "运输服务权重", "#888888"),
    "weight_airfare": ("G019184808", "机票权重", "#888888"),
    "weight_edu_services": ("G019184821", "教育通信服务权重", "#888888"),
    "weight_personal_services": ("G019184837", "其他个人服务权重", "#888888"),
    "weight_supercore": ("G025882546", "超级核心服务权重", "#888888"),
    "mich_1y": ("G012274201", "密歇根大学1年预期", "#2f7fa3"),
    "mich_5y": ("G012937589", "密歇根大学5年预期", "#765a9b"),
    "cleve_1y": ("G014102434", "克利夫兰联储1年预期", "#2f7fa3"),
    "cleve_5y": ("G014102439", "克利夫兰联储5年预期", "#765a9b"),
    "cleve_10y": ("G014102444", "克利夫兰联储10年预期", "#c94c4c"),
    "be_5y": ("G013233145", "5年盈亏平衡通胀率", "#765a9b"),
    "be_7y": ("G013233146", "7年盈亏平衡通胀率", "#ba7a2e"),
    "be_10y": ("G013233147", "10年盈亏平衡通胀率", "#c94c4c"),
    "be_20y": ("G013233148", "20年盈亏平衡通胀率", "#3c8b6d"),
}

CPI_TREND_KEYS = ["cpi_yoy", "core_cpi_yoy", "cpi_food_yoy", "cpi_energy_yoy"]
PCE_TREND_KEYS = ["pce_yoy", "core_pce_yoy", "pce_goods_yoy", "pce_services_yoy"]
CORE_SPLIT_KEYS = ["cpi_goods_yoy", "cpi_housing_yoy", "cpi_supercore_yoy"]
CORE_SPLIT_LABELS = {"cpi_goods_yoy": "核心商品", "cpi_housing_yoy": "住房", "cpi_supercore_yoy": "超级核心服务"}
SURVEY_KEYS = ["mich_1y", "mich_5y", "cleve_1y", "cleve_5y", "cleve_10y"]
BREAKEVEN_KEYS = ["be_5y", "be_7y", "be_10y", "be_20y"]

NATURE = {
    "cpi_yoy": "总量",
    "core_cpi_yoy": "总量",
    "cpi_food_yoy": "波动项",
    "cpi_energy_yoy": "波动项",
    "cpi_goods_yoy": "周期分项",
    "cpi_services_yoy": "结构分项",
    "cpi_housing_yoy": "结构分项",
    "pce_yoy": "总量",
    "core_pce_yoy": "总量",
    "pce_goods_yoy": "周期分项",
    "pce_services_yoy": "结构分项",
}

CYCLE_STATS_KEYS = [
    ("核心商品", "cpi_goods_yoy", "周期分项", "周期"),
    ("住房", "cpi_housing_yoy", "半结构分项", "半结构"),
    ("超级核心服务", "cpi_supercore_yoy", "结构分项", "结构"),
]

CONTRIBUTION_KEYS = ["contrib_core_services", "contrib_core_goods", "contrib_food", "contrib_energy"]

# label, group, yoy key, mom key, weight key, depth
HEATMAP_ROWS = [
    ("所有项目", "总量", "cpi_yoy", "cpi_mom", None, 0),
    ("食品", "食品", "cpi_food_yoy", "cpi_food_mom", "weight_food", 0),
    ("家庭食品", "食品", "food_home_yoy", "food_home_mom", "weight_food_home", 1),
    ("外出就餐", "食品", "food_away_yoy", "food_away_mom", "weight_food_away", 1),
    ("能源", "能源", "cpi_energy_yoy", "cpi_energy_mom", "weight_energy", 0),
    ("能源商品", "能源", "energy_goods_yoy", "energy_goods_mom", "weight_energy_goods", 1),
    ("能源服务", "能源", "energy_services_yoy", "energy_services_mom", "weight_energy_services", 1),
    ("电力", "能源", "electricity_yoy", "electricity_mom", "weight_electricity", 2),
    ("管道燃气", "能源", "utility_gas_yoy", "utility_gas_mom", "weight_utility_gas", 2),
    ("核心商品", "核心商品", "cpi_goods_yoy", "cpi_goods_mom", "weight_core_goods", 0),
    ("服饰", "核心商品", "apparel_yoy", "apparel_mom", "weight_apparel", 1),
    ("教育通信商品", "核心商品", "edu_goods_yoy", "edu_goods_mom", "weight_edu_goods", 1),
    ("其他商品", "核心商品", "other_goods_yoy", "other_goods_mom", "weight_other_goods", 1),
    ("核心服务", "核心服务", "cpi_services_yoy", "cpi_services_mom", "weight_core_services", 0),
    ("住房", "核心服务", "cpi_housing_yoy", "cpi_housing_mom", "weight_shelter", 1),
    ("主要住所租金", "核心服务", "rent_yoy", "rent_mom", "weight_rent", 2),
    ("业主等价租金", "核心服务", "oer_yoy", "oer_mom", "weight_oer", 2),
    ("医疗服务", "核心服务", "medical_services_yoy", "medical_services_mom", "weight_medical_services", 1),
    ("运输服务", "核心服务", "transport_services_yoy", "transport_services_mom", "weight_transport_services", 1),
    ("机票", "核心服务", "airfare_yoy", "airfare_mom", "weight_airfare", 2),
    ("教育通信服务", "核心服务", "edu_services_yoy", "edu_services_mom", "weight_edu_services", 1),
    ("其他个人服务", "核心服务", "personal_services_yoy", "personal_services_mom", "weight_personal_services", 1),
    ("超级核心服务", "超级核心", "cpi_supercore_yoy", "cpi_supercore_mom", "weight_supercore", 0),
]

DETAIL_ROWS = [
    ("所有项目", "cpi_yoy", "cpi_mom", 0),
    ("食品", "cpi_food_yoy", "cpi_food_mom", 1),
    ("能源", "cpi_energy_yoy", "cpi_energy_mom", 1),
    ("核心", "core_cpi_yoy", "core_cpi_mom", 0),
    ("商品(不含食品能源)", "cpi_goods_yoy", "cpi_goods_mom", 1),
    ("服务(不含能源)", "cpi_services_yoy", "cpi_services_mom", 1),
    ("住房", "cpi_housing_yoy", "cpi_housing_mom", 1),
]


def compact_date(value: Any) -> str:
    text = str(value)
    normalized = text.replace("-", "").replace("/", "").replace(".", "")
    if len(normalized) == 6:
        year, month = int(normalized[:4]), int(normalized[4:6])
        return f"{year:04d}{month:02d}01"
    if len(normalized) >= 8:
        return normalized[:8]
    raise ValueError(f"invalid observation date: {value!r}")


def detect_missing_months(dates: Iterable[str]) -> list[str]:
    periods = sorted({str(value)[:6].replace("-", "") for value in dates})
    if not periods:
        return []
    current_year, current_month = int(periods[0][:4]), int(periods[0][4:6])
    end_year, end_month = int(periods[-1][:4]), int(periods[-1][4:6])
    expected: list[str] = []
    while (current_year, current_month) <= (end_year, end_month):
        expected.append(f"{current_year:04d}{current_month:02d}")
        current_month += 1
        if current_month == 13:
            current_year += 1
            current_month = 1
    return [period for period in expected if period not in periods]


def fetch_response_series(payload: dict[str, Any], display_id: str) -> tuple[list[str], list[float]]:
    if payload.get("code") != 1:
        raise ValueError(f"iFinD rejected request: {payload.get('msg') or payload.get('code')}")
    data = payload.get("data") or {}
    tables = data.get("tables") or []
    table = next((t for t in tables if str(t.get("displayid") or "") == display_id), None)
    if table is None:
        raise ValueError(f"iFinD returned no data block for {display_id}")
    dates, values = table.get("time") or [], table.get("value") or []
    rows = [
        (compact_date(d), float(v))
        for d, v in zip(dates, values)
        if v not in (None, "", "--")
    ]
    rows.sort(key=lambda item: item[0])
    if not rows:
        raise ValueError(f"iFinD returned no observations for {display_id}")
    return [row[0] for row in rows], [row[1] for row in rows]


def _candidate_log_dirs() -> Iterable[Path]:
    env = None
    import os
    env = os.environ.get("IFIND_LOG_DIR")
    if env:
        yield Path(env)
    for drive in string.ascii_uppercase:
        root = Path(f"{drive}:\\")
        try:
            if not root.is_dir():
                continue
        except OSError:
            continue
        for upper in (root, root / "Program Files", root / "Program Files (x86)"):
            try:
                if not upper.is_dir():
                    continue
                for child in upper.iterdir():
                    if "ifind" in child.name.lower():
                        log_dir = child / "logs"
                        if log_dir.is_dir():
                            yield log_dir
            except (OSError, PermissionError):
                continue


def read_token() -> tuple[str, Path]:
    for log_dir in _candidate_log_dirs():
        try:
            logs = sorted(log_dir.glob("socketclient_*.xlog"), key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError:
            continue
        for log_file in logs:
            try:
                text = log_file.read_bytes().decode("utf-8", "ignore")
            except OSError:
                continue
            hits = LOG_TOKEN.findall(text)
            if hits and _HEX32.match(hits[-1]):
                return hits[-1], log_file
    raise RuntimeError("未找到 iFinD 登录会话：请打开 iFinD 客户端登录一次后再运行。")


def fetch_indicator(token: str, display_id: str, start: str, end: str) -> dict[str, Any]:
    form = urllib.parse.urlencode({
        "zb_str": _CODE_PREFIX.sub("", display_id) or display_id,
        "displayid": display_id,
        "zb_rtime": "0", "formula": "0", "wt": "json", "usage": "macro",
        "sdate": start.replace("-", ""), "edate": end.replace("-", ""),
    }).encode()
    request = urllib.request.Request(FETCH_URL, data=form, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": USER_AGENT, "Referer": REFERER,
        "Origin": "https://ft.51ifind.com",
        "Cookie": f"jgbsessid={token}",
    })
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all(token: str) -> dict[str, dict[str, Any]]:
    end = datetime.now(timezone.utc).date().isoformat()
    return {
        key: fetch_indicator(token, display_id, START_DATE, end)
        for key, (display_id, _label, _color) in SERIES_SPEC.items()
    }


def series(
    *,
    series_id: str,
    label: str,
    dates: list[str],
    values: list[float],
    color: str,
    code: str,
) -> dict[str, Any]:
    return {
        "id": series_id,
        "label": label,
        "dates": dates,
        "values": values,
        "color": color,
        "frequency": "月",
        "defaultActive": True,
        "latestObservation": dates[-1],
        "latestValue": values[-1],
        "source": {
            "provider": "iFinD EDB",
            "institution": "iFinD 经济数据库",
            "code": code,
            "name": label,
            "rawUnit": "%",
            "url": "https://ft.51ifind.com",
            "latestObservation": dates[-1],
        },
    }


def build_chart(parsed: dict[str, tuple[list[str], list[float]]], keys: list[str]) -> list[dict[str, Any]]:
    return [
        series(
            series_id=key, label=SERIES_SPEC[key][1], dates=parsed[key][0],
            values=parsed[key][1], color=SERIES_SPEC[key][2], code=SERIES_SPEC[key][0],
        )
        for key in keys
    ]


def pct_change_series(
    dates: list[str], values: list[float], lag: int,
) -> tuple[list[str], list[float]]:
    rows = []
    for index in range(lag, len(values)):
        previous = values[index - lag]
        if previous == 0:
            continue
        rows.append((dates[index], (values[index] / previous - 1) * 100))
    return [row[0] for row in rows], [row[1] for row in rows]


def annual_means(dates: list[str], values: list[float]) -> dict[int, float]:
    buckets: dict[int, list[float]] = {}
    for date, value in zip(dates, values):
        buckets.setdefault(int(date[:4]), []).append(value)
    return {year: statistics.fmean(sample) for year, sample in buckets.items() if sample}


def pearson(left: dict[int, float], right: dict[int, float]) -> float:
    years = sorted(set(left) & set(right))
    if len(years) < 3:
        return 0.0
    xs, ys = [left[y] for y in years], [right[y] for y in years]
    xm, ym = statistics.fmean(xs), statistics.fmean(ys)
    numerator = sum((x - xm) * (y - ym) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - xm) ** 2 for x in xs) * sum((y - ym) ** 2 for y in ys))
    return numerator / denominator if denominator else 0.0


def half_life_years(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    lagged, current = values[:-1], values[1:]
    xm, ym = statistics.fmean(lagged), statistics.fmean(current)
    denominator = sum((x - xm) ** 2 for x in lagged)
    rho = sum((x - xm) * (y - ym) for x, y in zip(lagged, current)) / denominator if denominator else 0.0
    if not 0 < rho < 1:
        return 0.0
    return -math.log(2) / math.log(rho)


def cycle_structure_stats(parsed: dict[str, tuple[list[str], list[float]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    wage_annual = annual_means(*parsed["eci_wage_yoy"])
    for label, key, nature, classification in CYCLE_STATS_KEYS:
        dates, values = parsed[key]
        long_points = [(d, v) for d, v in zip(dates, values) if d >= "20000101"]
        post_shock = [(d, v) for d, v in long_points if d >= "20200101"]
        annual = annual_means(*parsed[key])
        baseline_values = [value for year, value in annual.items() if 2015 <= year <= 2019]
        if not long_points or not post_shock or not baseline_values:
            continue
        peak = max(value for _, value in post_shock)
        peak_date = max((date for date, value in post_shock if value == peak), default="")
        latest = values[-1]
        baseline = statistics.fmean(baseline_values)
        retrace = (peak - latest) / (peak - baseline) * 100 if peak != baseline else 100.0
        retrace = min(100.0, max(0.0, retrace))
        rows.append({
            "id": key,
            "label": label,
            "nature": nature,
            "classification": classification,
            "peak": round(peak, 2),
            "peakDate": peak_date,
            "latest": round(latest, 2),
            "latestDate": dates[-1],
            "baseline": round(baseline, 2),
            "annualVolatility": round(statistics.pstdev(list(annual.values())), 2),
            "halfLifeYears": round(half_life_years([annual[year] for year in sorted(annual)]), 2),
            "wageCorrelation": round(pearson(annual, wage_annual), 2),
            "retrace": round(retrace, 1),
            "code": SERIES_SPEC[key][0],
        })
    return rows


def build_heatmap(parsed: dict[str, tuple[list[str], list[float]]]) -> dict[str, Any]:
    periods = list(dict.fromkeys(date[:6] for date in reversed(parsed["cpi_yoy"][0])))[:12]
    rows = []
    for label, group, yoy_key, mom_key, weight_key, depth in HEATMAP_ROWS:
        yoy_map = {date[:6]: value for date, value in zip(*parsed[yoy_key])}
        mom_map = {date[:6]: value for date, value in zip(*parsed[mom_key])}
        weight = 100.0 if weight_key is None else parsed[weight_key][1][-1]
        rows.append({
            "id": yoy_key,
            "label": label,
            "group": group,
            "depth": depth,
            "weight": round(weight, 2),
            "yoy": [round(yoy_map[p], 2) if p in yoy_map else None for p in periods],
            "mom": [round(mom_map[p], 2) if p in mom_map else None for p in periods],
            "source": {"provider": "iFinD EDB", "code": SERIES_SPEC[yoy_key][0]},
        })
    return {"periods": periods, "rows": rows}


def build_dataset(raw: dict[str, dict[str, Any]], generated_at: str, raw_snapshot: str) -> dict[str, Any]:
    parsed: dict[str, tuple[list[str], list[float]]] = {}
    for key, (display_id, _label, _color) in SERIES_SPEC.items():
        parsed[key] = fetch_response_series(raw[key], display_id)

    cpi_dates = parsed["cpi_yoy"][0]
    cpi_missing = detect_missing_months(cpi_dates)

    cpi_trend = build_chart(parsed, CPI_TREND_KEYS)
    pce_trend = build_chart(parsed, PCE_TREND_KEYS)
    core_split = build_chart(parsed, CORE_SPLIT_KEYS)
    for item in core_split:
        item["label"] = CORE_SPLIT_LABELS[item["id"]]
    cycle_rows = cycle_structure_stats(parsed)
    heatmap = build_heatmap(parsed)

    contribution_series = build_chart(parsed, CONTRIBUTION_KEYS)

    pce_supercore_dates, pce_supercore_values = pct_change_series(*parsed["pce_supercore_index"], lag=1)
    supercore_mom = [
        series(
            series_id="cpi_supercore_mom", label="CPI口径",
            dates=parsed["cpi_supercore_mom"][0], values=parsed["cpi_supercore_mom"][1],
            color="#6b4a9e", code=SERIES_SPEC["cpi_supercore_mom"][0],
        ),
        series(
            series_id="pce_supercore_mom", label="PCE口径",
            dates=pce_supercore_dates, values=[round(value, 4) for value in pce_supercore_values],
            color="#2f7fa3", code=SERIES_SPEC["pce_supercore_index"][0],
        ),
    ]

    ulc_dates, ulc_values = pct_change_series(*parsed["unit_labor_cost_index"], lag=4)
    wage_anchor = [
        series(
            series_id="eci_wage_yoy", label="ECI私营企业工资同比",
            dates=parsed["eci_wage_yoy"][0], values=parsed["eci_wage_yoy"][1],
            color="#c94c4c", code=SERIES_SPEC["eci_wage_yoy"][0],
        ),
        series(
            series_id="unit_labor_cost_yoy", label="单位劳动成本同比",
            dates=ulc_dates, values=[round(value, 4) for value in ulc_values],
            color="#ba7a2e", code=SERIES_SPEC["unit_labor_cost_index"][0],
        ),
        series(
            series_id="cpi_supercore_yoy", label="超级核心服务同比",
            dates=parsed["cpi_supercore_yoy"][0], values=parsed["cpi_supercore_yoy"][1],
            color="#6b4a9e", code=SERIES_SPEC["cpi_supercore_yoy"][0],
        ),
    ]

    detail_rows = []
    for label, yoy_key, mom_key, depth in DETAIL_ROWS:
        yoy_dates, yoy_values = parsed[yoy_key]
        mom_dates, mom_values = parsed[mom_key]
        # use the latest common month between yoy and mom
        yoy_map = {date[:6]: value for date, value in zip(yoy_dates, yoy_values)}
        mom_map = {date[:6]: value for date, value in zip(mom_dates, mom_values)}
        common = sorted(set(yoy_map) & set(mom_map))
        if not common:
            raise ValueError(f"no common month for detail {label}")
        period = common[-1]
        yoy = yoy_map[period]
        mom = mom_map[period]
        previous_periods = [p for p in sorted(yoy_map) if p < period]
        previous_yoy = yoy_map[previous_periods[-1]] if previous_periods else yoy
        detail_rows.append({
            "id": yoy_key,
            "label": label,
            "depth": depth,
            "nature": NATURE[yoy_key],
            "observation": f"{period}01",
            "yoy": round(yoy, 4),
            "yoyChange": round(yoy - previous_yoy, 4),
            "mom": round(mom, 4),
            "source": {
                "provider": "iFinD EDB",
                "institution": "iFinD 经济数据库",
                "code": SERIES_SPEC[yoy_key][0],
                "name": label,
                "rawUnit": "%",
                "url": "https://ft.51ifind.com",
                "latestObservation": f"{period}01",
            },
        })

    survey_series = build_chart(parsed, SURVEY_KEYS)
    for item in survey_series:
        if item["id"] in ("cleve_1y", "cleve_5y", "cleve_10y"):
            item["dash"] = "3 4"

    breakeven_series = build_chart(parsed, BREAKEVEN_KEYS)
    latest_curve = [
        {"tenor": item["label"].replace("盈亏平衡通胀率", ""), "value": item["latestValue"], "observation": item["latestObservation"]}
        for item in breakeven_series
    ]

    headline_lookup = {item["id"]: item for item in survey_series + breakeven_series}
    pce_lookup = {item["id"]: item for item in pce_trend}

    return {
        "schemaVersion": 4,
        "generatedAt": generated_at,
        "source": "iFinD EDB",
        "sourceProviders": ["iFinD EDB"],
        "headline": [
            {"id": "actual", "label": "实际通胀", "title": "核心PCE同比", "value": pce_lookup["core_pce_yoy"]["latestValue"], "unit": "%", "observation": pce_lookup["core_pce_yoy"]["latestObservation"], "source": "iFinD EDB"},
            {"id": "survey", "label": "调查通胀", "title": "密歇根大学1年预期", "value": headline_lookup["mich_1y"]["latestValue"], "unit": "%", "observation": headline_lookup["mich_1y"]["latestObservation"], "source": "iFinD EDB"},
            {"id": "implied", "label": "市场隐含", "title": "5年盈亏平衡通胀率", "value": headline_lookup["be_5y"]["latestValue"], "unit": "%", "observation": headline_lookup["be_5y"]["latestObservation"], "source": "iFinD EDB"},
        ],
        "actual": {
            "cpiTrend": {
                "id": "cpi-trend", "eyebrow": "ACTUAL · CPI",
                "title": "CPI同比分项", "description": "iFinD EDB 美国劳工局数据：总CPI、核心、食品与能源当月同比。",
                "unit": "%", "reference": 2, "defaultRange": "5Y", "series": cpi_trend,
            },
            "pceTrend": {
                "id": "pce-trend", "eyebrow": "ACTUAL · PCE",
                "title": "PCE同比分项", "description": "iFinD EDB 美国经济分析局数据：总PCE、核心、商品与服务当月同比。",
                "unit": "%", "reference": 2, "defaultRange": "5Y", "series": pce_trend,
            },
            "coreSplit": {
                "id": "core-split", "eyebrow": "ACTUAL · CYCLE vs STRUCTURE",
                "title": "核心通胀三分项", "description": "按核心商品、住房与超级核心服务拆分；总量核心CPI只是三者的加权平均，不直接携带机制信息。",
                "unit": "%", "reference": 2, "defaultRange": "5Y", "series": core_split,
            },
            "cpiContributions": {
                "id": "cpi-contributions", "eyebrow": "ACTUAL · CONTRIBUTION",
                "title": "CPI环比分项贡献", "description": "iFinD季调分项对CPI环比的直接影响值，分为核心服务、核心商品、食品与能源。",
                "unit": "百分点", "reference": 0, "defaultRange": "3Y", "series": contribution_series,
                "totalSeries": series(
                    series_id="cpi_mom_total", label="CPI环比",
                    dates=parsed["cpi_mom"][0], values=parsed["cpi_mom"][1],
                    color="#1c2530", code=SERIES_SPEC["cpi_mom"][0],
                ),
            },
            "supercoreMom": {
                "id": "supercore-mom", "eyebrow": "ACTUAL · SUPERCORE",
                "title": "超级核心通胀环比", "description": "CPI服务剔除住房与PCE服务剔除住房和能源，均采用季调环比；PCE由指数计算。",
                "unit": "%", "reference": 0, "defaultRange": "3Y", "series": supercore_mom,
            },
            "wageAnchor": {
                "id": "wage-anchor", "eyebrow": "STRUCTURE · WAGE ANCHOR",
                "title": "工资—劳动成本—超级核心服务", "description": "工资与单位劳动成本是结构性服务通胀的锚；月度与季度序列保留各自观测日期。",
                "unit": "%", "reference": 2, "defaultRange": "5Y", "series": wage_anchor,
            },
            "cycleStructure": {
                "title": "周期与结构：四项统计检验",
                "description": "年度波动率、AR(1)冲击半衰期、与ECI工资同比的相关性、相对2015—2019均值的归位度共同识别周期与结构。",
                "rows": cycle_rows,
                "source": {"provider": "iFinD EDB", "route": "https://ft.51ifind.com"},
            },
            "cpiHeatmap": {
                "title": "CPI分项温度表",
                "description": "参考CPI报告结构，展示23个总量与细分项目最近12个可用月份的同比/季调环比及最新权重。",
                **heatmap,
                "source": {"provider": "iFinD EDB", "route": "https://ft.51ifind.com"},
            },
            "cpiDetail": {
                "title": "CPI分项明细",
                "description": "各分项当月同比、环比与同比变化并列；「性质」栏区分总量、波动项、周期分项与结构分项。",
                "rows": detail_rows,
                "source": {"provider": "iFinD EDB", "route": "https://ft.51ifind.com"},
            },
        },
        "survey": {
            "expectations": {
                "id": "survey-expectations", "eyebrow": "SURVEY · EXPECTATIONS",
                "title": "居民与模型通胀预期", "description": "密歇根大学居民调查与克利夫兰联储模型预期，二者口径不同，分开阅读。",
                "unit": "%", "reference": 2, "defaultRange": "5Y", "series": survey_series,
            },
        },
        "implied": {
            "breakeven": {
                "id": "breakeven-curve", "eyebrow": "MARKET · BREAKEVEN",
                "title": "盈亏平衡通胀率期限结构", "description": "名义国债与TIPS价差隐含的通胀定价，含风险与流动性溢价，非无偏预测。",
                "unit": "%", "reference": 2, "defaultRange": "3Y", "series": breakeven_series,
            },
            "latestCurve": latest_curve,
        },
        "dataQuality": {
            "cpiMissingPeriods": cpi_missing,
            "note": "iFinD EDB 各序列独立更新日期；CPI/PCE/调查/盈亏平衡通胀率不共享同一截至日。",
        },
        "rawSnapshots": {"ifind": raw_snapshot},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--input", type=Path, help="Use a saved iFinD raw bundle instead of fetching.")
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if args.input:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
    else:
        token, log_file = read_token()
        print(f"read iFinD session from {log_file.name}")
        raw = fetch_all(token)
        args.raw_dir.mkdir(parents=True, exist_ok=True)
        stamp = generated_at.replace(":", "").replace("-", "")
        raw_path = args.raw_dir / f"{stamp}_ifind_inflation.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"raw saved to {raw_path}")

    dataset = build_dataset(raw, generated_at, str(raw_path.relative_to(REPO_ROOT)).replace("\\", "/") if not args.input else str(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"cpiTrend: {len(dataset['actual']['cpiTrend']['series'])} series")
    print(f"pceTrend: {len(dataset['actual']['pceTrend']['series'])} series")
    print(f"coreSplit: {len(dataset['actual']['coreSplit']['series'])} series")
    print(f"cycleStructure: {len(dataset['actual']['cycleStructure']['rows'])} rows")
    print(f"detail rows: {len(dataset['actual']['cpiDetail']['rows'])}")
    print(f"survey: {len(dataset['survey']['expectations']['series'])} series")
    print(f"breakeven: {len(dataset['implied']['breakeven']['series'])} series")
    print(f"CPI missing periods: {dataset['dataQuality']['cpiMissingPeriods']}")


if __name__ == "__main__":
    main()
