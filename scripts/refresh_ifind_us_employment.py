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
START_DATE = "2000-01-01"

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
    "u3": ("G005311378", "美国:失业率:U3:季调:当月值", "U3失业率", "%", "月", "#1859b8", (0, 30)),
    "u6": ("G005311381", "美国:失业率:U6:季调:当月值", "U6广义失业率", "%", "月", "#855c9c", (0, 40)),
    "temporary_unemployed": ("G003049325", "美国:失业人数:非自愿性失业(含临时工):暂时性解雇:季调:当月值", "暂时性解雇", "千人", "月", "#ba7a2e", (0, 20000)),
    "permanent_unemployed": ("G003049327", "美国:失业人数:非自愿性失业(含临时工):非暂时性解雇:失业并寻找新工作:季调:当月值", "失业并寻找新工作", "千人", "月", "#c94c4c", (0, 20000)),
    "duration_median": ("G003049383", "美国:失业人数:持续时间中位数:季调:当月值", "持续时间中位数", "周", "月", "#1859b8", (0, 60)),
    "duration_average": ("G003049382", "美国:失业人数:持续时间平均数:季调:当月值", "持续时间平均数", "周", "月", "#855c9c", (0, 80)),
    "initial_claims": ("G002600494", "美国:当周初次申请失业金人数:季调", "初请失业金", "人", "周", "#1859b8", (0, 10_000_000)),
    "continuing_claims": ("G002600496", "美国:截止本周领取失业保险人群:季调", "续请失业金", "人", "周", "#855c9c", (0, 30_000_000)),
    "vacancy_rate": ("G003049462", "美国:职位空缺率:非农部门:季调:当月值", "职位空缺率", "%", "月", "#c94c4c", (0, 15)),
    "hire_rate": ("G003049504", "美国:雇佣率:非农部门:季调:当月值", "雇佣率", "%", "月", "#2f8a7a", (0, 15)),
    "quit_rate": ("G005316325", "美国:自愿性离职率:非农部门:季调:当月值", "自愿离职率", "%", "月", "#ba7a2e", (0, 10)),
    "payroll_total": ("G004786716", "美国:新增非农就业人数:当月值:季调", "非农就业", "千人", "月", "#17233b", (-30_000, 10_000)),
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
    "wage_yoy": ("G005214653", "美国:平均时薪:非农就业员工:私营企业:季调:当月同比", "平均时薪同比", "%", "月", "#c94c4c", (-5, 15)),
    "weekly_hours": ("G005214514", "美国:平均每周工时:非农就业员工:私营企业:季调:当月值", "平均每周工时", "小时", "月", "#1859b8", (20, 50)),
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


def source_meta(key: str, latest: str, *, raw_unit: str | None = None) -> dict[str, Any]:
    code, name, _label, unit, _frequency, _color, _bounds = SERIES_SPEC[key]
    return {
        "provider": "iFinD EDB",
        "institution": "美国劳工局" if "claims" not in key else "圣路易斯联储",
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
    }
    if reference is not None:
        result["reference"] = reference
    if total_series is not None:
        result["totalSeries"] = total_series
    return result


def build_dataset(raw: dict[str, dict[str, Any]], generated_at: str, raw_snapshot: str) -> dict[str, Any]:
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
    print(f"charts: {sum(len(section['charts']) for section in dataset['sections'].values())}")
    print(f"sector rows: {len(dataset['sections']['demand']['sectorHeatmap']['rows'])}")


if __name__ == "__main__":
    main()
