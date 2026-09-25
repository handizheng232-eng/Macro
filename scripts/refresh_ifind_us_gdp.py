"""Build the US GDP and national-accounts workspace from iFinD EDB.

The script validates each selected indicator against iFinD search metadata, saves
raw responses, derives documented transformations, and writes
``src/data/usGdpData.json``.  It never persists the local iFinD session token.
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
DEFAULT_OUTPUT = REPO_ROOT / "src" / "data" / "usGdpData.json"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "ifind-us-gdp"
START_DATE = "1990-01-01"
SEARCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/search/associate"
FETCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/fetch_data/search"
REFERER = "https://ft.51ifind.com/standardgwapi/bff/macro_bff/edb_web/index?pluginVersion=excel_win64"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 Chrome/84.0.4147.105 Safari/537.36"
LOG_TOKEN = re.compile(r'jgbsession["\'\:= ]+([0-9a-fA-F]{32})')
_CODE_PREFIX = re.compile(r"^[A-Za-z]+0*")

# code, exact name, label, raw unit, frequency, institution, color, plausible range
SERIES_SPEC: dict[str, tuple[str, str, str, str, str, str, str, tuple[float, float]]] = {
    "real_gdp_level": ("G002599633", "美国:GDP:不变价:支出法:折年数:季调:当季值", "实际GDP", "十亿美元", "季", "美国经济分析局", "#1859b8", (5_000, 40_000)),
    "real_gdp_saar": ("G005120877", "美国:GDP:不变价:支出法:环比折年率:季调:当季值", "实际GDP", "%", "季", "美国经济分析局", "#17233b", (-50, 50)),
    "nominal_gdp_level": ("G002599635", "美国:GDP:支出法:折年数:季调:当季值", "名义GDP", "十亿美元", "季", "美国经济分析局", "#c94c4c", (5_000, 50_000)),
    "potential_gdp": ("G011775386", "美国:10年经济预测:实际潜在GDP:当季值", "CBO实际潜在GDP", "十亿美元", "季", "美国国会预算办公室", "#c94c4c", (10_000, 50_000)),
    "potential_growth": ("G011775387", "美国:10年经济预测:实际潜在GDP:折年数:增长率:当季值", "CBO实际潜在GDP增速", "%", "季", "美国国会预算办公室", "#a56a12", (-5, 10)),
    "labor_force_yoy": ("G005213865", "美国:劳动力人数:16岁及以上:季调:当月同比", "劳动力增速", "%", "月", "美国劳工局", "#1859b8", (-10, 10)),
    "productivity_yoy": ("G005349842", "美国:投入产出指数:人工生产率非农商业:当季同比", "劳动生产率增速", "%", "季", "美国劳工局", "#c94c4c", (-20, 20)),
    "nominal_consumption": ("G002599638", "美国:GDP:支出法:个人消费:折年数:季调:当季值", "消费 C", "十亿美元", "季", "美国经济分析局", "#1859b8", (1_000, 40_000)),
    "nominal_investment": ("G002599643", "美国:GDP:支出法:国内私人投资:折年数:季调:当季值", "私人投资 I", "十亿美元", "季", "美国经济分析局", "#c94c4c", (-5_000, 15_000)),
    "nominal_government": ("G002599657", "美国:GDP:支出法:政府消费支出和投资:折年数:季调:当季值", "政府购买 G", "十亿美元", "季", "美国经济分析局", "#8a9096", (1_000, 15_000)),
    "nominal_net_exports": ("G002599650", "美国:GDP:支出法:净出口:折年数:季调:当季值", "净出口 NX", "十亿美元", "季", "美国经济分析局", "#a56a12", (-5_000, 5_000)),
    "final_sales_saar": ("G005132578", "美国:GDP:不变价:最终销售:环比折年率:季调:当季值", "最终销售", "%", "季", "美国经济分析局", "#2f7fa3", (-50, 50)),
    "domestic_final_sales_saar": ("G010701366", "美国:不变价:国内采购总额:最终销售:环比折年率:季调:当季值", "国内购买者最终销售", "%", "季", "美国经济分析局", "#855c9c", (-50, 50)),
    "pdfp_saar": ("G010701368", "美国:不变价:国内私人采购:最终销售:环比折年率:季调:当季值", "PDFP私人国内最终购买", "%", "季", "美国经济分析局", "#2f8a7a", (-50, 50)),
    "contrib_consumption": ("G005120950", "美国:GDP:不变价:支出法:环比贡献率:个人消费:折年数:季调:当季值", "消费", "%", "季", "美国经济分析局", "#1859b8", (-30, 30)),
    "contrib_investment": ("G005120955", "美国:GDP:不变价:支出法:环比贡献率:国内私人投资:折年数:季调:当季值", "私人投资", "%", "季", "美国经济分析局", "#c94c4c", (-30, 30)),
    "contrib_government": ("G005120969", "美国:GDP:不变价:支出法:环比贡献率:政府消费支出和投资:折年数:季调:当季值", "政府购买", "%", "季", "美国经济分析局", "#8a9096", (-30, 30)),
    "contrib_net_exports": ("G005120962", "美国:GDP:不变价:支出法:环比贡献率:净出口:折年数:季调:当季值", "净出口", "%", "季", "美国经济分析局", "#a56a12", (-30, 30)),
    "gdi_level": ("G010701498", "美国:不变价:GDI:折年数:季调:当季值", "实际GDI", "百万美元", "季", "美国经济分析局", "#c94c4c", (5_000_000, 40_000_000)),
    "gdp_gdi_mean": ("G010701499", "美国:不变价:GDP和GDI均值:折年数:季调:当季值", "GDP/GDI简单均值", "百万美元", "季", "美国经济分析局", "#8a9096", (5_000_000, 40_000_000)),
    "deflator_level": ("G005123971", "美国:GDP:2017价:支出法:平减指数:季调:当季值", "GDP平减指数", "2017年=100", "季", "美国经济分析局", "#ba7a2e", (20, 250)),
    "wei": ("G005350606", "美国:经济活动指数", "WEI周度经济指数", "", "周", "达拉斯联储", "#1859b8", (-20, 20)),
    "ces_employment": ("G002600500", "美国:非农就业人数:季调", "非农就业 CES", "千人", "月", "美国劳工局", "#1859b8", (50_000, 250_000)),
    "cps_employment": ("G002600502", "美国:就业人数:16岁及以上:季调:当月值", "家庭就业 CPS", "千人", "月", "美国劳工局", "#2f7fa3", (50_000, 250_000)),
    "real_pce_monthly": ("G010698399", "美国:2017价:个人消费支出:折年数:季调:当月值", "实际个人消费 PCE", "百万美元", "月", "美国经济分析局", "#ba7a2e", (5_000_000, 40_000_000)),
    "industrial_production": ("G006598549", "美国:工业生产指数:季调:当月值", "工业生产", "2017年=100", "月", "美联储", "#6f7883", (40, 150)),
}


def compact_date(value: Any) -> str:
    normalized = str(value).replace("-", "").replace("/", "").replace(".", "")
    if len(normalized) == 6:
        return normalized + "01"
    if len(normalized) >= 8:
        return normalized[:8]
    raise ValueError(f"invalid observation date: {value!r}")


def period_key(value: str, digits: int = 8) -> str:
    return compact_date(value)[:digits]


def align_common_periods(series_map: dict[str, tuple[list[str], list[float]]], digits: int = 8) -> tuple[list[str], dict[str, list[float]]]:
    maps = {key: {period_key(date, digits): value for date, value in zip(dates, values)} for key, (dates, values) in series_map.items()}
    periods = sorted(set.intersection(*(set(values) for values in maps.values()))) if maps else []
    return periods, {key: [values[period] for period in periods] for key, values in maps.items()}


def rolling_mean(dates: list[str], values: list[float], window: int) -> tuple[list[str], list[float]]:
    if window < 1:
        raise ValueError("window must be positive")
    return dates[window - 1:], [statistics.fmean(values[index - window + 1:index + 1]) for index in range(window - 1, len(values))]


def year_over_year(dates: list[str], values: list[float], periods: int = 4) -> tuple[list[str], list[float]]:
    rows = [(dates[index], (values[index] / values[index - periods] - 1) * 100) for index in range(periods, len(values)) if values[index - periods] != 0]
    return [date for date, _ in rows], [value for _, value in rows]


def annualized_growth(dates: list[str], values: list[float]) -> tuple[list[str], list[float]]:
    rows = [(dates[index], ((values[index] / values[index - 1]) ** 4 - 1) * 100) for index in range(1, len(values)) if values[index - 1] > 0]
    return [date for date, _ in rows], [value for _, value in rows]


def rebase(dates: list[str], values: list[float], base_period: str) -> tuple[list[str], list[float]]:
    base = next((value for date, value in zip(dates, values) if compact_date(date).startswith(base_period.replace("-", ""))), None)
    if base in (None, 0):
        raise ValueError(f"base period {base_period} unavailable")
    return list(dates), [value / base * 100 for value in values]


def detect_missing_periods(dates: Iterable[str], frequency: str) -> list[str]:
    compact = sorted({compact_date(date) for date in dates})
    if not compact or frequency not in {"月", "季"}:
        return []
    actual = {date[:6] for date in compact}
    year, month = int(compact[0][:4]), int(compact[0][4:6])
    end_year, end_month = int(compact[-1][:4]), int(compact[-1][4:6])
    step = 1 if frequency == "月" else 3
    expected = []
    while (year, month) <= (end_year, end_month):
        expected.append(f"{year:04d}{month:02d}")
        month += step
        while month > 12:
            month -= 12
            year += 1
    return [item for item in expected if item not in actual]


def fetch_response_series(payload: dict[str, Any], display_id: str) -> tuple[list[str], list[float]]:
    if payload.get("code") != 1:
        raise ValueError(f"iFinD rejected {display_id}: {payload.get('msg') or payload.get('code')}")
    table = next((item for item in ((payload.get("data") or {}).get("tables") or []) if str(item.get("displayid") or "") == display_id), None)
    if table is None:
        raise ValueError(f"iFinD returned no block for {display_id}")
    rows = [(compact_date(date), float(value)) for date, value in zip(table.get("time") or [], table.get("value") or []) if value not in (None, "", "--", "#N/A")]
    rows.sort(key=lambda item: item[0])
    if not rows:
        raise ValueError(f"iFinD returned no observations for {display_id}")
    return [date for date, _ in rows], [value for _, value in rows]


def candidate_log_dirs() -> Iterable[Path]:
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
                if parent.is_dir():
                    for child in parent.iterdir():
                        if "ifind" in child.name.lower() and (child / "logs").is_dir():
                            yield child / "logs"
            except (OSError, PermissionError):
                continue


def read_token() -> str:
    for log_dir in candidate_log_dirs():
        try:
            logs = sorted(log_dir.glob("socketclient_*.xlog"), key=lambda path: path.stat().st_mtime, reverse=True)
        except OSError:
            continue
        for log in logs:
            try:
                hits = LOG_TOKEN.findall(log.read_bytes().decode("utf-8", "ignore"))
            except OSError:
                continue
            if hits:
                return hits[-1]
    raise RuntimeError("未找到 iFinD 登录会话：请打开 iFinD 客户端登录一次后再运行。")


def headers(token: str) -> dict[str, str]:
    return {"Accept": "application/json, text/plain, */*", "User-Agent": USER_AGENT, "Referer": REFERER, "Origin": "https://ft.51ifind.com", "Cookie": f"jgbsessid={token}"}


def search_indicator(token: str, keyword: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(SEARCH_URL + "?" + urllib.parse.urlencode({"keyword": keyword}), headers=headers(token))
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 1:
        raise ValueError(f"iFinD search rejected {keyword}: {payload.get('msg')}")
    return payload.get("data") or []


def fetch_indicator(token: str, display_id: str, start: str, end: str) -> dict[str, Any]:
    body = urllib.parse.urlencode({"zb_str": _CODE_PREFIX.sub("", display_id) or display_id, "displayid": display_id, "zb_rtime": "0", "formula": "0", "wt": "json", "usage": "macro", "sdate": start.replace("-", ""), "edate": end.replace("-", "")}).encode()
    request = urllib.request.Request(FETCH_URL, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded", **headers(token)})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all(token: str) -> dict[str, dict[str, Any]]:
    end = datetime.now(timezone.utc).date().isoformat()
    result = {}
    for key, spec in SERIES_SPEC.items():
        code, exact_name, _label, unit, frequency, _institution, _color, bounds = spec
        metadata = next((item for item in search_indicator(token, exact_name) if item.get("displayid") == code), None)
        if metadata is None:
            raise ValueError(f"metadata mismatch: {key} {code} not found")
        returned_unit = metadata.get("unit") or ""
        if metadata.get("name") != exact_name or returned_unit != unit or metadata.get("frequency") != frequency:
            raise ValueError(f"identity mismatch for {key}: {metadata}")
        payload = fetch_indicator(token, code, START_DATE, end)
        dates, values = fetch_response_series(payload, code)
        if not all(bounds[0] <= value <= bounds[1] for value in values):
            raise ValueError(f"range check failed for {key}: {min(values)}..{max(values)}")
        result[key] = {"metadata": metadata, "payload": payload}
        print(f"verified {key}: {code} {dates[0]}..{dates[-1]} ({len(dates)})")
    return result


def source_meta(key: str, latest: str, raw_unit: str | None = None) -> dict[str, Any]:
    code, name, _label, unit, _frequency, institution, _color, _bounds = SERIES_SPEC[key]
    return {"provider": "iFinD EDB", "institution": institution, "code": code, "name": name, "rawUnit": unit if raw_unit is None else raw_unit, "url": "https://ft.51ifind.com", "latestObservation": latest}


def make_series(key: str, dates: list[str], values: list[float], *, series_id: str | None = None, label: str | None = None, color: str | None = None, unit: str | None = None, frequency: str | None = None, transform: str | None = None) -> dict[str, Any]:
    _code, _name, default_label, default_unit, default_frequency, _institution, default_color, _bounds = SERIES_SPEC[key]
    item = {"id": series_id or key, "label": label or default_label, "dates": dates, "values": [round(value, 4) for value in values], "color": color or default_color, "unit": default_unit if unit is None else unit, "frequency": frequency or default_frequency, "latestValue": round(values[-1], 4), "latestObservation": dates[-1], "source": source_meta(key, dates[-1])}
    if transform:
        item["transformLabel"] = transform
    return item


def chart(chart_id: str, title: str, description: str, unit: str, series: list[dict[str, Any]], *, eyebrow: str, explanation: dict[str, str], kind: str = "line", default_range: str = "5Y", reference: float | None = None, total_series: dict[str, Any] | None = None, rebased_at: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"id": chart_id, "kind": kind, "eyebrow": eyebrow, "title": title, "description": description, "unit": unit, "defaultRange": default_range, "series": series, "explanation": explanation}
    if reference is not None:
        result["reference"] = reference
    if total_series:
        result["totalSeries"] = total_series
    if rebased_at:
        result["rebasedAt"] = rebased_at
    return result


def parse_raw(raw: dict[str, dict[str, Any]]) -> dict[str, tuple[list[str], list[float]]]:
    return {key: fetch_response_series(item["payload"], SERIES_SPEC[key][0]) for key, item in raw.items()}


def build_dataset(raw: dict[str, dict[str, Any]], raw_snapshot: str) -> dict[str, Any]:
    parsed = parse_raw(raw)
    actual_last = parsed["real_gdp_level"][0][-1]
    p_dates, p_values = parsed["potential_gdp"]
    potential_actual = [(date, value) for date, value in zip(p_dates, p_values) if date <= actual_last]
    p_actual_dates = [date for date, _ in potential_actual]
    p_actual_values = [value for _, value in potential_actual]

    prod_dates, prod_values = rolling_mean(*parsed["productivity_yoy"], 8)
    labor_dates, labor_values = rolling_mean(*parsed["labor_force_yoy"], 12)

    real_yoy = year_over_year(*parsed["real_gdp_level"])
    nominal_yoy = year_over_year(*parsed["nominal_gdp_level"])
    gdi_yoy = year_over_year(parsed["gdi_level"][0], [value / 1000 for value in parsed["gdi_level"][1]])
    mean_yoy = year_over_year(parsed["gdp_gdi_mean"][0], [value / 1000 for value in parsed["gdp_gdi_mean"][1]])
    deflator_yoy = year_over_year(*parsed["deflator_level"])

    share_periods, share_values = align_common_periods({key: parsed[key] for key in ("nominal_gdp_level", "nominal_consumption", "nominal_investment", "nominal_government", "nominal_net_exports")})
    latest_share_index = -1
    nominal_gdp = share_values["nominal_gdp_level"][latest_share_index]
    shares = [{"id": key, "label": SERIES_SPEC[key][2], "value": round(share_values[key][latest_share_index] / nominal_gdp * 100, 1), "color": SERIES_SPEC[key][6], "source": source_meta(key, share_periods[latest_share_index])} for key in ("nominal_consumption", "nominal_investment", "nominal_government", "nominal_net_exports")]

    nber_series = []
    for key in ("ces_employment", "cps_employment", "real_pce_monthly", "industrial_production"):
        dates, values = rebase(*parsed[key], "202112")
        nber_series.append(make_series(key, dates, values, series_id=key, unit="指数", transform="2021-12=100"))

    actual_potential = chart("actual-potential", "实际GDP与CBO潜在GDP", "以潜在产出作为经济“限速”；实际高于潜在意味着正产出缺口，但潜在值是模型估计而非观测。", "十亿美元（链式2017价）", [make_series("real_gdp_level", *parsed["real_gdp_level"]), make_series("potential_gdp", p_actual_dates, p_actual_values, series_id="potential_gdp", transform="CBO十年经济预测当前版本；仅展示至最新实际GDP季度")], eyebrow="3.1 · POTENTIAL OUTPUT", default_range="ALL", explanation={"what": "实际GDP是BEA核算的真实产出；潜在GDP是CBO对可持续产出能力的估计。", "howToRead": "实际线高于潜在线时，产出缺口为正；判断增速强弱必须相对潜在增速。", "caveat": "CBO序列会随模型和人口假设修订，当前版本仅从2017Q1起，不是实时历史vintage。", "pptSlide": "PPT第96—98页 · 图3-1"})
    supply_legs = chart("supply-legs", "潜在增速的两条腿", "劳动力同比做12个月平滑，非农商业劳动生产率同比做8季平滑；两者方向共同决定供给侧增速。", "%同比", [make_series("labor_force_yoy", labor_dates, labor_values, transform="12个月移动平均"), make_series("productivity_yoy", prod_dates, prod_values, transform="8季移动平均")], eyebrow="3.1 · LABOR + PRODUCTIVITY", default_range="ALL", explanation={"what": "劳动力数量决定投入规模，产出/小时衡量劳动生产率。", "howToRead": "移民收缩压低劳动力腿；生产率趋势回升可抬高经济限速，但两者方向可能相反。", "caveat": "月频与季频序列保留各自观测日；相加只是增长核算近似，不是CBO潜在增速公式。", "pptSlide": "PPT第96、98页 · 图3-1右图"})
    core_onion = chart("gdp-core-onion", "从头条GDP剥到私人内需", "逐层剔除库存、净出口与政府购买，观察更平滑的内生需求。", "% SAAR", [make_series("real_gdp_saar", *parsed["real_gdp_saar"], series_id="real_gdp_saar"), make_series("final_sales_saar", *parsed["final_sales_saar"]), make_series("domestic_final_sales_saar", *parsed["domestic_final_sales_saar"]), make_series("pdfp_saar", *parsed["pdfp_saar"], series_id="pdfp_saar")], eyebrow="3.1 · CORE GDP ONION", explanation={"what": "GDP含全部支出；Final Sales剔库存；国内购买者最终销售再剔净出口；PDFP再剔政府。", "howToRead": "GDP弱而PDFP稳，多为库存或贸易噪音；PDFP同步走弱才更像私人需求降温。", "caveat": "四条都是季环比季调折年率，噪音约被放大四倍；PDFP不能替代GDP。", "pptSlide": "PPT第100—101页 · 未命名GDP/FGDP/PDFP图"})
    contributions = chart("growth-contributions", "实际GDP增长贡献拆分", "消费、投资、政府与净出口对当季实际GDP环比折年率的官方百分点贡献。", "百分点", [make_series(key, *parsed[key], unit="百分点", transform="iFinD元数据为%；经济含义为对GDP增速的百分点贡献") for key in ("contrib_consumption", "contrib_investment", "contrib_government", "contrib_net_exports")], kind="bar", total_series=make_series("real_gdp_saar", *parsed["real_gdp_saar"], series_id="gdp_total", label="实际GDP环比折年率"), eyebrow="3.1 · EXPENDITURE CONTRIBUTIONS", explanation={"what": "官方贡献序列把各支出分项对GDP增速的拉动直接表示为百分点。", "howToRead": "消费是体量支柱，投资通常是波动来源；库存和净出口常使头条GDP偏离私人需求。", "caveat": "实际链式美元分项不具严格可加性，应使用贡献序列而不是拿实际水平硬相加。", "pptSlide": "PPT第99—101页 · 图3-2与核心GDP说明"})
    gdp_gdi = chart("gdp-gdi", "同一经济的支出法与收入法", "实际GDP、实际GDI及两者官方简单均值的同比增速；分歧可视作统计差异的一部分。", "%同比", [make_series("real_gdp_level", *real_yoy, series_id="real_gdp_yoy", label="实际GDP同比", unit="%", transform="由实际GDP水平计算4季同比"), make_series("gdi_level", *gdi_yoy, series_id="gdi_yoy", label="实际GDI同比", unit="%", transform="百万美元转十亿美元后计算4季同比"), make_series("gdp_gdi_mean", *mean_yoy, series_id="gdp_gdi_mean_yoy", label="GDP/GDI简单均值同比", unit="%", transform="BEA官方简单均值水平计算4季同比")], eyebrow="3.2 · GDP VS GDI", explanation={"what": "GDP从支出/产出端核算，GDI从工资、利润、利息和租金等收入端核算。", "howToRead": "两者理论恒等、实测常背离；拐点处可参考简单均值，但不能把它标成GDPplus。", "caveat": "GDI通常更晚、修订更大；简单均值、CEA GDO与Philly Fed GDPplus不是同一算法。", "pptSlide": "PPT第103页 · 图3-4"})
    nominal_real = chart("nominal-real-deflator", "名义增长、实际增长与GDP平减指数", "把金额增长拆成真实产量和广义价格变化，避免把通胀造成的营收繁荣误读为实际繁荣。", "%同比", [make_series("nominal_gdp_level", *nominal_yoy, series_id="nominal_gdp_yoy", label="名义GDP同比", unit="%", transform="由名义GDP水平计算4季同比"), make_series("real_gdp_level", *real_yoy, series_id="real_gdp_yoy_price", label="实际GDP同比", unit="%", transform="由实际GDP水平计算4季同比"), make_series("deflator_level", *deflator_yoy, series_id="deflator_yoy", label="GDP平减指数同比", unit="%", transform="由官方GDP平减指数计算4季同比")], eyebrow="3.2 · NOMINAL / REAL / PRICE", explanation={"what": "名义GDP映射收入、营收与税收；实际GDP衡量产量；GDP平减指数覆盖消费、投资、政府与出口价格。", "howToRead": "名义强而实际弱时，增长主要来自价格；2021—22年的两者裂口即是典型。", "caveat": "平减指数不是CPI/PCE；名义增速减实际增速只是近似，页面使用官方平减指数。", "pptSlide": "PPT第104页 · 图3-5"})
    wei_gdp = chart("wei-gdp", "WEI填补季度GDP的统计真空", "iFinD中的“美国经济活动指数”由达拉斯联储提供，周频走势与季度实际GDP同比对照。", "% / iFinD原始口径", [make_series("wei", *parsed["wei"], series_id="wei", unit="", transform="iFinD单位字段为空；对应Dallas Fed Weekly Economic Index"), make_series("real_gdp_level", *real_yoy, series_id="real_gdp_yoy_wei", label="实际GDP同比", unit="%", transform="季度实际GDP水平计算4季同比")], eyebrow="3.3 · WEEKLY NOWCAST", explanation={"what": "WEI把初请、零售、用电、铁路货运等周度信息压缩为经济活动指数。", "howToRead": "重点看方向与拐点；2020年WEI比季度GDP更早显示垂直下跌。", "caveat": "iFinD名称未写WEI且单位字段为空，不能把空单位无条件改写为%；周频与季频保留各自日期。", "pptSlide": "PPT第107页 · 图3-8"})
    nber = chart("nber-dashboard", "NBER月度活动拼图", "以2021年12月为100，对照就业、实际消费与工业生产；iFinD EDB未检出六项中的实际收入除转移支付、实际制造与贸易销售。", "指数", nber_series, eyebrow="3.2/3.4 · RECESSION CHECK", default_range="5Y", reference=100, rebased_at="2021-12=100", explanation={"what": "NBER看经济活动下降的深度、广度与持续性，而不是机械套用两季负增长。", "howToRead": "多条月度硬数据持续、同步跌破基期才更接近广泛衰退；2022H1就业和消费并未同步坍塌。", "caveat": "本图接入四项；缺少的两项明确标记未接入。NBER没有固定六指标公式，峰谷判断是回顾性的。", "pptSlide": "PPT第105、109页 · 图3-7"})

    contrib_periods, contrib_values = align_common_periods({key: parsed[key] for key in ("real_gdp_saar", "contrib_consumption", "contrib_investment", "contrib_government", "contrib_net_exports")})
    contribution_sum = sum(contrib_values[key][-1] for key in ("contrib_consumption", "contrib_investment", "contrib_government", "contrib_net_exports"))
    deflator_periods, deflator_values = align_common_periods({"nominal": parsed["nominal_gdp_level"], "real": parsed["real_gdp_level"], "deflator": parsed["deflator_level"]})
    mean_periods, mean_values = align_common_periods({"gdp": parsed["real_gdp_level"], "gdi": (parsed["gdi_level"][0], [value / 1000 for value in parsed["gdi_level"][1]]), "mean": (parsed["gdp_gdi_mean"][0], [value / 1000 for value in parsed["gdp_gdi_mean"][1]])})

    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    headline = [
        {"id": "real-gdp", "label": "头条增长", "title": "实际GDP环比折年", "value": parsed["real_gdp_saar"][1][-1], "unit": "%", "observation": parsed["real_gdp_saar"][0][-1], "source": "iFinD EDB"},
        {"id": "pdfp", "label": "私人内需", "title": "PDFP环比折年", "value": parsed["pdfp_saar"][1][-1], "unit": "%", "observation": parsed["pdfp_saar"][0][-1], "source": "iFinD EDB"},
        {"id": "gdo", "label": "双核算均值", "title": "GDP/GDI均值环比折年", "value": annualized_growth(parsed["gdp_gdi_mean"][0], parsed["gdp_gdi_mean"][1])[1][-1], "unit": "%", "observation": parsed["gdp_gdi_mean"][0][-1], "source": "iFinD EDB"},
        {"id": "potential", "label": "供给标尺", "title": "CBO潜在增速", "value": parsed["potential_growth"][1][-1], "unit": "%", "observation": parsed["potential_growth"][0][-1], "source": "iFinD EDB"},
        {"id": "wei", "label": "周度温度计", "title": "WEI经济活动指数", "value": parsed["wei"][1][-1], "unit": "原始值", "observation": parsed["wei"][0][-1], "source": "iFinD EDB"},
    ]

    return {
        "schemaVersion": 1,
        "generatedAt": generated,
        "source": "iFinD EDB",
        "sourceProviders": ["iFinD EDB"],
        "frameworkSource": {"file": "研究框架/美国宏观数据培训【0829定稿】.pptx", "slides": "94—111", "routeSlide": 95},
        "routeMap": [
            {"id": "framework", "title": "分析框架", "subtitle": "先立标尺", "nodes": [{"title": "潜在增速", "detail": "劳动力+生产率"}, {"title": "支出法恒等式", "detail": "Y=C+I+G+NX"}, {"title": "剥洋葱", "detail": "GDP→最终销售→PDFP"}]},
            {"id": "official", "title": "官方数据", "subtitle": "再读核算", "nodes": [{"title": "三次估计", "detail": "advance信息增量最高"}, {"title": "GDP vs GDI", "detail": "同一经济量两次"}, {"title": "贡献拆分", "detail": "库存与净出口是噪音源"}, {"title": "衰退判定", "detail": "NBER拼图vs两季法则"}]},
            {"id": "tracking", "title": "第三方跟踪", "subtitle": "填统计真空", "nodes": [{"title": "GDPNow / Nowcast", "detail": "会计模拟vs动态因子"}, {"title": "WEI", "detail": "10项周度数据合成"}]},
            {"id": "pitfalls", "title": "常见陷阱", "subtitle": "口径纪律", "nodes": [{"title": "初值与修订", "detail": "拐点处初值可能系统性偏误"}, {"title": "会计错觉", "detail": "进口扣除≠进口造成损失；GDP≠福利"}]},
            {"id": "case", "title": "案例复盘", "subtitle": "保存vintage", "nodes": [{"title": "2022技术性衰退", "detail": "Q2初值-0.9%后修订为+0.6%"}]},
        ],
        "dataPassports": [
            {"id": "gdp", "title": "GDP报告", "producer": "BEA整合Census、BLS等源数据", "frequency": "季度；advance约T+30天", "revision": "advance→second→third；年度与综合修订", "use": "总量、支出分项与贡献", "pitfall": "SAAR放大噪音；advance到latest的修订可显著", "pptSlide": "第102页"},
            {"id": "potential", "title": "潜在GDP", "producer": "CBO模型估计", "frequency": "季度预测路径", "revision": "随人口、生产率和政策假设更新", "use": "判断增长相对经济限速", "pitfall": "不可观测；端点和实时估计最不可靠", "pptSlide": "第96—98页"},
            {"id": "gdi", "title": "GDI", "producer": "BEA收入法核算", "frequency": "季度，通常晚于GDP", "revision": "修订通常更大", "use": "从收入端交叉验证GDP", "pitfall": "简单均值、GDO、GDPplus不可混称", "pptSlide": "第103页"},
            {"id": "wei", "title": "WEI", "producer": "达拉斯联储高频合成指标", "frequency": "周", "revision": "高频历史值可能回修", "use": "填补季度GDP统计真空", "pitfall": "iFinD单位为空；与GDP SAAR不可直接同轴", "pptSlide": "第107页"},
            {"id": "nber", "title": "NBER衰退判定", "producer": "NBER商业周期委员会", "frequency": "月度拼图+季度交叉验证", "revision": "峰谷回顾性确认", "use": "判断下降深度、广度与持续性", "pitfall": "没有机械固定公式；两季负增长不是美国官方定义", "pptSlide": "第105、109页"},
        ],
        "headline": headline,
        "sections": {
            "benchmark": {"title": "潜在增速与支出结构", "description": "先用潜在产出建立标尺，再把Y=C+I+G+NX落实到最新名义份额。", "charts": [actual_potential, supply_legs], "expenditureShares": {"period": share_periods[-1], "rows": shares, "identityTotal": round(sum(item["value"] for item in shares), 1), "note": "名义分项可加总；份额受四舍五入影响。政府G是购买而非转移支付，进口扣除用于排除外国生产。"}},
            "coreDemand": {"title": "核心GDP与增长贡献", "description": "用剥洋葱口径识别内生需求，并用官方贡献序列解释头条波动。", "charts": [core_onion, contributions]},
            "incomePrices": {"title": "收入法与名义—实际桥", "description": "GDP/GDI双核算交叉验证，再把名义增长拆回真实产量与广义价格。", "charts": [gdp_gdi, nominal_real]},
            "cycleTracking": {"title": "Nowcast与衰退判定", "description": "周度指标填统计真空，月度硬数据判断经济下降是否足够广泛。", "charts": [wei_gdp, nber]},
        },
        "revisionCase": {"title": "2022上半年：初值叙事如何被修订改写", "unit": "% SAAR", "rows": [{"period": "2022Q1", "advance": -1.4, "third": -1.6, "latest": -1.0}, {"period": "2022Q2", "advance": -0.9, "third": -0.6, "latest": 0.6}], "source": "PPT第110页；初值来自BEA 2022年4/7月新闻稿，latest为PPT制作时现行国民账户", "caveat": "iFinD EDB当前接口只给latest时间序列，无法自动恢复历史vintage；本表保留PPT明确列示的历史发布值，不冒充定期更新序列。"},
        "informationFlow": [
            {"timing": "月中", "release": "零售销售", "target": "商品消费（控制组进入PCE）"},
            {"timing": "月中/下旬", "release": "住宅开工 / 新屋销售", "target": "住宅投资"},
            {"timing": "下旬", "release": "耐用品订单 / 出货", "target": "设备投资"},
            {"timing": "下旬", "release": "商品贸易 + 批发/零售库存", "target": "净出口与库存"},
            {"timing": "月末", "release": "个人收入与支出", "target": "服务消费"},
            {"timing": "季后约30天", "release": "GDP advance", "target": "已知输入加总+缺口外推"},
        ],
        "availability": [
            {"id": "wei", "label": "Dallas Fed WEI", "status": "available", "explanation": "iFinD EDB已接入G005350606；平台名称为“美国:经济活动指数”，单位字段为空。"},
            {"id": "gdpnow", "label": "Atlanta Fed GDPNow", "status": "not-integrated", "explanation": "本次iFinD EDB官方搜索未发现GDPNow序列，不用其他指标冒充。"},
            {"id": "ny-fed-nowcast", "label": "NY Fed Nowcast", "status": "not-integrated", "explanation": "本次iFinD EDB官方搜索未发现对应序列；若后续接官方快照，必须保存每次发布时间与目标季度。"},
            {"id": "nber-missing", "label": "NBER六项中的两项", "status": "not-integrated", "explanation": "实际收入（除转移支付）与实际制造/贸易销售未在iFinD EDB精确检出，页面仅展示已核验的四项。"},
        ],
        "dataQuality": {
            "missingPeriods": {key: detect_missing_periods(dates, SERIES_SPEC[key][4]) for key, (dates, _values) in parsed.items() if SERIES_SPEC[key][4] in {"月", "季"}},
            "accountingChecks": {
                "latestContributionPeriod": contrib_periods[-1],
                "latestContributionResidualPp": round(contribution_sum - contrib_values["real_gdp_saar"][-1], 6),
                "latestDeflatorPeriod": deflator_periods[-1],
                "latestDeflatorIdentityResidual": round(deflator_values["nominal"][-1] / deflator_values["real"][-1] * 100 - deflator_values["deflator"][-1], 6),
                "latestGdpGdiMeanPeriod": mean_periods[-1],
                "latestGdpGdiMeanResidualBillion": round((mean_values["gdp"][-1] + mean_values["gdi"][-1]) / 2 - mean_values["mean"][-1], 6),
            },
            "note": "所有可更新时序均来自iFinD EDB并逐条核验指标码、名称、单位、频率与量级；异频序列保留各自观测日期。",
        },
        "researchBasis": ["页面按PPT第三章第94—111页路线图、数据说明与图例重建。", "PPT用于定义研究顺序和解释；除明确标注的2022 vintage案例外，页面时序数值均由iFinD EDB重新提取。"],
        "rawSnapshots": {"ifind": raw_snapshot},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--input", type=Path, help="Replay a saved raw iFinD response bundle")
    args = parser.parse_args()
    if args.input:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        snapshot = args.input.relative_to(REPO_ROOT).as_posix() if args.input.is_relative_to(REPO_ROOT) else str(args.input)
    else:
        raw = fetch_all(read_token())
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S+0000")
        args.raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = args.raw_dir / f"{stamp}_ifind_gdp.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        snapshot = raw_path.relative_to(REPO_ROOT).as_posix()
    dataset = build_dataset(raw, snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output} ({sum(len(chart['series']) for section in dataset['sections'].values() for chart in section['charts'])} rendered series)")


if __name__ == "__main__":
    main()
