"""Build the US employment workspace from iFinD 经济数据库 (EDB).

The script reads the active local iFinD desktop session, validates every series
against iFinD search metadata, caches the raw responses, and writes the browser
snapshot at ``src/data/usEmploymentData.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import string
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "src" / "data" / "usEmploymentData.json"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "ifind-us-employment"
START_DATE = "1990-01-01"

SEARCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/search/associate"
FETCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/fetch_data/search"
REFERER = "https://ft.51ifind.com/standardgwapi/bff/macro_bff/edb_web/index?pluginVersion=excel_win64"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 Chrome/84.0.4147.105 Safari/537.36"
LOG_TOKEN = re.compile(r'jgbsession["\'\:= ]+([0-9a-fA-F]{32})')
_HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")
_CODE_PREFIX = re.compile(r"^[A-Za-z]+0*")

# key: code, exact iFinD name, label, unit, frequency, color, plausible range
SERIES_SPEC: dict[str, tuple[str, str, str, str, str, str, tuple[float, float]]] = {
    "participation_total": ("G003145519", "美国:劳动力参与率:16岁及以上:季调:当月值", "16岁以上", "%", "月", "#1859b8", (40, 80)),
    "participation_prime": ("G009358689", "美国:劳动力参与率:25至54岁:季调:当月值", "25—54岁", "%", "月", "#2f8a7a", (60, 95)),
    "u1": ("G005311376", "美国:失业率:U1:季调:当月值", "U1 长期失业率", "%", "月", "#c94c4c", (0, 20)),
    "u2": ("G005311377", "美国:失业率:U2:季调:当月值", "U2 非自愿失业率", "%", "月", "#ba7a2e", (0, 25)),
    "u3": ("G005311378", "美国:失业率:U3:季调:当月值", "U3 官方失业率", "%", "月", "#1859b8", (0, 30)),
    "u4": ("G005311379", "美国:失业率:U4:季调:当月值", "U4 含灰心者", "%", "月", "#8a9096", (0, 35)),
    "u5": ("G005311380", "美国:失业率:U5:季调:当月值", "U5 含边缘依附者", "%", "月", "#6f7883", (0, 35)),
    "u6": ("G005311381", "美国:失业率:U6:季调:当月值", "U6 最宽口径", "%", "月", "#a56a12", (0, 40)),
    "longterm_share": ("G003049371", "美国:失业人数占比:27周及以上:季调:当月值", "27周以上长期失业占比", "%", "月", "#c94c4c", (0, 100)),
    "temporary_unemployed": ("G003049325", "美国:失业人数:非自愿性失业(含临时工):暂时性解雇:季调:当月值", "暂时性解雇", "千人", "月", "#ba7a2e", (0, 20000)),
    "permanent_unemployed": ("G003049327", "美国:失业人数:非自愿性失业(含临时工):非暂时性解雇:失业并寻找新工作:季调:当月值", "失业并寻找新工作", "千人", "月", "#c94c4c", (0, 20000)),
    "duration_median": ("G003049383", "美国:失业人数:持续时间中位数:季调:当月值", "持续时间中位数", "周", "月", "#1859b8", (0, 60)),
    "duration_average": ("G003049382", "美国:失业人数:持续时间平均数:季调:当月值", "持续时间平均数", "周", "月", "#855c9c", (0, 80)),
    "unemployment_black": ("G005312729", "美国:失业率:黑人或非洲裔:16岁及以上:季调:当月值", "黑人", "%", "月", "#c94c4c", (0, 40)),
    "unemployment_white": ("G005312725", "美国:失业率:白人:16岁及以上:季调:当月值", "白人", "%", "月", "#8a9096", (0, 35)),
    "unemployment_hispanic": ("G005312734", "美国:失业率:西班牙或拉丁美洲裔:16岁及以上:季调:当月值", "拉美裔", "%", "月", "#a56a12", (0, 40)),
    "unemployment_teen": ("G003145555", "美国:失业率:16至19岁:季调:当月值", "16—19岁", "%", "月", "#c94c4c", (0, 60)),
    "unemployment_young": ("G005315505", "美国:失业率:20-24岁:季调:当月值", "20—24岁", "%", "月", "#a56a12", (0, 50)),
    "unemployment_prime": ("G005315507", "美国:失业率:25-54岁:季调:当月值", "25—54岁", "%", "月", "#1859b8", (0, 30)),
    "unemployment_prime_male": ("G005315518", "美国:失业率:男性:25-54岁:季调:当月值", "25—54岁男性", "%", "月", "#1859b8", (0, 30)),
    "unemployment_prime_female": ("G005315529", "美国:失业率:女性:25-54岁:季调:当月值", "25—54岁女性", "%", "月", "#c94c4c", (0, 30)),
    "cps_employment": ("G002600502", "美国:就业人数:16岁及以上:季调:当月值", "CPS家庭就业人数", "千人", "月", "#c94c4c", (50_000, 250_000)),
    "ces_employment": ("G003048986", "美国:就业人数:非农业部门:季调:当月值", "CES非农就业岗位", "千人", "月", "#1859b8", (50_000, 250_000)),
    "initial_claims": ("G002600494", "美国:当周初次申请失业金人数:季调", "初请失业金", "人", "周", "#1859b8", (0, 10_000_000)),
    "continuing_claims": ("G002600496", "美国:截止本周领取失业保险人群:季调", "续请失业金", "人", "周", "#855c9c", (0, 30_000_000)),
    "vacancy_rate": ("G003049462", "美国:职位空缺率:非农部门:季调:当月值", "职位空缺率", "%", "月", "#c94c4c", (0, 15)),
    "vacancy_count": ("G003049448", "美国:职位空缺数:非农部门:季调:当月值", "职位空缺数", "千人", "月", "#2f8a7a", (0, 20_000)),
    "unemployed_count": ("G002600531", "美国:失业人数:16岁及以上:季调:当月值", "失业人数", "千人", "月", "#855c9c", (0, 30_000)),
    "hire_rate": ("G003049504", "美国:雇佣率:非农部门:季调:当月值", "雇佣率", "%", "月", "#2f8a7a", (0, 15)),
    "quit_rate": ("G005316325", "美国:自愿性离职率:非农部门:季调:当月值", "自愿离职率", "%", "月", "#ba7a2e", (0, 10)),
    "payroll_total": ("G004786716", "美国:新增非农就业人数:当月值:季调", "非农就业", "千人", "月", "#17233b", (-30_000, 10_000)),
    "payroll_private": ("G004786717", "美国:新增非农就业人数:私营:当月值:季调", "私人非农就业", "千人", "月", "#1859b8", (-30_000, 10_000)),
    "payroll_goods": ("G002600512", "美国:新增非农就业人数:私营:生产:当月值:季调", "商品生产", "千人", "月", "#2f7fa3", (-10_000, 5_000)),
    "payroll_services": ("G004786762", "美国:新增非农就业人数:私营:服务:当月值:季调", "私人服务", "千人", "月", "#6b4a9e", (-30_000, 10_000)),
    "payroll_government": ("G002600520", "美国:新增非农就业人数:政府:当月值:季调", "政府", "千人", "月", "#ba7a2e", (-5_000, 5_000)),
    "sector_mining": ("G004786718", "美国:新增非农就业人数:私营:生产:采矿和伐木业:当月值:季调", "采矿与伐木", "千人", "月", "#6f7883", (-2_000, 2_000)),
    "sector_construction": ("G002600513", "美国:新增非农就业人数:私营:生产:建筑业:当月值:季调", "建筑业", "千人", "月", "#ba7a2e", (-3_000, 3_000)),
    "sector_manufacturing": ("G002600514", "美国:新增非农就业人数:私营:生产:制造业:当月值:季调", "制造业", "千人", "月", "#2f7fa3", (-5_000, 5_000)),
    "sector_retail": ("G002600516", "美国:新增非农就业人数:私营:服务:贸易、运输和公用事业:零售:当月值:季调", "零售业", "千人", "月", "#3c8b6d", (-5_000, 5_000)),
    "sector_transport": ("G004786785", "美国:新增非农就业人数:私营:服务:贸易、运输和公用事业:运输和仓储:当月值:季调", "运输仓储", "千人", "月", "#4f7398", (-5_000, 5_000)),
    "sector_information": ("G004786797", "美国:新增非农就业人数:私营:服务:信息咨询:当月值:季调", "信息业", "千人", "月", "#718295", (-3_000, 3_000)),
    "sector_financial": ("G004786804", "美国:新增非农就业人数:私营:服务:金融活动:当月值:季调", "金融活动", "千人", "月", "#855c9c", (-3_000, 3_000)),
    "sector_professional": ("G002600517", "美国:新增非农就业人数:私营:服务:专业和商业:当月值:季调", "专业商业服务", "千人", "月", "#6b4a9e", (-8_000, 8_000)),
    "sector_education_health": ("G002600518", "美国:新增非农就业人数:私营:服务:教育和保健:当月值:季调", "教育保健", "千人", "月", "#c94c4c", (-8_000, 8_000)),
    "wage_yoy": ("G005214653", "美国:平均时薪:非农就业员工:私营企业:季调:当月同比", "AHE平均时薪同比", "%", "月", "#c94c4c", (-5, 15)),
    "eci_wage_yoy": ("G005349364", "美国:劳动力成本指数:薪水报酬:当季同比", "ECI工资薪金同比", "%", "季", "#2f8a7a", (-5, 15)),
    "atlanta_wage": ("G012341449", "美国:亚特兰大联储薪资增长指数:3个月移动平均:当月值", "Atlanta Wage Tracker", "%", "月", "#1859b8", (-5, 20)),
    "weekly_hours": ("G005214514", "美国:平均每周工时:非农就业员工:私营企业:季调:当月值", "私人部门周工时", "小时", "月", "#1859b8", (20, 50)),
    "manufacturing_hours": ("G005214518", "美国:平均每周工时:非农就业员工:私营企业:生产:制造业:季调:当月值", "制造业周工时", "小时", "月", "#a56a12", (20, 55)),
    "temporary_help": ("G035586396", "美国:非农企业:就业人数:私营部门:服务生产:专业和商务服务:行政和支持服务以及废物管理和补救服务:临时帮助服务:季调:当月值", "临时工服务就业", "千人", "月", "#c94c4c", (0, 10_000)),
    "diffusion_1m": ("G003049534", "美国:就业扩散指数:私营企业:1个月跨度:季调:当月值", "1个月扩散指数", "%", "月", "#c94c4c", (0, 100)),
    "diffusion_3m": ("G003049535", "美国:就业扩散指数:私营企业:3个月跨度:季调:当月值", "3个月扩散指数", "%", "月", "#1859b8", (0, 100)),
    "adp_private_change": ("G039125311", "美国:ADP新增私营就业人数:当月值", "ADP私人就业", "人", "月", "#c94c4c", (-10_000_000, 10_000_000)),
    "u_star": ("G004427710", "(停)美国:潜在GDP预测:自然失业率", "CBO自然失业率 u*", "%", "季", "#c94c4c", (0, 15)),
    "real_gdp_yoy": ("G005130585", "美国:GDP:不变价:支出法:当季同比", "实际GDP同比", "%", "季", "#1859b8", (-40, 40)),
}

SECTOR_KEYS = [
    "sector_mining", "sector_construction", "sector_manufacturing", "sector_retail",
    "sector_transport", "sector_information", "sector_financial", "sector_professional",
    "sector_education_health",
]


def compact_date(value: Any) -> str:
    normalized = str(value).replace("-", "").replace("/", "").replace(".", "")
    if len(normalized) == 6:
        return f"{int(normalized[:4]):04d}{int(normalized[4:6]):02d}01"
    if len(normalized) >= 8:
        return normalized[:8]
    raise ValueError(f"invalid observation date: {value!r}")


def detect_missing_months(dates: Iterable[str]) -> list[str]:
    periods = sorted({compact_date(date)[:6] for date in dates})
    if not periods:
        return []
    year, month = int(periods[0][:4]), int(periods[0][4:6])
    end_year, end_month = int(periods[-1][:4]), int(periods[-1][4:6])
    expected: list[str] = []
    while (year, month) <= (end_year, end_month):
        expected.append(f"{year:04d}{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return [period for period in expected if period not in periods]


def rolling_mean(dates: list[str], values: list[float], window: int) -> tuple[list[str], list[float]]:
    if window < 1:
        raise ValueError("window must be positive")
    rows = [
        (dates[index], statistics.fmean(values[index - window + 1:index + 1]))
        for index in range(window - 1, len(values))
    ]
    return [row[0] for row in rows], [row[1] for row in rows]


def align_by_period(
    series_map: dict[str, tuple[list[str], list[float]]],
) -> tuple[list[str], dict[str, list[float]]]:
    """Align monthly series on their common YYYYMM periods."""
    if not series_map:
        return [], {}
    value_maps = {
        key: {compact_date(date)[:6]: value for date, value in zip(dates, values)}
        for key, (dates, values) in series_map.items()
    }
    periods = sorted(set.intersection(*(set(values) for values in value_maps.values())))
    return periods, {
        key: [value_map[period] for period in periods]
        for key, value_map in value_maps.items()
    }


def rebase_series(
    dates: list[str], values: list[float], base_period: str,
) -> tuple[list[str], list[float]]:
    """Rebase a series to 100 at the requested YYYYMM period."""
    base = next((value for date, value in zip(dates, values) if compact_date(date)[:6] == base_period), None)
    if base is None:
        raise ValueError(f"base period {base_period} is unavailable")
    if base == 0:
        raise ValueError("cannot rebase on zero")
    return list(dates), [round(value / base * 100, 8) for value in values]


def sahm_rule(dates: list[str], unemployment: list[float]) -> tuple[list[str], list[float]]:
    """Compute the Sahm indicator from monthly U3 unemployment rates."""
    ma_dates, ma_values = rolling_mean(dates, unemployment, 3)
    rows = []
    for index, value in enumerate(ma_values):
        trailing = ma_values[max(0, index - 11):index + 1]
        rows.append((ma_dates[index], value - min(trailing)))
    return [date for date, _value in rows], [value for _date, value in rows]


def fetch_response_series(payload: dict[str, Any], display_id: str) -> tuple[list[str], list[float]]:
    if payload.get("code") != 1:
        raise ValueError(f"iFinD rejected {display_id}: {payload.get('msg') or payload.get('code')}")
    tables = (payload.get("data") or {}).get("tables") or []
    table = next((item for item in tables if str(item.get("displayid") or "") == display_id), None)
    if table is None:
        raise ValueError(f"iFinD returned no data block for {display_id}")
    rows = [
        (compact_date(date), float(value))
        for date, value in zip(table.get("time") or [], table.get("value") or [])
        if value not in (None, "", "--", "#N/A")
    ]
    rows.sort(key=lambda item: item[0])
    if not rows:
        raise ValueError(f"iFinD returned no observations for {display_id}")
    return [row[0] for row in rows], [row[1] for row in rows]


def _candidate_log_dirs() -> Iterable[Path]:
    import os
    if os.environ.get("IFIND_LOG_DIR"):
        yield Path(os.environ["IFIND_LOG_DIR"])
    for drive in string.ascii_uppercase:
        root = Path(f"{drive}:\\")
        try:
            if not root.is_dir():
                continue
        except OSError:
            continue
        for parent in (root, root / "Program Files", root / "Program Files (x86)"):
            try:
                if not parent.is_dir():
                    continue
                for child in parent.iterdir():
                    if "ifind" in child.name.lower() and (child / "logs").is_dir():
                        yield child / "logs"
            except (OSError, PermissionError):
                continue


def read_token() -> tuple[str, Path]:
    for log_dir in _candidate_log_dirs():
        try:
            logs = sorted(log_dir.glob("socketclient_*.xlog"), key=lambda path: path.stat().st_mtime, reverse=True)
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


def request_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": USER_AGENT,
        "Referer": REFERER,
        "Origin": "https://ft.51ifind.com",
        "Cookie": f"jgbsessid={token}",
    }


def search_indicator(token: str, keyword: str) -> list[dict[str, Any]]:
    url = SEARCH_URL + "?" + urllib.parse.urlencode({"keyword": keyword})
    request = urllib.request.Request(url, headers=request_headers(token))
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 1:
        raise ValueError(f"iFinD search rejected {keyword}: {payload.get('msg')}")
    return payload.get("data") or []


def fetch_indicator(token: str, display_id: str, start: str, end: str) -> dict[str, Any]:
    form = urllib.parse.urlencode({
        "zb_str": _CODE_PREFIX.sub("", display_id) or display_id,
        "displayid": display_id,
        "zb_rtime": "0",
        "formula": "0",
        "wt": "json",
        "usage": "macro",
        "sdate": start.replace("-", ""),
        "edate": end.replace("-", ""),
    }).encode()
    request = urllib.request.Request(
        FETCH_URL,
        data=form,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", **request_headers(token)},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all(token: str) -> dict[str, dict[str, Any]]:
    end = datetime.now(timezone.utc).date().isoformat()
    result: dict[str, dict[str, Any]] = {}
    for key, spec in SERIES_SPEC.items():
        code, exact_name, _label, expected_unit, expected_frequency, _color, _bounds = spec
        candidates = search_indicator(token, exact_name)
        metadata = next((item for item in candidates if item.get("displayid") == code), None)
        if metadata is None:
            raise ValueError(f"iFinD metadata mismatch: {key} {code} not found for {exact_name}")
        if metadata.get("name") != exact_name or metadata.get("unit") != expected_unit or metadata.get("frequency") != expected_frequency:
            raise ValueError(f"iFinD identity mismatch for {key}: {metadata}")
        payload = fetch_indicator(token, code, START_DATE, end)
        dates, values = fetch_response_series(payload, code)
        lower, upper = _bounds
        if not all(lower <= value <= upper for value in values):
            minimum, maximum = min(values), max(values)
            raise ValueError(f"iFinD range check failed for {key}: [{minimum}, {maximum}] outside [{lower}, {upper}]")
        result[key] = {"metadata": metadata, "payload": payload}
        print(f"verified {key}: {code} {dates[0]}..{dates[-1]} ({len(dates)})")
    return result


SOURCE_INSTITUTION = {
    "initial_claims": "圣路易斯联储",
    "continuing_claims": "圣路易斯联储",
    "atlanta_wage": "亚特兰大联储",
    "adp_private_change": "ADP研究所",
    "u_star": "美国国会预算办公室",
    "real_gdp_yoy": "美国经济分析局",
}


def source_meta(key: str, latest: str, *, raw_unit: str | None = None) -> dict[str, Any]:
    code, name, _label, unit, _frequency, _color, _bounds = SERIES_SPEC[key]
    return {
        "provider": "iFinD EDB",
        "institution": SOURCE_INSTITUTION.get(key, "美国劳工局"),
        "code": code,
        "name": name,
        "rawUnit": raw_unit or unit,
        "url": "https://ft.51ifind.com",
        "latestObservation": latest,
    }


def make_series(
    key: str,
    dates: list[str],
    values: list[float],
    *,
    series_id: str | None = None,
    label: str | None = None,
    color: str | None = None,
    frequency: str | None = None,
    raw_unit: str | None = None,
    transform_label: str | None = None,
) -> dict[str, Any]:
    _code, _name, default_label, _unit, default_frequency, default_color, _bounds = SERIES_SPEC[key]
    item = {
        "id": series_id or key,
        "label": label or default_label,
        "dates": dates,
        "values": [round(value, 4) for value in values],
        "color": color or default_color,
        "frequency": frequency or default_frequency,
        "latestObservation": dates[-1],
        "latestValue": round(values[-1], 4),
        "source": source_meta(key, dates[-1], raw_unit=raw_unit),
    }
    if transform_label:
        item["transformLabel"] = transform_label
    return item


def chart(
    chart_id: str,
    title: str,
    description: str,
    unit: str,
    series: list[dict[str, Any]],
    *,
    eyebrow: str,
    explanation: dict[str, str],
    kind: str = "line",
    default_range: str = "5Y",
    reference: float | None = None,
    total_series: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": chart_id,
        "kind": kind,
        "eyebrow": eyebrow,
        "title": title,
        "description": description,
        "unit": unit,
        "defaultRange": default_range,
        "series": series,
        "explanation": explanation,
    }
    if reference is not None:
        result["reference"] = reference
    if total_series is not None:
        result["totalSeries"] = total_series
    return result


def explanation(what: str, how_to_read: str, caveat: str, slide: int) -> dict[str, str]:
    return {
        "what": what,
        "howToRead": how_to_read,
        "caveat": caveat,
        "pptSlide": f"PPT p.{slide}",
    }


def _build_dataset_v1(raw: dict[str, dict[str, Any]], generated_at: str, raw_snapshot: str) -> dict[str, Any]:
    parsed = {
        key: fetch_response_series(item["payload"], SERIES_SPEC[key][0])
        for key, item in raw.items()
    }

    initial_dates, initial_values = parsed["initial_claims"]
    continuing_dates, continuing_values = parsed["continuing_claims"]
    initial_values_10k = [value / 10_000 for value in initial_values]
    continuing_values_10k = [value / 10_000 for value in continuing_values]
    initial_ma_dates, initial_ma_values = rolling_mean(initial_dates, initial_values_10k, 4)
    continuing_ma_dates, continuing_ma_values = rolling_mean(continuing_dates, continuing_values_10k, 4)

    participation = chart(
        "participation", "劳动参与率：总量与壮年", "总参与率受老龄化影响；25—54岁参与率更接近周期性劳动力供给。", "%",
        [make_series(key, *parsed[key]) for key in ("participation_total", "participation_prime")],
        eyebrow="SUPPLY · PARTICIPATION",
    )
    unemployment = chart(
        "unemployment", "U3与U6失业率", "U6将边缘劳动力与因经济原因兼职者纳入，可识别U3未覆盖的松弛。", "%",
        [make_series(key, *parsed[key]) for key in ("u3", "u6")],
        eyebrow="SLACK · UNEMPLOYMENT",
    )
    composition = chart(
        "unemployment-composition", "失业性质：暂时性与永久性", "永久性失业通常比暂时性解雇更能提示再就业摩擦与需求转弱。", "千人",
        [make_series(key, *parsed[key]) for key in ("temporary_unemployed", "permanent_unemployed")],
        eyebrow="SLACK · COMPOSITION",
    )
    claims = chart(
        "claims", "初请与续请失业金人数", "初请捕捉新增裁员，续请更接近再就业速度；两者均展示4周移动平均，并以分面独立刻度避免量级差掩盖初请变化。", "万人",
        [
            make_series("initial_claims", initial_ma_dates, initial_ma_values, series_id="initial_claims_4w", label="初请4周均值", raw_unit="人", transform_label="iFinD原值÷10,000后计算4周均值"),
            make_series("continuing_claims", continuing_ma_dates, continuing_ma_values, series_id="continuing_claims_4w", label="续请4周均值", color="#855c9c", raw_unit="人", transform_label="iFinD原值÷10,000后计算4周均值"),
        ],
        eyebrow="SLACK · WEEKLY CLAIMS", default_range="3Y",
    )
    claims["separateScale"] = True
    duration = chart(
        "unemployment-duration", "失业持续时间", "平均数受长尾影响更大，中位数更贴近典型失业者；两者同步抬升才是更广泛的恶化。", "周",
        [make_series(key, *parsed[key]) for key in ("duration_median", "duration_average")],
        eyebrow="SLACK · DURATION",
    )

    u3_map = {date[:6]: value for date, value in zip(*parsed["u3"])}
    vacancy_map = {date[:6]: value for date, value in zip(*parsed["vacancy_rate"])}
    common_periods = sorted(set(u3_map) & set(vacancy_map))
    beveridge = {
        "id": "beveridge", "kind": "scatter", "eyebrow": "SLACK · BEVERIDGE CURVE",
        "title": "贝弗里奇曲线", "description": "横轴U3失业率、纵轴职位空缺率；曲线外移可能意味着匹配效率下降，不能仅以需求强弱解释。",
        "unit": "%", "defaultRange": "ALL",
        "xSource": source_meta("u3", parsed["u3"][0][-1]),
        "ySource": source_meta("vacancy_rate", parsed["vacancy_rate"][0][-1]),
        "points": [{"period": period, "x": u3_map[period], "y": vacancy_map[period]} for period in common_periods],
    }

    payroll_components = [make_series(key, *parsed[key]) for key in ("payroll_goods", "payroll_services", "payroll_government")]
    payroll_total = make_series("payroll_total", *parsed["payroll_total"])
    payroll_chart = chart(
        "payroll-composition", "非农新增就业构成", "商品生产、私人服务与政府就业堆叠；总非农折线保留BLS汇总口径。", "千人",
        payroll_components, eyebrow="DEMAND · PAYROLLS", kind="bar", default_range="3Y", reference=0, total_series=payroll_total,
    )
    jolts = chart(
        "jolts-rates", "JOLTS：空缺、雇佣与离职", "职位空缺率反映岗位需求，雇佣率反映实际匹配，自愿离职率反映劳动者议价与跳槽意愿。", "%",
        [make_series(key, *parsed[key]) for key in ("vacancy_rate", "hire_rate", "quit_rate")],
        eyebrow="DEMAND · JOLTS",
    )

    periods = list(dict.fromkeys(date[:6] for date in reversed(parsed["payroll_total"][0])))[:12]
    heatmap_rows = []
    for key in SECTOR_KEYS:
        dates, values = parsed[key]
        value_map = {date[:6]: value for date, value in zip(dates, values)}
        heatmap_rows.append({
            "id": key,
            "label": SERIES_SPEC[key][2],
            "values": [round(value_map[period], 2) if period in value_map else None for period in periods],
            "source": source_meta(key, dates[-1]),
        })

    earnings = chart(
        "average-hourly-earnings", "平均时薪同比", "私营非农就业员工平均时薪同比，是工资压力与服务通胀韧性的高频锚。", "%",
        [make_series("wage_yoy", *parsed["wage_yoy"])],
        eyebrow="WAGES · EARNINGS", reference=3.5,
    )
    hours = chart(
        "average-weekly-hours", "平均每周工时", "企业通常先调整工时、再调整人数；工时持续回落可能领先新增就业转弱。", "小时",
        [make_series("weekly_hours", *parsed["weekly_hours"])],
        eyebrow="WAGES · HOURS",
    )

    payroll_latest = payroll_total
    u3_latest = unemployment["series"][0]
    claims_latest = claims["series"][0]
    wage_latest = earnings["series"][0]
    monthly_missing = {
        key: detect_missing_months(dates)
        for key, (dates, _values) in parsed.items()
        if SERIES_SPEC[key][4] == "月"
    }

    return {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "source": "iFinD EDB",
        "sourceProviders": ["iFinD EDB"],
        "headline": [
            {"id": "payroll", "label": "就业增量", "title": "新增非农就业", "value": payroll_latest["latestValue"], "unit": "千人", "observation": payroll_latest["latestObservation"], "source": "iFinD EDB"},
            {"id": "unemployment", "label": "劳动力松弛", "title": "U3失业率", "value": u3_latest["latestValue"], "unit": "%", "observation": u3_latest["latestObservation"], "source": "iFinD EDB"},
            {"id": "claims", "label": "高频裁员", "title": "初请4周均值", "value": claims_latest["latestValue"], "unit": "万人", "observation": claims_latest["latestObservation"], "source": "iFinD EDB"},
            {"id": "wage", "label": "工资压力", "title": "平均时薪同比", "value": wage_latest["latestValue"], "unit": "%", "observation": wage_latest["latestObservation"], "source": "iFinD EDB"},
        ],
        "sections": {
            "supply": {
                "title": "劳动力供给",
                "description": "先区分人口结构驱动的总参与率与更具周期含义的壮年参与率。",
                "charts": [participation],
            },
            "slack": {
                "title": "失业与松弛",
                "description": "从失业率、失业性质、申领救济、失业时长与岗位匹配五个层次判断劳动力市场是否真正恶化。",
                "charts": [unemployment, composition, claims, duration, beveridge],
            },
            "demand": {
                "title": "劳动力需求",
                "description": "非农就业给出已实现的招聘，JOLTS给出岗位需求与匹配过程，行业热度表识别就业扩散或集中。",
                "charts": [payroll_chart, jolts],
                "sectorHeatmap": {
                    "title": "行业新增就业热度表",
                    "description": "九个主要行业最近12个可用月份的新增就业人数；红色为扩张、蓝色为收缩。",
                    "periods": periods,
                    "rows": heatmap_rows,
                    "source": {"provider": "iFinD EDB", "url": "https://ft.51ifind.com"},
                },
            },
            "wages": {
                "title": "工资与工时",
                "description": "工资反映劳动稀缺与通胀压力，工时常领先人数调整；两者必须联合阅读。",
                "charts": [earnings, hours],
            },
        },
        "dataQuality": {
            "monthlyMissingPeriods": monthly_missing,
            "note": "全部序列来自iFinD EDB；月度、周度与JOLTS序列保留各自观测日期，不共享统一截至日。",
        },
        "researchBasis": [
            "本页结构参考文件夹内就业研究Excel的劳动参与率—失业—申领救济—贝弗里奇曲线—非农分项—工资工时链条。",
            "PDF研报仅用于确定分析框架与图表组合；页面数值全部由iFinD EDB重取，不沿用研报截图数值。",
        ],
        "rawSnapshots": {"ifind": raw_snapshot},
    }


def build_dataset(raw: dict[str, dict[str, Any]], generated_at: str, raw_snapshot: str) -> dict[str, Any]:
    parsed = {
        key: fetch_response_series(item["payload"], SERIES_SPEC[key][0])
        for key, item in raw.items()
    }

    payroll_dates, payroll_values = parsed["payroll_total"]
    payroll_3m_dates, payroll_3m_values = rolling_mean(payroll_dates, payroll_values, 3)
    payroll_12m_dates, payroll_12m_values = rolling_mean(payroll_dates, payroll_values, 12)
    payroll_momentum = chart(
        "payroll-momentum", "新增非农：月度增量与3个月均值",
        "月度柱保留数据冲击，3个月均值提取中短期趋势；先看预期差，再看趋势，最后才与盈亏平衡增速比较。",
        "千人", [make_series("payroll_total", payroll_dates, payroll_values, label="月度增量")],
        eyebrow="CES · PAYROLL MOMENTUM", kind="bar", default_range="5Y", reference=0,
        total_series=make_series(
            "payroll_total", payroll_3m_dates, payroll_3m_values,
            series_id="payroll_total_3m", label="3个月均值", color="#111418",
            transform_label="由iFinD月度新增非农计算后向3个月移动平均",
        ),
        explanation=explanation(
            "CES企业调查统计工资单上的岗位，而不是就业人数；一人两职会被计为两个岗位。",
            "单月值用于事件交易，3个月均值用于判断就业动能是否持续；当前值还应结合失业率判断是否高于维持供需平衡的需要。",
            "非农初值随后两个月修正，并受年度QCEW基准修订和Birth-Death模型影响；疫情极值会压缩常态月份的可读性。",
            31,
        ),
    )

    industrial_periods, industrial_aligned = align_by_period({
        key: parsed[key] for key in ("sector_mining", "sector_construction", "sector_manufacturing")
    })
    industrial_values = [sum(values) for values in zip(*(industrial_aligned[key] for key in industrial_aligned))]
    industrial_dates = [f"{period}01" for period in industrial_periods]
    industrial_ma_dates, industrial_ma_values = rolling_mean(industrial_dates, industrial_values, 12)
    cyclical_industries = chart(
        "cyclical-industries", "周期敏感行业：工业就业与总非农",
        "采矿、建筑、制造业新增就业合计与总非农均取12个月移动平均，观察全球制造业和美国周期的共同拐点。",
        "千人", [
            make_series(
                "sector_mining", industrial_ma_dates, industrial_ma_values,
                series_id="industrial_payroll_12m", label="工业新增就业12月均值", color="#a56a12",
                transform_label="采矿与伐木+建筑+制造业新增就业之和，再计算12个月移动平均",
            ),
            make_series(
                "payroll_total", payroll_12m_dates, payroll_12m_values,
                series_id="payroll_total_12m", label="总非农12月均值", color="#1859b8",
                transform_label="新增非农后向12个月移动平均",
            ),
        ], eyebrow="CES · CYCLICAL EMPLOYMENT",
        explanation=explanation(
            "工业部门就业占比不高，但波动贡献和周期信息显著高于其体量。",
            "工业就业均值转正且持续，通常比教育医疗等结构性行业的增长更能确认周期复苏。",
            "12个月均值非常平滑，适合识别中期拐点，不适合判断最近一两个月的变化。",
            34,
        ),
    )
    temporary_help = chart(
        "temporary-help", "临时工服务就业",
        "企业面对需求变化时往往先调整临时工，再调整正式员工。",
        "千人", [make_series("temporary_help", *parsed["temporary_help"])],
        eyebrow="CES · TEMP HELP", default_range="ALL",
        explanation=explanation(
            "该序列统计临时帮助服务行业的工资单就业，不等于全经济所有临时合同工。",
            "需求转弱时临时工通常先被削减；持续止跌回升可作为正式招聘改善的早期线索。",
            "行业外包方式和派遣机构市场份额会改变序列，历史领先关系不是固定时钟。",
            34,
        ),
    )
    weekly_hours = chart(
        "weekly-hours", "周工时：强度边际领先数量边际",
        "解雇和重招有固定成本，企业通常先压缩工时、后裁员；制造业工时对周期更敏感。",
        "小时", [make_series(key, *parsed[key]) for key in ("manufacturing_hours", "weekly_hours")],
        eyebrow="CES · HOURS", default_range="ALL",
        explanation=explanation(
            "平均周工时衡量每名员工的劳动投入强度；工时×就业人数近似总工时投入。",
            "周工时跌破前低而非农仍为正，常对应需求走弱但企业惜裁；制造业工时更适合看长周期。",
            "两条线水平不同，不能只比视觉高度；行业构成变化也会影响平均值。",
            35,
        ),
    )
    diffusion = chart(
        "employment-diffusion", "就业扩散指数：增长的广度",
        "扩散指数衡量多少行业在增员，而不是新增就业的绝对强度。",
        "%", [make_series(key, *parsed[key]) for key in ("diffusion_1m", "diffusion_3m")],
        eyebrow="CES · BREADTH", default_range="ALL", reference=50,
        explanation=explanation(
            "指数等于就业增加行业占比加上就业不变行业占比的一半；50表示增减行业数量大致相当。",
            "总非农强但扩散指数低，说明增长集中在少数行业；3个月版本更平滑。",
            "广度不等于幅度，多数行业小幅增员与少数行业大幅增员可能给出相反叙事。",
            33,
        ),
    )
    hours_and_ces = [payroll_momentum, cyclical_industries, temporary_help, weekly_hours, diffusion]

    u_spectrum = chart(
        "u-spectrum", "U1—U6失业谱系",
        "从长期失业到广义就业不足逐层放宽口径；水平同涨同落，层距变化才是新增信息。",
        "%", [make_series(key, *parsed[key]) for key in ("u1", "u3", "u4", "u5", "u6")],
        eyebrow="CPS · U1—U6", default_range="ALL",
        explanation=explanation(
            "U3是官方失业率；U4/U5加入灰心者与边缘依附者；U6再加入因经济原因兼职者。",
            "重点观察U6−U3是否走阔，以及U1是否在低失业率环境下持续抬升。",
            "各口径分母并不完全相同，层距是就业不足代理，不应直接解释成隐性失业人数。",
            41,
        ),
    )
    long_term = chart(
        "long-term-unemployment", "失业率与长期失业占比",
        "低失业率与27周以上失业占比上行并存，是低招聘、低流动的冻结市场信号。",
        "%", [make_series(key, *parsed[key]) for key in ("u3", "longterm_share")],
        eyebrow="CPS · DURATION QUALITY",
        explanation=explanation(
            "长期失业占比以全部失业者为分母，描述失业者中有多少人已经失业至少27周。",
            "U3稳定但长期失业占比上升，意味着失业者不多、但一旦失业更难重新上岗。",
            "经济冲击初期大量短期失业者涌入会机械压低长期失业占比，必须与U3联合读。",
            41,
        ),
    )
    long_term["separateScale"] = True
    participation = chart(
        "participation", "劳动参与率：总量与黄金年龄",
        "16岁以上总参与率受老龄化拖累，25—54岁黄金年龄参与率更接近周期性劳动力供给。",
        "%", [make_series(key, *parsed[key]) for key in ("participation_total", "participation_prime")],
        eyebrow="CPS · PARTICIPATION",
        explanation=explanation(
            "参与率等于劳动力人口除以16岁以上居民非机构人口；劳动力=就业者+主动求职的失业者。",
            "判断周期优先看25—54岁；总参与率长期下降不能直接等同于劳动力市场恶化。",
            "退出求职会同时降低失业人数和劳动力分母，可能造成失业率的退出型改善。",
            42,
        ),
    )
    participation["separateScale"] = True
    race = chart(
        "race-unemployment", "分人种失业率：周期敏感度",
        "黑人失业率长期高于白人且周期弹性更大，可作为劳动力市场边际恶化的煤矿金丝雀。",
        "%", [make_series(key, *parsed[key]) for key in ("unemployment_black", "unemployment_hispanic", "u3", "unemployment_white")],
        eyebrow="CPS · DEMOGRAPHICS", default_range="ALL",
        explanation=explanation(
            "各人群失业率均以本组劳动力人口为分母，不是该组人口中的失业占比。",
            "观察黑人失业率是否先于总体拐头，以及不同人群的差距是否在衰退前扩大。",
            "人群样本小于总样本，月度噪音更大；结构差异不能直接归因于单一宏观冲击。",
            43,
        ),
    )
    age_sex = chart(
        "age-sex-unemployment", "年龄与性别失业率",
        "16—19岁是周期放大器；25—54岁性别差更多取决于本轮受冲击行业的构成。",
        "%", [make_series(key, *parsed[key]) for key in (
            "unemployment_teen", "unemployment_young", "unemployment_prime",
            "unemployment_prime_male", "unemployment_prime_female",
        )], eyebrow="CPS · AGE & SEX",
        explanation=explanation(
            "年轻人因技能、年资和岗位稳定性较低，失业率水平更高、对冲击反应更大。",
            "先看年轻人是否领先恶化，再比较25—54岁男女差异判断行业冲击偏向制造建筑还是服务业。",
            "年轻人与黄金年龄失业率量级差异大，阅读时宜用序列开关而不是直接比较线条高度。",
            44,
        ),
    )
    ces_rebased_dates, ces_rebased_values = rebase_series(*parsed["ces_employment"], "202112")
    cps_rebased_dates, cps_rebased_values = rebase_series(*parsed["cps_employment"], "202112")
    survey_divergence = chart(
        "survey-divergence", "CES与CPS就业：两调查背离",
        "把CES岗位数与CPS就业人数均重定基为2021-12=100，只比较累计路径，不混淆绝对规模。",
        "指数", [
            make_series("ces_employment", ces_rebased_dates, ces_rebased_values, label="CES企业调查", transform_label="2021-12=100"),
            make_series("cps_employment", cps_rebased_dates, cps_rebased_values, label="CPS家庭调查", transform_label="2021-12=100"),
        ], eyebrow="CES vs CPS · REBASED", default_range="5Y",
        explanation=explanation(
            "CES数岗位，CPS数人；多重职业者、自雇覆盖与人口控制差异会造成持续背离。",
            "比较重定基后的累计增幅，而不是把指数点差直接当作就业人数差。",
            "每年1月CPS人口控制可能制造机械跳变；本图未做BLS的payroll-compatible口径调整。",
            45,
        ),
    )
    official_charts = hours_and_ces + [u_spectrum, long_term, participation, race, age_sex, survey_divergence]

    initial_dates, initial_values = parsed["initial_claims"]
    continuing_dates, continuing_values = parsed["continuing_claims"]
    initial_ma_dates, initial_ma_values = rolling_mean(initial_dates, [value / 10_000 for value in initial_values], 4)
    continuing_ma_dates, continuing_ma_values = rolling_mean(continuing_dates, [value / 10_000 for value in continuing_values], 4)
    claims = chart(
        "claims", "初请与续请失业金人数",
        "初请反映新增裁员，续请反映再就业难度；均使用4周移动平均过滤车厂停工、假日周和单州异动。",
        "万人", [
            make_series("initial_claims", initial_ma_dates, initial_ma_values, series_id="initial_claims_4w", label="初请4周均值", raw_unit="人", transform_label="原值÷10000后计算4周均值"),
            make_series("continuing_claims", continuing_ma_dates, continuing_ma_values, series_id="continuing_claims_4w", label="续请4周均值", raw_unit="人", transform_label="原值÷10000后计算4周均值"),
        ], eyebrow="WEEKLY · CLAIMS", default_range="3Y",
        explanation=explanation(
            "失业保险行政记录接近普查，是周频官方硬数据；初请是解雇流量，续请兼含再就业速度。",
            "初请拐头向上通常领先就业恶化；初请稳定但续请上升，更像招聘冻结而非裁员潮。",
            "初请与续请统计参考周不同，不能把同一发布日期当作同一周数据；疫情特殊项目也改变过覆盖。",
            48,
        ),
    )
    claims["separateScale"] = True

    vu_periods, vu_aligned = align_by_period({
        "vacancy": parsed["vacancy_count"], "unemployed": parsed["unemployed_count"],
    })
    vu_values = [vacancy / unemployed if unemployed else 0.0 for vacancy, unemployed in zip(vu_aligned["vacancy"], vu_aligned["unemployed"])]
    vu_dates = [f"{period}01" for period in vu_periods]
    vu_wage = chart(
        "vu-wage", "V/U与ECI工资压力",
        "职位空缺数/失业人数是供需紧度核心代理，PPT将其视为领先ECI工资增速约2—4个季度的上游变量。",
        "% / 倍", [
            make_series("vacancy_count", vu_dates, vu_values, series_id="vacancy_unemployment_ratio", label="V/U", color="#1859b8", transform_label=f"{SERIES_SPEC['vacancy_count'][0]}÷{SERIES_SPEC['unemployed_count'][0]}"),
            make_series("eci_wage_yoy", *parsed["eci_wage_yoy"]),
        ], eyebrow="JOLTS · V/U → WAGES", default_range="ALL",
        explanation=explanation(
            "V/U表示每名失业者对应多少职位空缺；ECI固定职业权重，较少受行业构成变化影响。",
            "V/U接近1意味着岗位与求职者数量大体平衡；持续下降通常领先工资压力缓解。",
            "JOLTS发布滞后且回复率下降；V/U=1只是经验标尺，不是机械的通胀目标条件。",
            49,
        ),
    )
    vu_wage["separateScale"] = True
    jolts = chart(
        "jolts-rates", "JOLTS流量：空缺、雇佣与离职",
        "空缺率是岗位需求，雇佣率是实际匹配，自愿离职率反映劳动者议价与跳槽意愿。",
        "%", [make_series(key, *parsed[key]) for key in ("vacancy_rate", "hire_rate", "quit_rate")],
        eyebrow="JOLTS · FLOWS",
        explanation=explanation(
            "存量岗位背后每月有大规模雇佣、辞职和解雇流量；低招聘、低辞职、低解雇是冻结而非强劲。",
            "空缺率下降而雇佣率不回升，说明岗位广告减少但匹配效率未改善。",
            "JOLTS滞后约两个月，发布时当月非农已经公布，不能把它当成最新就业读数。",
            49,
        ),
    )

    wage_three = chart(
        "wage-three-measures", "工资三口径：AHE、ECI与Atlanta Wage Tracker",
        "AHE最快，ECI最适合确认，Atlanta同人同比更接近劳动者实际工资变化。",
        "%", [make_series(key, *parsed[key]) for key in ("wage_yoy", "eci_wage_yoy", "atlanta_wage")],
        eyebrow="WAGES · THREE MEASURES", default_range="ALL",
        explanation=explanation(
            "AHE是总工资除以总工时；ECI固定职业权重并含更稳定的构成；Atlanta Tracker跟踪同一人的工资同比中位数。",
            "月度跟踪先看AHE，季度确认看ECI，判断跳槽/留任溢价和个体工资体验看Atlanta。",
            "AHE有严重构成偏差，ECI频率低，Atlanta为3个月移动平均且覆盖口径不同，三者不能逐月机械对齐。",
            50,
        ),
    )

    def quarter_key(date: str) -> str:
        month = int(date[4:6])
        return f"{date[:4]}Q{(month - 1) // 3 + 1}"

    unemployment_quarters: dict[str, list[float]] = {}
    for date, value in zip(*parsed["u3"]):
        unemployment_quarters.setdefault(quarter_key(date), []).append(value)
    unemployment_quarter_avg = {period: statistics.fmean(values) for period, values in unemployment_quarters.items()}
    gdp_map = {quarter_key(date): value for date, value in zip(*parsed["real_gdp_yoy"])}
    common_quarters = sorted(set(unemployment_quarter_avg) & set(gdp_map))
    okun_points = []
    for index, period in enumerate(common_quarters):
        if index == 0:
            continue
        previous = common_quarters[index - 1]
        delta_u = unemployment_quarter_avg[period] - unemployment_quarter_avg[previous]
        okun_points.append({
            "period": period, "x": round(gdp_map[period], 4), "y": round(delta_u, 4),
            "group": "extreme" if period[:4] in ("2020", "2021") else "history",
        })
    regression_points = [point for point in okun_points if point["group"] == "history"]
    x_mean = statistics.fmean(point["x"] for point in regression_points)
    y_mean = statistics.fmean(point["y"] for point in regression_points)
    denominator = sum((point["x"] - x_mean) ** 2 for point in regression_points)
    slope = sum((point["x"] - x_mean) * (point["y"] - y_mean) for point in regression_points) / denominator
    intercept = y_mean - slope * x_mean
    okun = {
        "id": "okun", "kind": "scatter", "eyebrow": "FRAMEWORK · OKUN",
        "title": "Okun定律", "description": "实际GDP同比与失业率季度变化的经验负相关；2020—21极端值单独标记。",
        "unit": "% / 百分点", "defaultRange": "ALL", "points": okun_points,
        "xLabel": "实际GDP同比（%）", "yLabel": "失业率季度变化（百分点）",
        "regression": {"slope": round(slope, 4), "intercept": round(intercept, 4), "excludeGroup": "extreme"},
        "xSource": source_meta("real_gdp_yoy", parsed["real_gdp_yoy"][0][-1]),
        "ySource": source_meta("u3", parsed["u3"][0][-1]),
        "explanation": explanation(
            "Okun定律把产出增长与失业率变化联系起来，是经验汇率而非会计恒等式。",
            "增长越高，点通常越靠右下；回归斜率用于口算增长变化对应的失业率变化。",
            "系数随参与率、生产率和冲击性质漂移；2020—21停摆重启样本不应支配常态回归。",
            51,
        ),
    }
    unemployment_gap = chart(
        "unemployment-gap", "失业缺口 u−u*",
        "实际U3与CBO自然失业率并列；二者垂直距离是失业缺口。",
        "%", [make_series(key, *parsed[key]) for key in ("u3", "u_star")],
        eyebrow="FRAMEWORK · UNEMPLOYMENT GAP", default_range="ALL",
        explanation=explanation(
            "u*是与稳定通胀大致相容的自然失业率，不可观测，只能由模型估计。",
            "U3低于u*通常被读作劳动力市场偏热，高于u*则代表闲置；重点看方向而非小数点。",
            "iFinD中该CBO序列标记为停更/预测历史混合，且u*会被事后大幅修订，严禁当作实时真值。",
            52,
        ),
    )
    u3_map = {date[:6]: value for date, value in zip(*parsed["u3"])}
    vacancy_rate_map = {date[:6]: value for date, value in zip(*parsed["vacancy_rate"])}
    beveridge_periods = sorted(set(u3_map) & set(vacancy_rate_map))
    beveridge_points = []
    for period in beveridge_periods:
        year = int(period[:4])
        group = "history" if year <= 2019 else "mismatch" if year <= 2021 else "soft-landing" if year <= 2024 else "current"
        beveridge_points.append({"period": period, "x": u3_map[period], "y": vacancy_rate_map[period], "group": group})
    beveridge = {
        "id": "beveridge", "kind": "scatter", "eyebrow": "FRAMEWORK · BEVERIDGE",
        "title": "贝弗里奇曲线", "description": "按2001—19、疫情错配、2022—24软着陆和2025年至今分段，观察空缺率回落是否必须以失业率大升为代价。",
        "unit": "%", "defaultRange": "ALL", "points": beveridge_points,
        "xLabel": "失业率（%）", "yLabel": "职位空缺率（%）", "balanceLine": "V/U=1",
        "xSource": source_meta("u3", parsed["u3"][0][-1]),
        "ySource": source_meta("vacancy_rate", parsed["vacancy_rate"][0][-1]),
        "explanation": explanation(
            "贝弗里奇曲线描述职位空缺率与失业率的负相关；曲线外移通常代表匹配效率下降。",
            "2022—24若轨迹近乎垂直向下，意味着空缺减少而失业率少升，是软着陆证据；V/U=1是供需平衡线。",
            "曲线位置会随匹配效率、行业错配和劳动力供给变化移动，不能把历史曲线当成固定政策菜单。",
            53,
        ),
    }
    sahm_dates, sahm_values = sahm_rule(*parsed["u3"])
    sahm = chart(
        "sahm", "Sahm规则",
        "失业率3个月均值相对过去12个月低点的升幅；0.5个百分点为经验触发线。",
        "百分点", [make_series("u3", sahm_dates, sahm_values, series_id="sahm_rule", label="Sahm指标", transform_label="U3三个月均值减过去12个月三个月均值低点")],
        eyebrow="FRAMEWORK · SAHM", default_range="ALL", reference=0.5,
        explanation=explanation(
            "Sahm规则用于实时识别衰退，不是因果模型；历史上触发常与NBER衰退重合。",
            "指标越过0.5意味着失业率上升速度异常，需立即拆解裁员与劳动力供给驱动。",
            "2024年曾因移民扩张带来的分母效应触发但衰退未至，证明经验规则会在结构变化时误报。",
            54,
        ),
    )

    adp_dates, adp_values_raw = parsed["adp_private_change"]
    adp_values = [value / 1000 for value in adp_values_raw]
    adp_3m_dates, adp_3m_values = rolling_mean(adp_dates, adp_values, 3)
    private_dates, private_values = parsed["payroll_private"]
    private_3m_dates, private_3m_values = rolling_mean(private_dates, private_values, 3)
    adp_trend = chart(
        "adp-trend", "ADP与私人非农：趋势的第二意见",
        "两者都取3个月均值；ADP是真实工资单记录，但方法论不再以拟合非农为目标。",
        "千人", [
            make_series("payroll_private", private_3m_dates, private_3m_values, series_id="private_payroll_3m", label="私人非农3个月均值", transform_label="后向3个月均值"),
            make_series("adp_private_change", adp_3m_dates, adp_3m_values, series_id="adp_3m", label="ADP 3个月均值", raw_unit="人", transform_label="原值÷1000后计算3个月均值"),
        ], eyebrow="CROSS-CHECK · ADP", default_range="5Y",
        explanation=explanation(
            "ADP覆盖真实工资单、只含私人部门；CES是抽样调查并含Birth-Death外推。",
            "持续趋势背离可作为CES高估或低估的警报，尤其在非农质量下降或政府停摆时。",
            "逐月相关性弱，ADP不适合拿来精确预测当月非农；两者口径也不完全相同。",
            55,
        ),
    )
    adp_periods, adp_aligned = align_by_period({
        "adp": (adp_dates, adp_values), "private": parsed["payroll_private"],
    })
    adp_points = [
        {"period": period, "x": adp, "y": private, "group": "history"}
        for period, adp, private in zip(adp_periods, adp_aligned["adp"], adp_aligned["private"])
        if period >= "202301"
    ]
    adp_scatter = {
        "id": "adp-scatter", "kind": "scatter", "eyebrow": "CROSS-CHECK · MONTHLY FIT",
        "title": "ADP能否预测私人非农", "description": "逐月散点与45度线检验幅度和方向是否一致。",
        "unit": "千人", "defaultRange": "ALL", "points": adp_points,
        "xLabel": "ADP月增（千人）", "yLabel": "私人非农月增（千人）", "equalityLine": True,
        "xSource": source_meta("adp_private_change", adp_dates[-1], raw_unit="人"),
        "ySource": source_meta("payroll_private", private_dates[-1]),
        "explanation": explanation(
            "每个点是一月；45度线代表ADP与私人非农完全相同。",
            "点云越贴近45度线，单月预测力越强；跨象限表示两者连增减方向都相反。",
            "相关性随样本窗口变化，不能把回顾期拟合当成稳定的前瞻关系。",
            55,
        ),
    }

    sector_periods = list(dict.fromkeys(date[:6] for date in reversed(payroll_dates)))[:12]
    sector_rows = []
    for key in SECTOR_KEYS:
        dates, values = parsed[key]
        value_map = {date[:6]: value for date, value in zip(dates, values)}
        recent = [value_map[period] for period in sector_periods if period in value_map]
        baseline = [value for date, value in zip(dates, values) if "201801" <= date[:6] <= "201912"]
        sector_rows.append({
            "id": key, "label": SERIES_SPEC[key][2],
            "values": [round(value_map[period], 2) if period in value_map else None for period in sector_periods],
            "recent12mAverage": round(statistics.fmean(recent), 2),
            "baseline2018To2019": round(statistics.fmean(baseline), 2),
            "source": source_meta(key, dates[-1]),
        })

    route_map = [
        {"id": "official-surveys", "title": "官方双调查", "subtitle": "每月第一个周五", "nodes": [
            {"title": "CES 企业调查：非农增量·工时·时薪", "detail": "数岗位，有修正"},
            {"title": "CPS 家庭调查：失业率·参与率·U1—U6", "detail": "数人，比率相对可靠"},
        ]},
        {"id": "flows-weekly", "title": "流量与周频", "subtitle": "存量背后的进出", "nodes": [
            {"title": "JOLTS：重点看V/U紧度", "detail": "工资压力上游，发布滞后"},
            {"title": "初请/续请：唯一周频官方硬数据", "detail": "初请看解雇，续请看再就业"},
        ]},
        {"id": "wage-measures", "title": "工资三口径", "subtitle": "快、准与同人跟踪", "nodes": [
            {"title": "AHE：月频最快", "detail": "有构成偏差"},
            {"title": "ECI：季度固定职业权重", "detail": "联储正式参照"},
            {"title": "Atlanta Wage Tracker：同人同比", "detail": "区分个体工资体验"},
        ]},
        {"id": "empirical-frameworks", "title": "四大经验框架", "subtitle": "学完数据再用", "nodes": [
            {"title": "Okun 定律", "detail": "增长与失业的经验汇率"},
            {"title": "失业缺口 u−u*", "detail": "概念重要，u*估不准"},
            {"title": "贝弗里奇曲线", "detail": "空缺与失业，软着陆主战场"},
            {"title": "Sahm 规则", "detail": "衰退触发器，2024首次误报"},
        ]},
        {"id": "cross-checks", "title": "第三方交叉验证", "subtitle": "第二意见而非真值", "nodes": [
            {"title": "ADP：独立样本的第二意见", "detail": "不能机械预测非农"},
            {"title": "Challenger·Indeed·NFIB", "detail": "裁员意愿、职位与招聘计划"},
            {"title": "WARN 裁员预告", "detail": "领先性最强，州口径不一"},
        ]},
    ]
    data_passports = [
        {"id": "ces", "title": "CES企业调查", "producer": "BLS", "sample": "约12.1万家企业、63万个工作地点；数岗位，不数人", "frequency": "月频；每月第一个周五8:30（美东）", "revision": "随后两个月各修正一次；每年2月对QCEW做基准修订", "use": "非农、行业就业、周工时、AHE与就业扩散指数", "pitfall": "初值回收率低、Birth-Death顺周期偏差、罢工/天气/参考周扰动", "pptSlide": "PPT p.29—37"},
        {"id": "cps", "title": "CPS家庭调查", "producer": "BLS与Census", "sample": "约6万户家庭、约10万人；数人，含自雇与农业", "frequency": "月频；与CES同日发布", "revision": "不作月度修正；每年1月人口控制跳变", "use": "U1—U6、参与率、分人群失业率、就业与劳动力流量", "pitfall": "样本误差远大于CES；退出劳动力可机械压低U3；1月水平变化不可直接读", "pptSlide": "PPT p.38—47"},
        {"id": "claims", "title": "初请/续请失业金", "producer": "美国劳工部；iFinD转引圣路易斯联储", "sample": "失业保险行政记录，接近普查", "frequency": "周频；每周四", "revision": "通常修正很小；4周均值用于过滤周度噪音", "use": "初请监测新增裁员，续请监测再就业难度", "pitfall": "车厂停工、假日周、单州异动与特殊救济项目会扭曲单周", "pptSlide": "PPT p.48"},
        {"id": "jolts", "title": "JOLTS", "producer": "BLS", "sample": "约2.1万家机构；职位空缺、雇佣、辞职与解雇", "frequency": "月频；通常发布T−2月数据", "revision": "会修正，且回复率已明显下降", "use": "V/U衡量供需紧度；流量刻画冻结、高流动或裁员周期", "pitfall": "时效显著落后非农；职位广告不等于有效招聘", "pptSlide": "PPT p.49"},
        {"id": "wages", "title": "工资三口径", "producer": "BLS/CES、BLS/ECI、Atlanta Fed/CPS微观", "sample": "AHE总薪资÷总工时；ECI固定职业权重；Atlanta同人隔12个月配对", "frequency": "AHE月频最快；ECI季频最慢；Atlanta月频、3个月均值", "revision": "三者更新节奏不同", "use": "AHE跟踪、ECI确认、Atlanta观察个体工资与跳槽溢价", "pitfall": "AHE受低薪岗位进出造成的构成偏差；不可把三条线当同口径", "pptSlide": "PPT p.50"},
    ]

    payroll_latest = payroll_momentum["totalSeries"]
    u3_latest = u_spectrum["series"][1]
    vu_latest = vu_wage["series"][0]
    claims_latest = claims["series"][0]
    wage_latest = wage_three["series"][1]
    monthly_missing = {
        key: detect_missing_months(dates)
        for key, (dates, _values) in parsed.items()
        if SERIES_SPEC[key][4] == "月"
    }

    return {
        "schemaVersion": 2,
        "generatedAt": generated_at,
        "source": "iFinD EDB",
        "sourceProviders": ["iFinD EDB"],
        "frameworkSource": {"file": "研究框架/美国宏观数据培训【0829定稿】.pptx", "slides": "26—59", "routeSlide": 27},
        "routeMap": route_map,
        "dataPassports": data_passports,
        "headline": [
            {"id": "payroll-momentum", "label": "CES趋势", "title": "新增非农3个月均值", "value": payroll_latest["latestValue"], "unit": "千人", "observation": payroll_latest["latestObservation"], "source": "iFinD EDB"},
            {"id": "unemployment", "label": "CPS结果", "title": "U3失业率", "value": u3_latest["latestValue"], "unit": "%", "observation": u3_latest["latestObservation"], "source": "iFinD EDB"},
            {"id": "vu", "label": "供需紧度", "title": "V/U", "value": vu_latest["latestValue"], "unit": "倍", "observation": vu_latest["latestObservation"], "source": "iFinD EDB"},
            {"id": "claims", "label": "周频哨兵", "title": "初请4周均值", "value": claims_latest["latestValue"], "unit": "万人", "observation": claims_latest["latestObservation"], "source": "iFinD EDB"},
            {"id": "wage", "label": "工资确认", "title": "ECI工资薪金同比", "value": wage_latest["latestValue"], "unit": "%", "observation": wage_latest["latestObservation"], "source": "iFinD EDB"},
        ],
        "sections": {
            "officialSurveys": {
                "title": "官方双调查", "description": "CES回答岗位的量、强度和价格；CPS回答人的就业状态、参与和结构。",
                "charts": official_charts,
                "sectorMonitor": {"title": "行业就业广度与结构表", "description": "最近12个月逐月热度，并与2018—2019月均增量比较。", "periods": sector_periods, "rows": sector_rows, "source": {"provider": "iFinD EDB", "url": "https://ft.51ifind.com"}},
            },
            "flows": {"title": "流量与周频", "description": "用JOLTS刻画岗位与人员流量，用初请/续请补足月度数据之间的高频真空。", "charts": [claims, vu_wage, jolts]},
            "wages": {"title": "工资三口径", "description": "快读AHE、确认ECI、理解个体工资用Atlanta；三条线互补而非替代。", "charts": [wage_three]},
            "frameworks": {"title": "四大经验框架", "description": "把数据变成判断，但把经验关系当作可失效的假设，而不是经济定律。", "charts": [okun, unemployment_gap, beveridge, sahm]},
            "crossChecks": {
                "title": "第三方交叉验证", "description": "第三方数据提供先行或独立样本，但覆盖和方法论决定其只能作为第二意见。",
                "charts": [adp_trend, adp_scatter],
                "availability": [
                    {"id": "challenger", "label": "Challenger裁员", "status": "not-integrated", "explanation": "公告裁员而非实际解雇，且不季调；当前iFinD EDB未找到可稳定验证的总量序列。"},
                    {"id": "indeed", "label": "Indeed职位发布", "status": "not-integrated", "explanation": "实时招聘广告领先JOLTS，但受平台份额变化影响；当前未接入可复现iFinD序列。"},
                    {"id": "nfib", "label": "NFIB招聘计划", "status": "not-integrated", "explanation": "反映小企业招聘意愿和招工困难；当前未接入可复现iFinD序列。"},
                    {"id": "warn", "label": "WARN裁员预告", "status": "not-integrated", "explanation": "法定预告领先性强，但州级门槛与格式不一，需独立管线而非拼接模拟。"},
                ],
            },
        },
        "dataQuality": {"monthlyMissingPeriods": monthly_missing, "note": "全部已绘制时序来自iFinD EDB；月、周、季频与JOLTS保留各自观测日期。派生指标均在构建脚本中确定性计算。"},
        "researchBasis": ["页面信息架构依据《美国宏观数据培训【0829定稿】》第一章就业市场路线图与图表说明重建。", "页面数值全部由iFinD EDB重新提取；PPT只提供指标定义、阅读顺序和口径警示。"],
        "rawSnapshots": {"ifind": raw_snapshot},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--input", type=Path, help="Use a saved raw iFinD bundle instead of fetching.")
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if args.input:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        raw_snapshot = str(args.input)
    else:
        token, log_file = read_token()
        print(f"read iFinD session from {log_file.name}")
        raw = fetch_all(token)
        args.raw_dir.mkdir(parents=True, exist_ok=True)
        stamp = generated_at.replace(":", "").replace("-", "")
        raw_path = args.raw_dir / f"{stamp}_ifind_employment.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        raw_snapshot = str(raw_path.relative_to(REPO_ROOT)).replace("\\", "/")
        print(f"raw saved to {raw_path}")

    dataset = build_dataset(raw, generated_at, raw_snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"headline: {len(dataset['headline'])}")
    print(f"charts: {sum(len(section.get('charts', [])) for section in dataset['sections'].values())}")
    print(f"sector rows: {len(dataset['sections']['officialSurveys']['sectorMonitor']['rows'])}")


if __name__ == "__main__":
    main()
