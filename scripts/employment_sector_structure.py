"""BLS CES all-employee SA levels -> complete non-overlapping monthly flows.

Classification: https://www.bls.gov/webapps/legacy/cesbtab1.htm
Aggregation: https://www.bls.gov/web/empsit/cesfaq.htm
CES (not CEU) identifies seasonal adjustment; data type 01 is all employees,
THOUSANDS, not hourly earnings (03) or production/nonsupervisory employees.
"""
from __future__ import annotations

import json
import math
import statistics
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
# id, label, BLS series, parent, published level resolution (thousand jobs).
SECTORS = (
    ("payroll_total", "非农总计", "CES0000000001", None, 1),
    ("payroll_private", "私营部门总计", "CES0500000001", "payroll_total", 1),
    ("payroll_goods", "商品生产", "CES0600000001", "payroll_private", 1),
    ("sector_mining", "采矿与伐木", "CES1000000001", "payroll_goods", 1),
    ("sector_construction", "建筑业", "CES2000000001", "payroll_goods", 1),
    ("sector_manufacturing", "制造业", "CES3000000001", "payroll_goods", 1),
    ("payroll_services", "私人服务", "CES0800000001", "payroll_private", 1),
    ("sector_wholesale", "批发业", "CES4142000001", "payroll_services", 0.1),
    ("sector_retail", "零售业", "CES4200000001", "payroll_services", 0.1),
    ("sector_transport", "运输仓储", "CES4300000001", "payroll_services", 0.1),
    ("sector_utilities", "公用事业", "CES4422000001", "payroll_services", 0.1),
    ("sector_information", "信息业", "CES5000000001", "payroll_services", 1),
    ("sector_financial", "金融活动", "CES5500000001", "payroll_services", 1),
    ("sector_professional", "专业商业服务", "CES6000000001", "payroll_services", 1),
    ("sector_education_health", "私人教育与医疗服务", "CES6500000001", "payroll_services", 1),
    ("sector_leisure", "休闲与酒店业", "CES7000000001", "payroll_services", 1),
    ("sector_other", "其他服务", "CES8000000001", "payroll_services", 1),
    ("payroll_government", "政府总计", "CES9000000001", "payroll_total", 1),
    ("sector_federal", "联邦政府", "CES9091000001", "payroll_government", 1),
    ("sector_state", "州政府", "CES9092000001", "payroll_government", 1),
    ("sector_local", "地方政府", "CES9093000001", "payroll_government", 1),
)
BASELINE_PERIODS = [f"{year}{month:02d}" for year in (2018, 2019) for month in range(1, 13)]


class ReconciliationError(ValueError):
    """Carries candidate residuals so failed refreshes remain auditable."""
    def __init__(self, message, reconciliation):
        super().__init__(message)
        self.reconciliation = reconciliation


def shift_month(period, offset):
    ordinal = int(period[:4]) * 12 + int(period[4:]) - 1 + offset
    year, month = divmod(ordinal, 12)
    return f"{year:04d}{month + 1:02d}"


def fetch_sector_levels(end_year=None):
    """Fetch fixed baseline and recent years, never lose baseline to rolling API cap.

    Each request includes every industry. Responses are a single refresh batch;
    separate disjoint date windows avoid both the 10-year cap and vintage mixing.
    """
    end_year = end_year or datetime.now(timezone.utc).year
    windows = [(2017, end_year)] if end_year <= 2026 else [(2017, 2019), (max(2020, end_year - 2), end_year)]
    bundle = {"provider": "BLS Public Data API", "fetchedAt": datetime.now(timezone.utc).isoformat(), "responses": []}
    for start, end in windows:
        body = {"seriesid": [s[2] for s in SECTORS], "startyear": str(start), "endyear": str(end)}
        request = urllib.request.Request(BLS_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "macro-research-dashboard/0.1"}, method="POST")
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        bundle["responses"].append({"request": body, "response": payload})
    return bundle


def parse_sector_levels(bundle):
    expected = {s[2] for s in SECTORS}
    resolution = {s[2]: Decimal(str(s[4])) for s in SECTORS}
    levels = {code: {} for code in expected}
    responses = bundle.get("responses", [{"response": bundle}])
    if not responses:
        raise ValueError("BLS employment response bundle is empty")
    for batch in responses:
        payload = batch["response"]
        if payload.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError(f"BLS employment request failed: {payload.get('message')}")
        seen = set()
        for series in payload.get("Results", {}).get("series", []):
            code = series.get("seriesID")
            if code not in expected or code in seen:
                raise ValueError(f"Unexpected or duplicate BLS employment identity: {code}")
            seen.add(code)
            for point in series.get("data", []):
                period = point.get("period", "")
                if period == "M13":
                    continue
                if period not in {f"M{i:02d}" for i in range(1, 13)}:
                    raise ValueError(f"Invalid BLS monthly period: {period}")
                month = f"{int(point['year']):04d}{period[1:]}"
                value = Decimal(str(point["value"]))
                if not value.is_finite() or not 0 < value < 300_000:
                    raise ValueError(f"BLS employment range check failed: {code} {month}")
                if value % resolution[code] != 0:
                    raise ValueError(f"Unexpected BLS employment precision: {code} {month}: {value}")
                if month in levels[code]:
                    raise ValueError(f"Duplicate BLS employment month: {code} {month}")
                levels[code][month] = value
        if seen != expected:
            raise ValueError(f"Missing BLS employment series: {sorted(expected - seen)}")
    return levels


def build_sector_monitor(bundle, payroll_dates, payroll_values, raw_snapshot):
    levels = parse_sector_levels(bundle)
    if len(payroll_dates) != len(payroll_values):
        raise ValueError("Payroll dates and values are misaligned")
    payroll = {}
    for date, value in zip(payroll_dates, payroll_values):
        period = date.replace("-", "")[:6]
        if period in payroll or not math.isfinite(value):
            raise ValueError(f"Invalid or duplicate payroll observation: {period}")
        payroll[period] = value
    if not payroll:
        raise ValueError("Missing payroll comparison")
    periods = [shift_month(max(payroll), -i) for i in range(12)]
    required = set(periods + BASELINE_PERIODS)
    changes = {}
    for key, _label, code, _parent, _resolution in SECTORS:
        values = levels[code]
        missing = sorted({p for p in required if p not in values or shift_month(p, -1) not in values})
        if missing:
            raise ValueError(f"Missing contiguous monthly levels for {code}: {missing}")
        changes[key] = {p: float(values[p] - values[shift_month(p, -1)]) for p in required}
    missing_chart = sorted(required - payroll.keys())
    if missing_chart:
        raise ValueError(f"Missing monthly payroll comparison: {missing_chart}")

    parents = {s[0]: s[3] for s in SECTORS}
    resolution = {s[0]: s[4] for s in SECTORS}
    private_leaves = [s[0] for s in SECTORS if s[3] in ("payroll_goods", "payroll_services")]
    government_leaves = [s[0] for s in SECTORS if s[3] == "payroll_government"]
    relations = [
        ("private-leaves", "私营叶子行业－私营总计", private_leaves, "payroll_private"),
        ("government-leaves", "联邦＋州＋地方－政府总计", government_leaves, "payroll_government"),
        ("nonfarm-total", "私营＋政府－非农总计", ["payroll_private", "payroll_government"], "payroll_total"),
        ("goods-subtotal", "商品生产叶子－商品生产小计", [s[0] for s in SECTORS if s[3] == "payroll_goods"], "payroll_goods"),
        ("services-subtotal", "私人服务叶子－私人服务小计", [s[0] for s in SECTORS if s[3] == "payroll_services"], "payroll_services"),
        ("private-subtotals", "商品生产＋私人服务－私营总计", ["payroll_goods", "payroll_services"], "payroll_private"),
    ]

    def checks_for(months):
        checks = []
        for check_id, label, children, parent in relations:
            # Each rounded level has error <= resolution / 2. A month difference
            # uses TWO levels, so its maximum error is resolution (not / 2).
            tolerance = round(sum(resolution[k] for k in children) + resolution[parent], 1)
            checks.append({"id": check_id, "label": label, "values": [round(sum(changes[k][p] for k in children) - changes[parent][p], 1) for p in months], "tolerance": tolerance})
        checks.append({"id": "table-vs-payroll", "label": "表中非农－iFinD月度柱（跨源修订差额）", "values": [round(changes["payroll_total"][p] - payroll[p], 4) for p in months], "tolerance": 0})
        return checks

    reconciliation = {
        "checks": checks_for(periods),
        "baselinePeriods": BASELINE_PERIODS,
        "baselineChecks": checks_for(BASELINE_PERIODS),
        "note": "差额单位：千人。容差为发布水平舍入导致的最坏界：月差涉及两期，容差=各子项水平最小刻度之和+父项刻度；总量/超级行业为1千人，批发/零售/运输仓储/公用事业为0.1千人。私营叶子10.4、政府4、私营+政府3、商品4、服务7.4、私营小计3千人；跨源图表必须严格为0。超标拒绝更新，不倒填其他行业；2018—19逐月同样验收。",
    }
    violations = [(c["id"], max(map(abs, c["values"])), c["tolerance"]) for group in ("checks", "baselineChecks") for c in reconciliation[group] if any(abs(v) > c["tolerance"] + 1e-9 for v in c["values"])]
    if violations:
        raise ReconciliationError(f"Employment reconciliation failed: {violations}", reconciliation)
    rows = []
    for key, label, code, parent, _resolution in SECTORS:
        depth = 0
        ancestor = parent
        while ancestor is not None:
            depth += 1
            ancestor = parents[ancestor]
        rows.append({
            "id": key, "label": label, "parentId": parent, "depth": depth,
            "rowType": "total" if parent is None else "subtotal" if key in parents.values() else "detail",
            "values": [changes[key][p] for p in periods],
            "recent12mAverage": round(statistics.fmean(changes[key][p] for p in periods), 2),
            "baseline2018To2019": round(statistics.fmean(changes[key][p] for p in BASELINE_PERIODS), 2),
            "source": {"provider": "BLS Public Data API", "institution": "U.S. Bureau of Labor Statistics", "code": code, "name": f"All employees, thousands, seasonally adjusted: {label}", "rawUnit": "千人", "url": f"https://data.bls.gov/timeseries/{code}", "latestObservation": max(levels[code]), "transform": "当月季调全体雇员水平减前一连续月份水平", "rawSnapshot": raw_snapshot},
        })
    return {"title": "行业就业广度与结构表", "description": "完整私营行业与联邦、州、地方政府；最近12个月月增量与2018—2019完整24个月基准。", "periods": periods, "rows": rows, "unit": "千人", "decimals": 1, "codeLabel": "BLS CES序列", "recentLabel": "近12月平均月增", "baselineLabel": "2018—19月均增量", "note": "BLS同批次CES全体雇员季调水平按连续月份差分。父级总计/小计与叶子行业分层展示，不重复加总；私人教育医疗不含政府教育，州/地方政府不再叠加教育细项。只允许官方发布水平舍入残差，逐月差额另列；非农总计与上方iFinD月度柱严格匹配，不与3个月均线比较。缺月拒绝更新，不缩短均值分母。", "reconciliation": reconciliation, "source": {"provider": "BLS Public Data API", "url": "https://www.bls.gov/ces/", "rawSnapshot": raw_snapshot, "fetchedAt": bundle.get("fetchedAt"), "classificationUrl": "https://www.bls.gov/webapps/legacy/cesbtab1.htm", "aggregationUrl": "https://www.bls.gov/web/empsit/cesfaq.htm"}}
