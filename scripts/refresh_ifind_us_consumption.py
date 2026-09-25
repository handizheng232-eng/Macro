"""Build the US consumption workspace from iFinD EDB.

The script verifies every source contract, saves the raw provider responses, derives
PPT-defined transformations, and writes ``src/data/usConsumptionData.json``.
It never persists the local iFinD session token.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "src" / "data" / "usConsumptionData.json"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "ifind-us-consumption"
START_DATE = "1990-01-01"
SEARCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/search/associate"
FETCH_URL = "https://ft.51ifind.com/standardgwapi/api/macro_service/fetch_data/search"
REFERER = "https://ft.51ifind.com/standardgwapi/bff/macro_bff/edb_web/index?pluginVersion=excel_win64"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 Chrome/84.0.4147.105 Safari/537.36"
LOG_TOKEN = re.compile(r'jgbsession["\'\:= ]+([0-9a-fA-F]{32})')
_CODE_PREFIX = re.compile(r"^[A-Za-z]+0*")

# code, exact name, label, unit, frequency, institution, color, plausible range
SERIES_SPEC: dict[str, tuple[str, str, str, str, str, str, str, tuple[float, float]]] = {
    "nominal_gdp": ("G002599635", "美国:GDP:支出法:折年数:季调:当季值", "名义GDP", "十亿美元", "季", "美国经济分析局", "#7a838c", (5_000, 50_000)),
    "nominal_pce_q": ("G002599638", "美国:GDP:支出法:个人消费:折年数:季调:当季值", "个人消费支出", "十亿美元", "季", "美国经济分析局", "#1859b8", (2_000, 40_000)),
    "retail_total": ("G002903442", "美国:零售和食品服务销售额:总计:季调", "总零售", "百万美元", "月", "美国人口普查局", "#7a838c", (100_000, 1_500_000)),
    "retail_auto": ("G002903446", "美国:零售和食品服务销售额:机动车辆和零部件店:季调", "汽车及零部件", "百万美元", "月", "美国人口普查局", "#9a6c55", (20_000, 300_000)),
    "retail_gas": ("G002903460", "美国:零售和食品服务销售额:加油站:季调", "加油站", "百万美元", "月", "美国人口普查局", "#ba7a2e", (5_000, 150_000)),
    "retail_building": ("G002903453", "美国:零售和食品服务销售额:建筑材料、园林设备和物料店:季调", "建材及园林", "百万美元", "月", "美国人口普查局", "#2f7fa3", (5_000, 100_000)),
    "retail_foodservice": ("G002903476", "美国:零售和食品服务销售额:食品服务和饮吧:季调", "餐饮", "百万美元", "月", "美国人口普查局", "#855c9c", (10_000, 200_000)),
    "cpi_index": ("G002600424", "美国:CPI:季调:当月值", "CPI季调指数", "1982-84年=100", "月", "美国劳工局", "#ba7a2e", (50, 500)),
    "real_dpi_yoy": ("G005376552", "美国:个人可支配收入:2017价:季调:当月同比", "实际可支配收入同比", "%", "月", "美国经济分析局", "#1859b8", (-30, 40)),
    "real_pce": ("G010698399", "美国:2017价:个人消费支出:折年数:季调:当月值", "实际个人消费支出", "百万美元", "月", "美国经济分析局", "#c94c4c", (3_000_000, 40_000_000)),
    "saving_rate": ("G002602083", "美国:个人储蓄:占可支配收入比重:折年数:季调:当月值", "个人储蓄率", "%", "月", "美国经济分析局", "#2f8a7a", (0, 40)),
    "nominal_pce": ("G002602081", "美国:个人支出:消费支出:折年数:季调:当月值", "名义PCE", "十亿美元", "月", "美国经济分析局", "#6f7883", (2_000, 40_000)),
    "nominal_services": ("G005376410", "美国:个人支出:消费支出:服务:折年数:季调:当月值", "服务", "十亿美元", "月", "美国经济分析局", "#1859b8", (1_000, 30_000)),
    "nominal_durables": ("G005376408", "美国:个人支出:消费支出:商品:耐用品:折年数:季调:当月值", "耐用品", "十亿美元", "月", "美国经济分析局", "#c94c4c", (100, 10_000)),
    "nominal_nondurables": ("G005376409", "美国:个人支出:消费支出:商品:非耐用品:折年数:季调:当月值", "非耐用品", "十亿美元", "月", "美国经济分析局", "#ba7a2e", (500, 15_000)),
    "real_services": ("G010698403", "美国:2017价:个人消费支出:服务:折年数:季调:当月值", "实际服务消费", "百万美元", "月", "美国经济分析局", "#1859b8", (1_000_000, 30_000_000)),
    "real_durables": ("G010698401", "美国:2017价:个人消费支出:商品:耐用品:折年数:季调:当月值", "实际耐用品消费", "百万美元", "月", "美国经济分析局", "#c94c4c", (100_000, 10_000_000)),
    "real_nondurables": ("G010698402", "美国:2017价:个人消费支出:商品:非耐用品:折年数:季调:当月值", "实际非耐用品消费", "百万美元", "月", "美国经济分析局", "#ba7a2e", (500_000, 15_000_000)),
    "michigan": ("G002601564", "美国:密歇根大学消费者信心指数", "密歇根消费者信心", "1966年1季=100", "月", "密歇根大学", "#c94c4c", (20, 150)),
    "conference": ("G002601565", "美国:世界大型企业联合会:消费者信心指数", "咨商会消费者信心", "1985年=100", "月", "世界大型企业联合会", "#1859b8", (20, 180)),
    "revolving_credit_yoy": ("G002601177", "美国:消费循环信贷:季调:当月同比", "循环消费信贷同比", "%", "月", "美联储", "#855c9c", (-30, 50)),
    "card_delinquency": ("G022571240", "美国:拖欠率:信用卡贷款:所有商业银行:季调", "信用卡拖欠率", "%", "季", "圣路易斯联储", "#c94c4c", (0, 15)),
    "wealth_ratio": ("G017486386", "美国:家庭和非营利组织:净资产占个人可支配收入的百分比", "家庭净资产/可支配收入", "%", "年", "美联储", "#2f7fa3", (200, 1_500)),
}


def compact_date(value: Any) -> str:
    normalized = str(value).replace("-", "").replace("/", "").replace(".", "")
    if len(normalized) == 4:
        return normalized + "1231"
    if len(normalized) == 6:
        return normalized + "01"
    if len(normalized) >= 8:
        return normalized[:8]
    raise ValueError(f"invalid observation date: {value!r}")


def align_common(series_map: dict[str, tuple[list[str], list[float]]], digits: int = 6) -> tuple[list[str], dict[str, list[float]]]:
    maps = {key: {compact_date(date)[:digits]: value for date, value in zip(dates, values)} for key, (dates, values) in series_map.items()}
    periods = sorted(set.intersection(*(set(item) for item in maps.values()))) if maps else []
    return periods, {key: [item[period] for period in periods] for key, item in maps.items()}


def pct_change(dates: list[str], values: list[float], periods: int) -> tuple[list[str], list[float]]:
    rows = [(dates[index], (values[index] / values[index - periods] - 1) * 100) for index in range(periods, len(values)) if values[index - periods] != 0]
    return [date for date, _ in rows], [value for _, value in rows]


def standardize(dates: list[str], values: list[float], start: str = "201501", end: str = "201912") -> tuple[list[str], list[float]]:
    baseline = [value for date, value in zip(dates, values) if start <= compact_date(date)[:6] <= end]
    if len(baseline) < 12:
        raise ValueError("insufficient standardization baseline")
    mean = statistics.fmean(baseline)
    sd = statistics.stdev(baseline)
    if sd == 0:
        raise ValueError("zero standard deviation")
    return list(dates), [(value - mean) / sd for value in values]


def detect_missing_periods(dates: Iterable[str], frequency: str) -> list[str]:
    compact = sorted({compact_date(date) for date in dates})
    if not compact or frequency not in {"月", "季"}:
        return []
    actual = {date[:6] for date in compact}
    year, month = int(compact[0][:4]), int(compact[0][4:6])
    end_year, end_month = int(compact[-1][:4]), int(compact[-1][4:6])
    step = 1 if frequency == "月" else 3
    expected: list[str] = []
    while (year, month) <= (end_year, end_month):
        expected.append(f"{year:04d}{month:02d}")
        month += step
        if month > 12:
            month -= 12
            year += 1
    return [period for period in expected if period not in actual]


def fetch_response_series(payload: dict[str, Any], display_id: str) -> tuple[list[str], list[float]]:
    if payload.get("code") != 1:
        raise ValueError(f"iFinD rejected {display_id}: {payload.get('msg') or payload.get('code')}")
    table = next((item for item in ((payload.get("data") or {}).get("tables") or []) if str(item.get("displayid") or "") == display_id), None)
    if table is None:
        raise ValueError(f"iFinD returned no block for {display_id}")
    rows = [(compact_date(date), float(value)) for date, value in zip(table.get("time") or [], table.get("value") or []) if value not in (None, "", "--", "#N/A")]
    rows.sort(key=lambda row: row[0])
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
    result: dict[str, dict[str, Any]] = {}
    for key, spec in SERIES_SPEC.items():
        code, exact_name, _label, unit, frequency, _institution, _color, bounds = spec
        metadata = next((item for item in search_indicator(token, exact_name) if item.get("displayid") == code), None)
        if metadata is None:
            raise ValueError(f"metadata mismatch: {key} {code} not found")
        if metadata.get("name") != exact_name or (metadata.get("unit") or "") != unit or metadata.get("frequency") != frequency or metadata.get("datasource") != _institution:
            raise ValueError(f"identity mismatch for {key}: {metadata}")
        payload = fetch_indicator(token, code, START_DATE, end)
        dates, values = fetch_response_series(payload, code)
        if not all(bounds[0] <= value <= bounds[1] for value in values):
            raise ValueError(f"range check failed for {key}: {min(values)}..{max(values)}")
        result[key] = {"metadata": metadata, "payload": payload}
        print(f"verified {key}: {code} {dates[0]}..{dates[-1]} ({len(dates)})")
    return result


def source_meta(key: str, latest: str) -> dict[str, Any]:
    code, name, _label, unit, _frequency, institution, _color, _bounds = SERIES_SPEC[key]
    return {"provider": "iFinD EDB", "institution": institution, "code": code, "name": name, "rawUnit": unit, "url": "https://ft.51ifind.com", "latestObservation": latest}


def make_series(key: str, dates: list[str], values: list[float], *, series_id: str | None = None, label: str | None = None, color: str | None = None, unit: str | None = None, transform: str | None = None) -> dict[str, Any]:
    _code, _name, default_label, default_unit, frequency, _institution, default_color, _bounds = SERIES_SPEC[key]
    result = {"id": series_id or key, "label": label or default_label, "dates": dates, "values": [round(value, 4) for value in values], "color": color or default_color, "unit": default_unit if unit is None else unit, "frequency": frequency, "latestValue": round(values[-1], 4), "latestObservation": dates[-1], "source": source_meta(key, dates[-1])}
    if transform:
        result["transformLabel"] = transform
    return result


def derived_series(base_key: str, dates: list[str], values: list[float], *, series_id: str, label: str, color: str, unit: str, transform: str, source_keys: list[str]) -> dict[str, Any]:
    item = make_series(base_key, dates, values, series_id=series_id, label=label, color=color, unit=unit, transform=transform)
    item["source"]["code"] = "DERIVED:" + "+".join(SERIES_SPEC[key][0] for key in source_keys)
    item["source"]["name"] = transform
    item["source"]["rawUnit"] = "见变换说明"
    return item


def chart(chart_id: str, title: str, description: str, unit: str, series: list[dict[str, Any]], *, eyebrow: str, explanation: dict[str, str], default_range: str = "5Y", reference: float | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"id": chart_id, "kind": "line", "eyebrow": eyebrow, "title": title, "description": description, "unit": unit, "defaultRange": default_range, "series": series, "explanation": explanation}
    if reference is not None:
        result["reference"] = reference
    return result


def build_dataset(raw: dict[str, dict[str, Any]], raw_snapshot: str) -> dict[str, Any]:
    parsed = {key: fetch_response_series(item["payload"], SERIES_SPEC[key][0]) for key, item in raw.items()}

    share_dates, share_values = align_common({"gdp": parsed["nominal_gdp"], "pce": parsed["nominal_pce_q"]})
    pce_gdp_share = [pce / gdp * 100 for pce, gdp in zip(share_values["pce"], share_values["gdp"])]

    retail_dates, retail = align_common({key: parsed[key] for key in ("retail_total", "retail_auto", "retail_gas", "retail_building", "retail_foodservice")})
    control_level = [retail["retail_total"][i] - retail["retail_auto"][i] - retail["retail_gas"][i] - retail["retail_building"][i] - retail["retail_foodservice"][i] for i in range(len(retail_dates))]
    total_mom = pct_change(retail_dates, retail["retail_total"], 1)
    control_mom = pct_change(retail_dates, control_level, 1)
    total_yoy = pct_change(retail_dates, retail["retail_total"], 12)
    control_yoy = pct_change(retail_dates, control_level, 12)

    price_dates, price_values = align_common({"retail": parsed["retail_total"], "cpi": parsed["cpi_index"]})
    real_retail_level = [retail / cpi * 100 for retail, cpi in zip(price_values["retail"], price_values["cpi"])]
    nominal_retail_yoy = pct_change(price_dates, price_values["retail"], 12)
    real_retail_yoy = pct_change(price_dates, real_retail_level, 12)

    real_pce_yoy = pct_change(*parsed["real_pce"], 12)
    income_dates, income_values = align_common({"dpi": parsed["real_dpi_yoy"], "pce": real_pce_yoy})

    structure_dates, structure = align_common({key: parsed[key] for key in ("nominal_pce", "nominal_services", "nominal_durables", "nominal_nondurables")})
    structure_series = []
    for key, label, color in (("nominal_services", "服务占比", "#1859b8"), ("nominal_nondurables", "非耐用品占比", "#ba7a2e"), ("nominal_durables", "耐用品占比", "#c94c4c")):
        values = [component / total * 100 for component, total in zip(structure[key], structure["nominal_pce"])]
        structure_series.append(derived_series(key, structure_dates, values, series_id=f"{key}_share", label=label, color=color, unit="%", transform="分项名义PCE÷名义PCE总额×100", source_keys=[key, "nominal_pce"]))

    real_component_series = []
    for key, label, color in (("real_services", "服务实际同比", "#1859b8"), ("real_nondurables", "非耐用品实际同比", "#ba7a2e"), ("real_durables", "耐用品实际同比", "#c94c4c")):
        dates, values = pct_change(*parsed[key], 12)
        real_component_series.append(make_series(key, dates, values, series_id=f"{key}_yoy", label=label, color=color, unit="%", transform="由2017价月度水平计算12个月同比"))

    michigan_z = standardize(*parsed["michigan"])
    conference_z = standardize(*parsed["conference"])
    pce_z = standardize(*real_pce_yoy)

    charts = {
        "anchor": [
            chart("pce-gdp-share", "消费占名义GDP的比重", "PCE占名义GDP的季度份额；用于刻画体量，不把份额上升机械解释为消费绝对额加速。", "%名义GDP", [derived_series("nominal_pce_q", share_dates, pce_gdp_share, series_id="pce_gdp_share", label="消费占GDP", color="#1859b8", unit="%", transform="名义个人消费支出÷名义GDP×100", source_keys=["nominal_pce_q", "nominal_gdp"])], eyebrow="4.1 · ANCHOR", default_range="ALL", explanation={"what": "个人消费支出在名义GDP中的份额。", "howToRead": "美国消费长期约占GDP三分之二，是经济压舱石；消费明显走弱更偏确认信号。", "caveat": "份额可因投资等其他分项下降更快而上升，不能替代消费增速。", "pptSlide": "PPT第115页 · 图4-1"}),
            chart("income-consumption", "实际收入与实际消费", "把当期购买力与真实支出并列；消费强于收入时，差额需由储蓄下降、资产收益或信贷弥补。", "%同比", [make_series("real_dpi_yoy", income_dates, income_values["dpi"], series_id="real_dpi_yoy_aligned"), make_series("real_pce", income_dates, income_values["pce"], series_id="real_pce_yoy", label="实际PCE同比", unit="%", transform="由2017价PCE水平计算12个月同比")], eyebrow="4.1 · INCOME DRIVER", explanation={"what": "实际可支配收入同比与实际PCE同比。", "howToRead": "收入是四个驱动轮中最稳定的一轮；消费持续跑赢收入时要检查储蓄与信贷。", "caveat": "两条BEA序列会随国民账户修订；短期转移支付可令收入剧烈跳变。", "pptSlide": "PPT第114、121页 · 图4-4左"}),
        ],
        "retail": [
            chart("retail-control-mom", "总零售与控制组环比", "控制组由总计剔除汽车、加油站、建材及园林、餐饮；减少供给、价格与天气噪音。", "%环比", [make_series("retail_total", *total_mom, series_id="retail_total_mom", label="总零售环比", unit="%", transform="由季调水平计算1个月环比"), derived_series("retail_total", *control_mom, series_id="retail_control_mom", label="控制组环比", color="#1859b8", unit="%", transform="(总计−汽车−加油站−建材园林−餐饮)水平计算1个月环比", source_keys=["retail_total", "retail_auto", "retail_gas", "retail_building", "retail_foodservice"])], eyebrow="4.2 · RETAIL CONTROL", reference=0, explanation={"what": "Census零售总计及研究者按标准排除项重建的控制组。", "howToRead": "控制组更接近直接进入PCE商品核算的基础趋势，单月极端值仍需结合修正。", "caveat": "全部是名义值；汽车、汽油、建材在极端月份仍应与控制组对照读。", "pptSlide": "PPT第117—118页 · 图4-3左"}),
            chart("retail-control-yoy", "总零售与控制组同比", "以同比观察中期方向，避免只用高噪音单月环比判断消费趋势。", "%同比", [make_series("retail_total", *total_yoy, series_id="retail_total_yoy", label="总零售同比", unit="%", transform="由季调水平计算12个月同比"), derived_series("retail_total", *control_yoy, series_id="retail_control_yoy", label="控制组同比", color="#1859b8", unit="%", transform="控制组派生水平计算12个月同比", source_keys=["retail_total", "retail_auto", "retail_gas", "retail_building", "retail_foodservice"])], eyebrow="4.2 · RETAIL TREND", reference=0, default_range="10Y", explanation={"what": "总零售和控制组的12个月同比。", "howToRead": "方向一致时消费商品端信号较稳；背离时先定位汽车、油价、天气或餐饮。", "caveat": "同比仍是名义口径且包含基数效应；控制组不是完整PCE。", "pptSlide": "PPT第118页 · 图4-3右"}),
            chart("nominal-real-retail", "名义零售与CPI实际化零售", "按PPT方法用当月季调CPI指数近似平减零售总额，检查金额增长是否只是价格上涨。", "%同比", [make_series("retail_total", *nominal_retail_yoy, series_id="nominal_retail_yoy", label="名义零售同比", color="#c94c4c", unit="%", transform="季调零售水平计算12个月同比"), derived_series("retail_total", *real_retail_yoy, series_id="real_retail_yoy", label="CPI实际化零售同比", color="#1859b8", unit="%", transform="零售总额÷季调CPI指数后计算12个月同比", source_keys=["retail_total", "cpi_index"])], eyebrow="4.2 · NOMINAL VS REAL", reference=0, default_range="10Y", explanation={"what": "名义零售同比与用总体CPI近似平减后的实际同比。", "howToRead": "两者裂口扩大说明价格贡献上升；2022年名义强、实际近停滞是典型。", "caveat": "总体CPI不是零售专属平减指数，因此只是实时近似，不冒充BEA实际PCE。", "pptSlide": "PPT第119页 · 图4-2"}),
        ],
        "income": [
            chart("saving-rate", "个人储蓄率", "收入减消费后的残差；用于判断消费缓冲，但绝对水平会随收入和支出两侧修订而重写。", "%可支配收入", [make_series("saving_rate", *parsed["saving_rate"])], eyebrow="4.2 · SAVING RESIDUAL", default_range="ALL", explanation={"what": "BEA个人储蓄占可支配收入比重。", "howToRead": "消费跑赢收入且储蓄率下降，说明家庭在降低缓冲；重点看趋势和拐点。", "caveat": "储蓄率是两个大数相减的残差，年度综合修订可整体平移历史。", "pptSlide": "PPT第121页 · 图4-4右"}),
            chart("credit-stress", "循环信贷与信用卡拖欠率", "信贷扩张可短期替代收入，拖欠率则用于识别总量稳定之下的结构裂缝。", "%", [make_series("revolving_credit_yoy", *parsed["revolving_credit_yoy"]), make_series("card_delinquency", *parsed["card_delinquency"])], eyebrow="4.1/4.4 · CREDIT DRIVER", reference=0, default_range="10Y", explanation={"what": "G.19循环消费信贷同比与商业银行信用卡季调拖欠率。", "howToRead": "信贷增速回升可支撑短期消费；拖欠率上行提示低MPC群体之外的压力扩散。", "caveat": "月频增速与季频拖欠率不同步；信用卡余额增加也可能反映支付方式迁移。", "pptSlide": "PPT第113—114、128页 · 四驱动轮与总量/结构背离"}),
        ],
        "structure": [
            chart("consumption-shares", "PCE结构：体量看服务", "名义PCE内部的服务、非耐用品和耐用品份额。", "%消费支出", structure_series, eyebrow="4.2 · CONSUMPTION MIX", default_range="ALL", explanation={"what": "三大PCE分项占名义PCE总额的比重。", "howToRead": "服务决定体量；耐用品虽小，却更适合识别周期拐点。", "caveat": "名义份额同时受数量与相对价格影响；不能与实际链式美元直接加总。", "pptSlide": "PPT第122页 · 图4-10左"}),
            chart("consumption-volatility", "实际消费结构：波动看耐用品", "用2017价月度水平计算服务、非耐用品和耐用品同比。", "%同比", real_component_series, eyebrow="4.2 · CYCLICAL AMPLIFIER", reference=0, default_range="10Y", explanation={"what": "服务、非耐用品和耐用品的实际PCE同比。", "howToRead": "耐用品可推迟、利率敏感且依赖信贷，通常是消费内部波动最大的分项。", "caveat": "疫情期服务与商品替代造成异常波动；不要把一次性重启效应外推。", "pptSlide": "PPT第122页 · 图4-10右"}),
        ],
        "sentiment": [
            chart("confidence-standardized", "两大消费者信心调查", "为解决1966Q1=100与1985=100不可直接比较，两条指数均按2015—2019均值和标准差转为z分数。", "标准差", [make_series("michigan", *michigan_z, series_id="michigan_z", label="密歇根信心z分数", unit="σ", transform="以2015—2019为均值0、标准差1"), make_series("conference", *conference_z, series_id="conference_z", label="咨商会信心z分数", unit="σ", transform="以2015—2019为均值0、标准差1")], eyebrow="4.3 · TWO SURVEYS", reference=0, default_range="10Y", explanation={"what": "密歇根更偏个人财务与物价体感，咨商会更偏就业市场现况。", "howToRead": "两者同跌才是广泛情绪转弱；劈叉时先区分通胀体感和劳动力市场感知。", "caveat": "标准化只解决量纲，不消除样本、问法、党派和调查模式差异。", "pptSlide": "PPT第125页"}),
            chart("soft-hard-divergence", "软数据与实际消费", "将密歇根信心与实际PCE同比均按2015—2019标准化，直接观察情绪与真实支出的背离。", "标准差", [make_series("michigan", *michigan_z, series_id="michigan_soft_z", label="密歇根信心z分数", unit="σ", transform="以2015—2019为均值0、标准差1"), make_series("real_pce", *pce_z, series_id="real_pce_growth_z", label="实际PCE同比z分数", color="#1859b8", unit="σ", transform="先计算12个月同比，再以2015—2019为均值0、标准差1")], eyebrow="4.4 · SOFT VS HARD", reference=0, default_range="10Y", explanation={"what": "同一标准化尺度上的调查情绪与实际消费增速。", "howToRead": "信心崩而实际PCE仍稳是vibecession；消费拐点要由硬数据确认。", "caveat": "z分数只表示偏离各自基准的幅度，不是百分点；相关性不等于领先或因果。", "pptSlide": "PPT第127页 · 图4-6"}),
        ],
    }

    latest = {key: {"value": values[-1], "date": dates[-1]} for key, (dates, values) in parsed.items()}
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "iFinD EDB",
        "sourceProviders": ["iFinD EDB"],
        "frameworkSource": {"file": "研究框架/美国宏观数据培训【0829定稿】.pptx", "slides": "112—129", "routeSlide": 113},
        "routeMap": [
            {"id": "framework", "title": "分析框架", "subtitle": "四个驱动轮", "nodes": [{"title": "收入·财富·信贷·预期", "detail": "再乘MPC异质性"}, {"title": "消费平滑", "detail": "拐点偏确认，不是领先"}, {"title": "主线", "detail": "双轨数据+三大背离"}]},
            {"id": "official", "title": "官方双轨", "subtitle": "快窄 vs 慢全", "nodes": [{"title": "零售销售", "detail": "快、窄、名义；控制组直送GDP"}, {"title": "个人收支", "detail": "慢、全、可实际化；储蓄率为残差"}]},
            {"id": "high-frequency", "title": "第三方与高频", "subtitle": "补服务统计滞后", "nodes": [{"title": "刷卡", "detail": "看方向和分组差，不看水平"}, {"title": "服务高频", "detail": "TSA / OpenTable"}, {"title": "信心调查", "detail": "密歇根偏物价，咨商会偏就业"}]},
            {"id": "divergence", "title": "三大背离", "subtitle": "先辨口径", "nodes": [{"title": "软 vs 硬", "detail": "信心崩、支出稳；信硬数据"}, {"title": "名义 vs 实际", "detail": "通胀期先实际化"}, {"title": "总量 vs 结构", "detail": "K型分化先见于信贷"}]},
            {"id": "case", "title": "案例复盘", "subtitle": "拒绝伪精确", "nodes": [{"title": "超额储蓄之辩", "detail": "趋势线假设决定耗尽日，不可机械交易"}]},
        ],
        "dataPassports": [
            {"id": "retail", "title": "零售销售", "producer": "Census Advance Monthly Retail Trade Survey", "frequency": "月；参考月后约两周", "coverage": "商品+餐饮，约占消费1/3", "revision": "随后两个月+年度基准修订", "use": "最快消费硬数据；控制组输入PCE商品", "pitfall": "全部为名义值；初值样本小、噪音和修订较大", "pptSlide": "第117—119页"},
            {"id": "pio", "title": "个人收入与支出", "producer": "BEA整合工资、零售与服务外推", "frequency": "月末发布上月", "coverage": "商品+服务+收入分解+储蓄率+PCE价格", "revision": "随国民账户反复修订", "use": "完整实际消费与实际收入", "pitfall": "发布时零售/CPI已出；储蓄率是残差", "pptSlide": "第120—122页"},
            {"id": "credit", "title": "消费信贷", "producer": "美联储G.19与银行监管数据", "frequency": "月/季", "coverage": "循环信贷与商业银行信用卡拖欠", "revision": "不同发布日、不同机构覆盖", "use": "收入替代与结构压力", "pitfall": "余额增加可由现金向卡迁移，不等于真实消费增加", "pptSlide": "第113—114、128页"},
            {"id": "confidence", "title": "消费者信心", "producer": "密歇根大学 / 世界大型企业联合会", "frequency": "月", "coverage": "个人财务与物价 / 就业现况与预期", "revision": "初值、终值及方法调整", "use": "预期与风险感知", "pitfall": "党派、汽油价、问法和样本构成污染水平", "pptSlide": "第125—127页"},
        ],
        "headline": [
            {"id": "share", "label": "压舱石", "title": "消费占名义GDP", "value": round(pce_gdp_share[-1], 2), "unit": "%", "observation": share_dates[-1], "source": "iFinD EDB"},
            {"id": "real-pce", "label": "硬消费", "title": "实际PCE同比", "value": round(real_pce_yoy[1][-1], 2), "unit": "%", "observation": real_pce_yoy[0][-1], "source": "iFinD EDB"},
            {"id": "income", "label": "收入轮", "title": "实际可支配收入同比", "value": round(latest["real_dpi_yoy"]["value"], 2), "unit": "%", "observation": latest["real_dpi_yoy"]["date"], "source": "iFinD EDB"},
            {"id": "saving", "label": "储蓄缓冲", "title": "个人储蓄率", "value": round(latest["saving_rate"]["value"], 2), "unit": "%", "observation": latest["saving_rate"]["date"], "source": "iFinD EDB"},
            {"id": "credit", "label": "信贷轮", "title": "循环信贷同比", "value": round(latest["revolving_credit_yoy"]["value"], 2), "unit": "%", "observation": latest["revolving_credit_yoy"]["date"], "source": "iFinD EDB"},
            {"id": "wealth", "label": "财富轮", "title": "净资产/可支配收入", "value": round(latest["wealth_ratio"]["value"], 1), "unit": "%", "observation": latest["wealth_ratio"]["date"], "source": "iFinD EDB"},
        ],
        "drivers": [
            {"id": "income", "title": "收入", "mechanism": "劳动收入≈就业×时薪×工时", "signal": "实际可支配收入同比", "status": f"{latest['real_dpi_yoy']['value']:.1f}% · {latest['real_dpi_yoy']['date'][:6]}", "note": "转移支付和税收可令月度收入跳变"},
            {"id": "wealth", "title": "财富", "mechanism": "股市+房价经财富效应影响支出", "signal": "净资产/可支配收入", "status": f"{latest['wealth_ratio']['value']:.1f}% · {latest['wealth_ratio']['date'][:4]}", "note": "iFinD可核验序列为年频，不能伪装成实时财富信号"},
            {"id": "credit", "title": "信贷", "mechanism": "循环信贷可短期替代收入", "signal": "循环信贷同比 / 信用卡拖欠率", "status": f"{latest['revolving_credit_yoy']['value']:.1f}% / {latest['card_delinquency']['value']:.2f}%", "note": "余额增长与消费增长不可等同"},
            {"id": "expectations", "title": "预期", "mechanism": "预防性储蓄先响应失业恐惧", "signal": "密歇根 / 咨商会信心", "status": f"{latest['michigan']['value']:.1f} / {latest['conference']['value']:.1f}", "note": "两指数基期不同，原始水平不可横向比"},
        ],
        "sections": {
            "anchor": {"title": "压舱石与四驱动轮", "description": "先确认消费体量，再检查收入、财富、信贷和预期；MPC异质性决定同样冲击落在不同家庭后的总量效果。", "charts": charts["anchor"]},
            "retail": {"title": "官方快轨：零售销售", "description": "先看控制组，再把名义零售实际化；速度优势不能抵消覆盖窄、初值噪音和修订风险。", "charts": charts["retail"]},
            "income": {"title": "官方慢轨：个人收支与信用", "description": "BEA补齐服务、收入和储蓄；信贷数据用来判断消费是否在透支未来或出现结构裂缝。", "charts": charts["income"]},
            "structure": {"title": "消费结构：体量看服务，波动看耐用品", "description": "名义份额解释结构，实际增速解释周期；两种口径不能混为一谈。", "charts": charts["structure"]},
            "sentiment": {"title": "预期与软硬背离", "description": "区分密歇根的物价体感与咨商会的就业感知，并用实际PCE约束情绪叙事。", "charts": charts["sentiment"]},
        },
        "highFrequency": [
            {"name": "BofA刷卡", "frequency": "周/月", "coverage": "约7000万户内部账户；可分收入组与品类", "use": "看方向与分组差", "status": "未接入", "caveat": "私人样本、名义口径；不以iFinD替代"},
            {"name": "TSA安检人数", "frequency": "日", "coverage": "航空出行", "use": "服务消费即时确认", "status": "未接入", "caveat": "节假日错位需看7日均"},
            {"name": "OpenTable订座", "frequency": "日", "coverage": "餐饮", "use": "面对面服务热度", "status": "未接入", "caveat": "天气与平台覆盖偏差"},
            {"name": "Redbook", "frequency": "周", "coverage": "大型连锁同店销售", "use": "零售方向交叉验证", "status": "未接入", "caveat": "商业订阅；同店不等于总消费"},
        ],
        "caseStudy": {"title": "超额储蓄：同一数据、两条趋势线、两个“耗尽日”", "summary": "PPT示例中，按2016—2019线性趋势外推得到约2025-01耗尽；锁定2019储蓄率均值则约2026-02耗尽，相差约13个月。", "formula": "累计超额储蓄＝实际储蓄－反事实储蓄路径的累计差", "caveat": "这是一项对反事实高度敏感的历史案例，不是iFinD可自动更新的官方序列；页面保留方法和结论，不把PPT静态值冒充实时指标。", "pptSlide": "PPT第129页 · 图4-5"},
        "availability": [
            {"id": "party", "label": "密歇根分党派信心", "status": "not-integrated", "explanation": "PPT第126页来自Michigan Table 5b；iFinD EDB未检出对应分党派序列，不用总指数替代。"},
            {"id": "high-frequency", "label": "刷卡与服务高频", "status": "not-integrated", "explanation": "BofA、TSA、OpenTable和Redbook不属于本次iFinD EDB自动更新合同；逐项保留覆盖与局限。"},
            {"id": "excess-saving", "label": "超额储蓄耗尽日", "status": "historical-case", "explanation": "取决于反事实趋势线，保留为PPT历史案例，不作为可交易实时指标。"},
        ],
        "dataQuality": {
            "missingPeriods": {key: detect_missing_periods(dates, SERIES_SPEC[key][4]) for key, (dates, _values) in parsed.items() if SERIES_SPEC[key][4] in {"月", "季"}},
            "accountingChecks": {
                "latestControlPositive": control_level[-1] > 0,
                "latestPceComponentShareSum": round(sum(series["values"][-1] for series in structure_series), 6),
                "latestPceGdpShare": round(pce_gdp_share[-1], 6),
            },
            "note": "23条源序列逐条核验指标码、精确名称、单位、频率与合理区间；派生控制组、实际化零售、份额、同比和z分数均由脚本确定性重建。",
        },
        "researchBasis": ["页面按PPT第四章第112—129页路线图、数据说明与图例重建。", "PPT定义研究顺序与解释；所有可更新时序均由iFinD EDB重新提取，静态案例和不可得项明确隔离。"],
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
        raw_path = args.raw_dir / f"{stamp}_ifind_consumption.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        snapshot = raw_path.relative_to(REPO_ROOT).as_posix()
    dataset = build_dataset(raw, snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    chart_count = sum(len(section["charts"]) for section in dataset["sections"].values())
    print(f"wrote {args.output} ({chart_count} charts, {len(SERIES_SPEC)} verified source series)")


if __name__ == "__main__":
    main()
