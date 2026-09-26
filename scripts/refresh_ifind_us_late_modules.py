"""Build PPT chapters 5-9 US macro workspaces from verified iFinD EDB series.

The output powers Housing, Business Investment, PMI, Fiscal/Treasury and
Federal Reserve/Financial Conditions. Provider responses are cached so the
build can be replayed without a live session. The local iFinD token is never
persisted.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.refresh_ifind_us_consumption import (
    compact_date,
    detect_missing_periods,
    fetch_indicator,
    fetch_response_series,
    read_token,
    search_indicator,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "src" / "data" / "usLateModulesData.json"
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "ifind-us-late-modules"

# code, exact name, label, unit, frequency, institution, color, bounds, start
Spec = tuple[str, str, str, str, str, str, str, tuple[float, float], str]
SERIES_SPEC: dict[str, Spec] = {
    # Chapter 5 · Housing
    "mortgage30": ("G002601698", "美国:30年期抵押贷款固定利率", "30年固定房贷利率", "%", "周", "房地美", "#da1e28", (0, 25), "1990-01-01"),
    "nahb": ("G019744864", "美国:全美住宅建筑商协会(NAHB)/富国银行住房市场指数:季调:当月值", "NAHB住房市场指数", "", "月", "全美地产经纪商协会", "#6929c4", (0, 100), "1990-01-01"),
    "permits": ("G002601863", "美国:已获得批准的新建私人住宅:折年数", "营建许可", "千套", "月", "美国人口普查局", "#007d79", (300, 3500), "1990-01-01"),
    "starts": ("G002601889", "美国:已开工的新建私人住宅:折年数", "新屋开工", "千套", "月", "美国人口普查局", "#0f62fe", (300, 3500), "1990-01-01"),
    "starts_single": ("G002601890", "美国:已开工的新建私人住宅:折年数:1单元", "单户开工", "千套", "月", "美国人口普查局", "#0f62fe", (100, 2500), "1990-01-01"),
    "starts_multi": ("G002601903", "美国:已开工的新建私人住宅:5单元以上", "多户开工", "千套", "月", "美国人口普查局", "#9f1853", (0, 1500), "1990-01-01"),
    "new_sales": ("G002601721", "美国:新建住房销售:折年数:季调:当月值", "新屋销售", "千套", "月", "美国人口普查局", "#0f62fe", (100, 2000), "1990-01-01"),
    "existing_sales": ("G002601743", "美国:成屋销售:季调:折年数", "成屋销售", "万套", "月", "全美地产经纪商协会", "#da1e28", (100, 1000), "1999-01-01"),
    "new_supply": ("G002601737", "美国:新建住房月度供给(以目前的销售率)", "新屋库存月数", "月", "月", "美国人口普查局", "#0f62fe", (0, 30), "1990-01-01"),
    "existing_supply": ("G002601746", "美国:成屋月度供给", "成屋库存月数", "月", "月", "全美地产经纪商协会", "#da1e28", (0, 30), "1999-01-01"),
    "fhfa_yoy": ("G003590411", "美国:FHFA房价指数:季调:当月同比", "FHFA房价同比", "%", "月", "美国联邦住房金融局", "#0f62fe", (-30, 40), "1992-01-01"),
    "cs_yoy": ("G002601681", "美国:标准普尔/CS房价指数:20个大中城市:当月同比", "Case-Shiller 20城同比", "%", "月", "标准普尔", "#6929c4", (-30, 40), "2001-01-01"),
    "mortgage_delinquency": ("G022571288", "美国:拖欠率:住房抵押贷款:所有商业银行:季调", "住房抵押贷款拖欠率", "%", "季", "圣路易斯联储", "#da1e28", (0, 20), "1990-01-01"),
    # Chapter 6 · Business investment
    "core_orders": ("G003592403", "美国:耐用品:新订单:季调:资本货物:非国防资本货物(不含飞机)", "核心资本品订单", "百万美元", "月", "美国人口普查局", "#0f62fe", (20_000, 200_000), "2002-01-01"),
    "core_shipments": ("G003592309", "美国:耐用品:出货量:季调:资本货物:非国防资本货物(不含飞机)", "核心资本品出货", "百万美元", "月", "美国人口普查局", "#007d79", (20_000, 200_000), "2002-01-01"),
    "capacity_util": ("G002601612", "美国:产能利用率:全部工业部门:季调", "工业产能利用率", "%", "月", "美联储", "#9f1853", (40, 100), "1990-01-01"),
    "inv_structures_growth": ("G005120886", "美国:GDP:不变价:支出法:国内私人投资:固定投资:非住宅类:建筑:环比折年率:季调:当季值", "建筑投资", "%", "季", "美国经济分析局", "#9f1853", (-80, 100), "1990-01-01"),
    "inv_equipment_growth": ("G005120887", "美国:GDP:不变价:支出法:国内私人投资:固定投资:非住宅类:设备和器械:环比折年率:季调:当季值", "设备投资", "%", "季", "美国经济分析局", "#0f62fe", (-80, 100), "1990-01-01"),
    "inv_ipp_growth": ("G005120888", "美国:GDP:不变价:支出法:国内私人投资:固定投资:非住宅类:知识产权产品:环比折年率:季调:当季值", "知识产权投资", "%", "季", "美国经济分析局", "#007d79", (-50, 80), "1990-01-01"),
    "mfg_construction": ("G025151759", "美国:私人建造支出:制造业:折年数:季调:当月值", "制造业建造支出", "百万美元", "月", "美国人口普查局", "#9f1853", (1_000, 500_000), "2000-01-01"),
    "dc_construction": ("G025151708", "美国:私人建造支出:非住宅:办公:数据中心:折年数:季调:当月值", "数据中心建造支出", "百万美元", "月", "美国人口普查局", "#0f62fe", (100, 300_000), "2014-01-01"),
    # Chapter 7 · PMI
    "ism": ("G002601508", "美国:供应管理协会(ISM):制造业PMI", "ISM制造业PMI", "", "月", "美国供应管理协会", "#0f62fe", (20, 80), "1990-01-01"),
    "ism_orders": ("G002601511", "美国:ISM:制造业PMI:新订单", "ISM新订单", "", "月", "美国供应管理协会", "#0f62fe", (10, 90), "1990-01-01"),
    "ism_inventory": ("G002601515", "美国:ISM:制造业PMI:自有库存", "ISM自有库存", "", "月", "美国供应管理协会", "#9f1853", (10, 90), "1990-01-01"),
    "ism_prices": ("G002601517", "美国:ISM:制造业PMI:物价", "ISM价格支付", "", "月", "美国供应管理协会", "#da1e28", (10, 100), "1990-01-01"),
    "ism_employment": ("G002601513", "美国:ISM:制造业PMI:就业", "ISM就业", "", "月", "美国供应管理协会", "#007d79", (10, 90), "1990-01-01"),
    "ism_delivery": ("G002601514", "美国:ISM:制造业PMI:供应商交付", "ISM供应商交付", "", "月", "美国供应管理协会", "#6929c4", (10, 100), "1990-01-01"),
    "industrial_production": ("G006598549", "美国:工业生产指数:季调:当月值", "工业生产", "2017年=100", "月", "美联储", "#0f62fe", (40, 150), "1990-01-01"),
    "wholesale_ratio": ("G002902608", "美国:批发商库存销售比:季调", "批发库存销售比", "", "月", "美国人口普查局", "#9f1853", (0.5, 3), "1992-01-01"),
    "retail_ratio": ("G002902607", "美国:零售商库存销售比:季调", "零售库存销售比", "", "月", "美国人口普查局", "#007d79", (0.5, 3), "1992-01-01"),
    "ny_fed": ("G003049555", "美国:纽约联储制造业指数:综合:季调", "纽约联储制造业", "", "月", "纽约联储", "#6929c4", (-100, 100), "2001-01-01"),
    "philly_fed": ("G002951323", "美国:费城联储制造业指数:季调", "费城联储制造业", "", "月", "费城联储", "#0f62fe", (-100, 100), "1990-01-01"),
    "korea_exports": ("G012203163", "韩国:出口金额:当月同比", "韩国出口同比", "%", "月", "同花顺金融", "#007d79", (-80, 100), "1990-01-01"),
    # Chapter 8 · Fiscal and Treasury
    "fiscal_receipts": ("G002601592", "美国:政府财政收入", "财政收入", "百万美元", "月", "美国财政部", "#007d79", (0, 2_000_000), "1990-01-01"),
    "fiscal_outlays": ("G002601593", "美国:政府财政支出", "财政支出", "百万美元", "月", "美国财政部", "#da1e28", (0, 3_000_000), "1990-01-01"),
    "fiscal_deficit": ("G002601594", "美国:政府财政赤字(盈余为负)", "财政赤字", "百万美元", "月", "美国财政部", "#9f1853", (-1_000_000, 3_000_000), "1990-01-01"),
    "net_interest_gdp": ("G027048109", "美国:联邦财政支出:利息净额:占GDP的比例", "净利息支出/GDP", "%", "年", "美国国会预算办公室", "#da1e28", (0, 15), "1990-01-01"),
    "debt_gdp": ("G003820238", "美国:联邦政府债务:公众持有的债务:占GDP比重(含预测)", "公众持有债务/GDP", "%", "年", "美国政府信息公开平台", "#0f62fe", (0, 250), "1990-01-01"),
    "auction_10y_btc": ("G012902021", "美国:国债拍卖:10年期:竞拍倍数", "10年期拍卖竞拍倍数", "", "日", "同花顺金融", "#6929c4", (0.5, 8), "2008-01-01"),
    # Shared rates and Fed chapter
    "ust2": ("G002600770", "美国:国债收益率:2年", "2年期美债", "%", "日", "美联储", "#0f62fe", (-2, 20), "2000-01-01"),
    "ust10": ("G002600774", "美国:国债收益率:10年", "10年期美债", "%", "日", "美联储", "#9f1853", (-2, 20), "2000-01-01"),
    "effr": ("G026773952", "美国:有效联邦基金利率(EFFR)", "EFFR", "%", "月", "圣路易斯联储", "#0f62fe", (0, 20), "2000-01-01"),
    "iorb": ("G006736804", "美国:准备金余额利率(IORB)", "IORB", "%", "日", "美联储", "#007d79", (0, 20), "2021-01-01"),
    "sofr": ("G005226445", "美国:SOFR:利率", "SOFR", "%", "日", "纽约联储", "#9f1853", (-2, 20), "2018-01-01"),
    "onrrp_rate": ("G006613832", "美国:隔夜逆回购协议:国库券:利率", "ON RRP利率", "%", "日", "圣路易斯联储", "#6929c4", (-2, 20), "2013-01-01"),
    "reserves": ("G010391328", "美国:货币基础:准备金余额:当月值", "准备金余额", "十亿美元", "月", "美国经济分析局", "#0f62fe", (0, 10_000), "2000-01-01"),
    "onrrp_amount": ("G006613831", "美国:隔夜逆回购协议:国库券:总额", "ON RRP用量", "十亿美元", "日", "圣路易斯联储", "#6929c4", (0, 5_000), "2013-01-01"),
    "tga": ("G006615675", "美国:所有联储银行:负债:存款(除准备金):美国财政部普通账户(TGA余额):当周值", "TGA余额", "百万美元", "日", "美联储", "#da1e28", (0, 3_000_000), "2002-01-01"),
    "fed_treasuries": ("G025034601", "美国:所有联储银行:资产:持有证券:国债:总计", "联储持有美债", "百万美元", "日", "美联储", "#0f62fe", (0, 10_000_000), "2002-01-01"),
    "fed_mbs": ("G025034584", "美国:所有联储银行:资产:持有证券:抵押担保证券:总计", "联储持有MBS", "百万美元", "日", "美联储", "#9f1853", (0, 5_000_000), "2002-01-01"),
    "nfci": ("G012264492", "美国:芝加哥联储:全国金融状况指数:当周值", "芝加哥联储NFCI", "", "周", "芝加哥联储", "#6929c4", (-5, 10), "1990-01-01"),
    "broad_dollar": ("G002600886", "美国:名义美元指数:广义", "广义美元指数", "1973年3月=100", "日", "美联储", "#007d79", (50, 200), "1995-01-01"),
}


def pct_change(dates: list[str], values: list[float], periods: int) -> tuple[list[str], list[float]]:
    rows = [(dates[i], (values[i] / values[i - periods] - 1) * 100) for i in range(periods, len(values)) if values[i - periods] != 0]
    return [d for d, _ in rows], [v for _, v in rows]


def rolling_sum(dates: list[str], values: list[float], periods: int) -> tuple[list[str], list[float]]:
    rows = [(dates[i], sum(values[i - periods + 1:i + 1])) for i in range(periods - 1, len(values))]
    return [d for d, _ in rows], [v for _, v in rows]


def difference(left: tuple[list[str], list[float]], right: tuple[list[str], list[float]]) -> tuple[list[str], list[float]]:
    lmap = {compact_date(d)[:6]: v for d, v in zip(*left)}
    rmap = {compact_date(d)[:6]: v for d, v in zip(*right)}
    periods = sorted(set(lmap) & set(rmap))
    return periods, [lmap[p] - rmap[p] for p in periods]


def fetch_all(token: str) -> dict[str, dict[str, Any]]:
    end = datetime.now(timezone.utc).date().isoformat()
    result: dict[str, dict[str, Any]] = {}
    for key, spec in SERIES_SPEC.items():
        code, exact_name, _label, unit, frequency, institution, _color, bounds, start = spec
        metadata = next((item for item in search_indicator(token, exact_name) if item.get("displayid") == code), None)
        if metadata is None:
            raise ValueError(f"metadata mismatch: {key} {code} not found")
        actual = (metadata.get("name"), metadata.get("unit") or "", metadata.get("frequency"), metadata.get("datasource"))
        expected = (exact_name, unit, frequency, institution)
        if actual != expected:
            raise ValueError(f"identity mismatch for {key}: expected={expected!r}, actual={actual!r}")
        payload = fetch_indicator(token, code, start, end)
        dates, values = fetch_response_series(payload, code)
        if not all(bounds[0] <= value <= bounds[1] for value in values):
            raise ValueError(f"range check failed for {key}: {min(values)}..{max(values)}")
        result[key] = {"metadata": metadata, "payload": payload}
        print(f"verified {key}: {code} {dates[0]}..{dates[-1]} ({len(dates)})")
    return result


def source_meta(key: str, latest: str) -> dict[str, Any]:
    code, name, _label, unit, _frequency, institution, _color, _bounds, _start = SERIES_SPEC[key]
    return {"provider": "iFinD EDB", "institution": institution, "code": code, "name": name, "rawUnit": unit or "无量纲指数", "url": "https://ft.51ifind.com", "latestObservation": latest}


def series(key: str, parsed: dict[str, tuple[list[str], list[float]]], *, series_id: str | None = None, label: str | None = None, data: tuple[list[str], list[float]] | None = None, unit: str | None = None, color: str | None = None, transform: str | None = None, scale: float = 1.0) -> dict[str, Any]:
    dates, values = data or parsed[key]
    values = [value * scale for value in values]
    _code, _name, default_label, raw_unit, frequency, _institution, default_color, _bounds, _start = SERIES_SPEC[key]
    result = {
        "id": series_id or key, "label": label or default_label, "dates": dates,
        "values": [round(value, 5) for value in values], "color": color or default_color,
        "unit": raw_unit if unit is None else unit, "frequency": frequency,
        "latestValue": round(values[-1], 5), "latestObservation": dates[-1], "source": source_meta(key, dates[-1]),
    }
    if transform:
        result["transformLabel"] = transform
    return result


def chart(chart_id: str, title: str, description: str, unit: str, items: list[dict[str, Any]], *, eyebrow: str, what: str, read: str, caveat: str, slide: str, default: str = "10Y", reference: float | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"id": chart_id, "kind": "line", "eyebrow": eyebrow, "title": title, "description": description, "unit": unit, "defaultRange": default, "series": items, "explanation": {"what": what, "howToRead": read, "caveat": caveat, "pptSlide": slide}}
    if reference is not None:
        result["reference"] = reference
    return result


def module_static() -> dict[str, dict[str, Any]]:
    return {
        "housing": {
            "chapter": "05", "label": "住房", "accent": "teal", "slides": "130—147", "routeSlide": 131,
            "title": "周期之母：沿最长的数据链条读住房", "subtitle": "按利率→信心→销量→开工→房价→租金CPI识别货币政策传导，并用锁定效应解释量价背离。", "core": "住宅投资仅约占GDP 4%，却常领先衰退4—6个季度",
            "routeMap": [
                {"id": "framework", "title": "分析框架", "subtitle": "周期之母", "nodes": [{"title": "住宅投资", "detail": "体量小但领先周期"}, {"title": "传导链", "detail": "利率→信心→销量→开工→房价→租金CPI"}]},
                {"id": "mortgage", "title": "房贷制度", "subtitle": "不对称传导", "nodes": [{"title": "30年固定+可再融资", "detail": "加息冻结增量，不抬存量房主月供"}, {"title": "MBS链", "detail": "发放→两房/Ginnie→投资者；FHLB作流动性后盾"}]},
                {"id": "official", "title": "官方数据", "subtitle": "量·库·价·租", "nodes": [{"title": "许可/开工", "detail": "单户与多户分读"}, {"title": "新屋/成屋", "detail": "签约领先过户"}, {"title": "库存月数", "detail": "6个月为经验平衡线"}, {"title": "房价与房租", "detail": "价格滞后约半年，CPI住房约1.5年"}]},
                {"id": "high-frequency", "title": "第三方高频", "subtitle": "链条前端", "nodes": [{"title": "NAHB/MBA/房贷利率", "detail": "最先响应融资条件"}, {"title": "Zillow/Redfin", "detail": "挂牌与新租约领先官方"}]},
                {"id": "case", "title": "案例复盘", "subtitle": "量崩价稳", "nodes": [{"title": "2022—23", "detail": "锁定效应压缩供给；用库存、杠杆、信用区分2008"}]},
            ],
            "passports": [
                {"id": "mortgage", "title": "房贷利率/NAHB", "producer": "Freddie Mac周度调查 / NAHB建筑商调查", "frequency": "周/月", "coverage": "新增融资成本与建筑商情绪", "revision": "调查方法与样本会调整", "use": "传导链最前端", "pitfall": "情绪不是成交；购房和再融资申请不可混读", "pptSlide": "第134—138、144页"},
                {"id": "construction", "title": "许可与开工", "producer": "Census New Residential Construction", "frequency": "月", "coverage": "单户、多户、地区", "revision": "天气敏感、月度修订较大", "use": "住宅投资领先/同步量", "pitfall": "多户项目与单户需求的周期不同", "pptSlide": "第138—139页"},
                {"id": "sales", "title": "新屋与成屋销售", "producer": "Census / NAR", "frequency": "月", "coverage": "新屋签约 / 成屋过户", "revision": "新屋样本小且修订大", "use": "交易量与锁定效应", "pitfall": "签约和过户时点不同，单位也不同", "pptSlide": "第138、140页"},
                {"id": "prices", "title": "FHFA / Case-Shiller", "producer": "FHFA贷款样本 / S&P重复销售", "frequency": "月；发布滞后", "coverage": "合规贷款 / 20城成交", "revision": "三个月移动平均及历史修订", "use": "房价方向与幅度确认", "pitfall": "均为滞后尺；覆盖和权重不可直接拼接", "pptSlide": "第141—143页"},
            ],
            "availability": [
                {"label": "MBA购房/再融资申请", "status": "not-integrated", "explanation": "PPT要求分开读；当前iFinD自动更新合同未检出可核验完整序列，不以房贷利率替代。"},
                {"label": "Zillow/Redfin挂牌与新租约", "status": "not-integrated", "explanation": "属于第三方高频；不以滞后的官方房价指数冒充。"},
                {"label": "2022—23量崩价稳", "status": "historical-case", "explanation": "作为锁定效应案例解释，不把PPT历史快照当实时数据。"},
            ],
        },
        "investment": {
            "chapter": "06", "label": "企业投资", "accent": "blue", "slides": "148—160", "routeSlide": 149,
            "title": "短期是需求，中期是供给", "subtitle": "拆分设备、知识产权和厂房三种周期，用订单—出货—建造—GDP核算连接月频与季度数据。", "core": "设备看周期，知识产权看趋势，厂房看政策与长波",
            "routeMap": [
                {"id": "framework", "title": "分析框架", "subtitle": "双重身份", "nodes": [{"title": "三分项", "detail": "设备/知识产权/厂房"}, {"title": "传统四因子", "detail": "需求加速、利润、资金成本、不确定性"}, {"title": "本轮特殊性", "detail": "AI投资对利率与不确定性更钝感"}]},
                {"id": "official", "title": "官方数据", "subtitle": "订单到核算", "nodes": [{"title": "核心资本品", "detail": "订单领先，出货同步；均为名义值"}, {"title": "建造支出", "detail": "制造业与数据中心分项"}, {"title": "GDP投资拆解", "detail": "研发资本化与链式量口径"}]},
                {"id": "micro", "title": "微观与第三方", "subtitle": "领先2—4季", "nodes": [{"title": "云厂商Capex", "detail": "看指引修正与capex/现金流"}, {"title": "供应链印证", "detail": "台积电/SEMI/电力落地"}, {"title": "中小企业对照", "detail": "NFIB与地区联储"}]},
                {"id": "case", "title": "案例复盘", "subtitle": "AI投资潮", "nodes": [{"title": "官方显形", "detail": "微观领先官方2—4季度"}, {"title": "测算纪律", "detail": "进口GPU不增加GDP；自上而下与财报法分开"}]},
            ],
            "passports": [
                {"id": "core-capital", "title": "核心资本品订单/出货", "producer": "Census M3 Durable Goods", "frequency": "月", "coverage": "非国防资本品除飞机", "revision": "初值、终值与年度修订", "use": "设备投资意愿/交付", "pitfall": "名义值；订单不能直接当GDP投资", "pptSlide": "第153页"},
                {"id": "construction", "title": "建造支出", "producer": "Census Value of Construction Put in Place", "frequency": "月；滞后约2个月", "coverage": "制造业、数据中心等用途", "revision": "修订较大、项目周期长", "use": "厂房与AI基础设施", "pitfall": "建筑潮不等于设备到位或产能投产", "pptSlide": "第154页"},
                {"id": "nipa", "title": "实际非住宅固定投资", "producer": "BEA NIPA", "frequency": "季", "coverage": "建筑、设备、知识产权", "revision": "多轮及年度综合修订", "use": "官方实际投资与GDP贡献", "pitfall": "链式实际美元不可直接加总；进口设备被进口项抵消", "pptSlide": "第150、155—156页"},
            ],
            "availability": [
                {"label": "Hyperscaler Capex指引", "status": "not-integrated", "explanation": "属于公司财报事件数据，含海外、土地和租赁；不能与美国GDP直接相加。"},
                {"label": "NFIB资本开支计划", "status": "not-integrated", "explanation": "当前iFinD EDB未检出精确可核验序列，不以产能利用率替代意向调查。"},
                {"label": "AI Capex贡献估算", "status": "methodology", "explanation": "保留自上而下与自下而上两种方法；进口GPU与海外投资必须剔除。"},
            ],
        },
        "pmi": {
            "chapter": "07", "label": "PMI与库存", "accent": "purple", "slides": "161—174", "routeSlide": 162,
            "title": "小体量、大波动：制造业是周期放大器", "subtitle": "用ISM变化、订单—库存差、价格分项、三级库存和地区调查识别基钦周期及资产共同因子。", "core": "PMI衡量改善广度；资产更多交易其变化，而非是否高于50",
            "routeMap": [
                {"id": "framework", "title": "分析框架", "subtitle": "库存周期", "nodes": [{"title": "牛鞭效应", "detail": "供应链逐级放大终端需求波动"}, {"title": "PCA证据", "detail": "PMI变化与全球多资产共同因子相关"}]},
                {"id": "hard", "title": "官方硬数据", "subtitle": "生产与库存", "nodes": [{"title": "工业生产/利用率", "detail": "准确但市场反应有限"}, {"title": "三级库存", "detail": "用库存销售比辨别补库/去库"}]},
                {"id": "ism", "title": "ISM深拆", "subtitle": "广度而非强度", "nodes": [{"title": "新订单−自有库存", "detail": "领先总指数约3个月"}, {"title": "价格", "detail": "商品通胀与关税前哨"}, {"title": "就业/交付", "detail": "两项常见误读"}, {"title": "校准", "detail": "50不是GDP零增长线"}]},
                {"id": "surveys", "title": "调查家族", "subtitle": "逐次修正预期", "nodes": [{"title": "S&P Flash", "detail": "约23日，当月最早全国调查"}, {"title": "地区联储", "detail": "早约2周；合成优于单家"}]},
                {"id": "global", "title": "全球与资产", "subtitle": "共同周期", "nodes": [{"title": "韩国出口", "detail": "每月较早的全球制造业硬数据"}, {"title": "四象限", "detail": "PMI方向×通胀方向"}]},
            ],
            "passports": [
                {"id": "ism", "title": "ISM制造业PMI", "producer": "ISM会员企业扩散调查", "frequency": "月；次月首个工作日", "coverage": "新订单、生产、就业、交付、库存等", "revision": "季调因子与年度权重调整", "use": "最早全国制造业广度", "pitfall": "50是扩散中性，不是实际产出零增长", "pptSlide": "第166—172页"},
                {"id": "ip", "title": "工业生产", "producer": "Federal Reserve G.17", "frequency": "月", "coverage": "制造、采矿、公用事业", "revision": "随后数月及年度修订", "use": "调查的硬数据确认", "pitfall": "发布时间较晚，市场增量有限", "pptSlide": "第163、166页"},
                {"id": "inventory", "title": "库存销售比", "producer": "Census制造/批发/零售调查", "frequency": "月", "coverage": "供应链不同层级", "revision": "发布错位且会修订", "use": "主动/被动补去库", "pitfall": "库存多为需求滞后项，须与订单联合", "pptSlide": "第169—170页"},
                {"id": "regional", "title": "地区联储调查", "producer": "纽约、费城等地区联储", "frequency": "月内较早", "coverage": "单区百余家制造企业", "revision": "季调与历史基准会调整", "use": "月内预测ISM", "pitfall": "单家样本小、噪音大，宜合成", "pptSlide": "第172—173页"},
            ],
            "availability": [
                {"label": "S&P Global Flash PMI", "status": "not-integrated", "explanation": "商业调查未纳入当前iFinD自动更新合同；不以ISM替代其更早发布时间。"},
                {"label": "制造业三级库存", "status": "partial", "explanation": "已接入批发与零售库存销售比；未找到同口径制造商总库存销售比，不用成品库存同比替代。"},
                {"label": "多资产四象限回测", "status": "methodology", "explanation": "需要可投资总回报序列和无未来信息的月末规则，本页暂保留研究框架。"},
            ],
        },
        "fiscal": {
            "chapter": "08", "label": "财政与国债", "accent": "red", "slides": "175—205", "routeSlide": 176,
            "title": "钱袋权在国会，财政部负责融资执行", "subtitle": "把立法决定的赤字和财政部决定的期限结构分开，再用DTS/MTS、CBO、QRA与拍卖逐层验证。", "core": "为什么借、借多少主要由国会决定；怎么借、借多久由财政部执行",
            "routeMap": [
                {"id": "legislation", "title": "立法流程", "subtitle": "永动机 vs 合同工", "nodes": [{"title": "必要支出+税收", "detail": "参数制；预算协调51票可改"}, {"title": "非必要支出", "detail": "授权+拨款，年度更新"}, {"title": "CR/关门/补充拨款", "detail": "短期财政事件"}]},
                {"id": "flows", "title": "收支特征", "subtitle": "结构决定弹性", "nodes": [{"title": "收入", "detail": "个税、工资税、企业税、关税"}, {"title": "支出", "detail": "必要支出显著大于非必要；净利息上升"}]},
                {"id": "stance", "title": "财政立场三看", "subtitle": "长中短分层", "nodes": [{"title": "长期看协调", "detail": "十年评分与参数变化"}, {"title": "中期看经济", "detail": "自动稳定器与COLA"}, {"title": "短期看拨款", "detail": "CR/关门/补充拨款"}]},
                {"id": "treasury", "title": "国债市场", "subtitle": "供给到期限溢价", "nodes": [{"title": "发行哲学", "detail": "regular & predictable"}, {"title": "拍卖三件套", "detail": "竞拍倍数/间接投标/尾部"}, {"title": "久期供给", "detail": "与QE/QT一体两面"}]},
                {"id": "system", "title": "数据体系", "subtitle": "逐层确认", "nodes": [{"title": "DTS→MTS→CBO→QRA→拍卖", "detail": "高频现金流到实际需求检验"}]},
            ],
            "passports": [
                {"id": "mts", "title": "MTS月度财政收支", "producer": "US Treasury", "frequency": "月；财政年度口径", "coverage": "收入、支出、赤字及科目", "revision": "季节性极强，月内时点错位", "use": "财政脉冲与12个月趋势", "pitfall": "报税季、退税与财政年度造成单月噪音", "pptSlide": "第182—188、202—203页"},
                {"id": "cbo", "title": "CBO基线与法案评分", "producer": "Congressional Budget Office", "frequency": "年度/事件", "coverage": "十年Current Law基线", "revision": "经济与法律假设变化即重估", "use": "长期财政路径", "pitfall": "基线不是最可能情景；含预测序列须显式标注", "pptSlide": "第187—193页"},
                {"id": "auction", "title": "国债拍卖", "producer": "US Treasury", "frequency": "每周多次", "coverage": "不同券种的发行与投标", "revision": "单次噪音大", "use": "实际需求检验", "pitfall": "竞拍倍数需和自身历史、间接投标与tail合读", "pptSlide": "第194—201页"},
            ],
            "availability": [
                {"label": "DTS日度现金流", "status": "not-integrated", "explanation": "当前以iFinD MTS月度序列为主；DTS需财政部官方文件管线。"},
                {"label": "QRA券种期限结构", "status": "event-data", "explanation": "季度公告是事件型表格，不以月度赤字代替；后续应接财政部官方QRA。"},
                {"label": "拍卖间接投标与tail", "status": "partial", "explanation": "当前iFinD接入10年期竞拍倍数；未检出稳定的间接投标占比和WI尾部完整序列。"},
            ],
        },
        "fed": {
            "chapter": "09", "label": "美联储与金融条件", "accent": "cyan", "slides": "206—231", "routeSlide": 207,
            "title": "从反应函数到政策的市场落点", "subtitle": "分清制度、工具、文本、市场定价与金融条件反馈；政策利率只是起点，实体感受到的是一揽子价格。", "core": "就业与通胀决定反应函数，市场价格决定政策如何传到实体",
            "routeMap": [
                {"id": "institution", "title": "制度框架", "subtitle": "谁决策", "nodes": [{"title": "双重使命", "detail": "相对偏离决定政策重心"}, {"title": "FOMC与信息流", "detail": "声明→记者会→SEP→纪要→讲话"}]},
                {"id": "tools", "title": "政策工具箱", "subtitle": "怎么实施", "nodes": [{"title": "利率走廊", "detail": "IORB/ON RRP/SRF；看EFFR与SOFR位置"}, {"title": "资产负债表", "detail": "QE/QT与准备金/ON RRP/TGA"}, {"title": "准备金充足", "detail": "数量与价格两类判别"}]},
                {"id": "text", "title": "文本数据", "subtitle": "如何读", "nodes": [{"title": "声明/SEP", "detail": "逐句比较、分布与修正"}, {"title": "纪要/讲话", "detail": "量词、鹰鸽与级别权重"}]},
                {"id": "pricing", "title": "市场定价", "subtitle": "预期差", "nodes": [{"title": "FF期货/OIS", "detail": "单次会议概率与完整路径"}, {"title": "市场 vs 点阵图", "detail": "分歧由数据裁决"}]},
                {"id": "conditions", "title": "金融条件", "subtitle": "政策落点", "nodes": [{"title": "组件", "detail": "曲线/信用/美元/股权"}, {"title": "反身性", "detail": "政策与市场形成循环"}]},
            ],
            "passports": [
                {"id": "corridor", "title": "EFFR / IORB / SOFR / ON RRP", "producer": "NY Fed / Federal Reserve", "frequency": "日/月", "coverage": "无抵押、准备金、有抵押与非银下限", "revision": "管理利率按会议调整", "use": "走廊实施与资金面", "pitfall": "EFFR月频与其他日频异步；不同市场不可机械相减", "pptSlide": "第219—223页"},
                {"id": "balance", "title": "H.4.1资产负债表", "producer": "Federal Reserve", "frequency": "周（iFinD日期字段标日）", "coverage": "持有证券、准备金、TGA、工具用量", "revision": "会计分类与发布日固定", "use": "QE/QT和流动性分配", "pitfall": "准备金、TGA、ON RRP此消彼长；总资产不是流动性单一答案", "pptSlide": "第218、223—224页"},
                {"id": "conditions", "title": "利率与NFCI", "producer": "Federal Reserve / Chicago Fed", "frequency": "日/周", "coverage": "政策路径、曲线与105项金融变量", "revision": "NFCI会随输入修订", "use": "市场传导与自稳定器", "pitfall": "FCI看方向，不把相关性当政策因果", "pptSlide": "第225—231页"},
            ],
            "availability": [
                {"label": "FOMC声明/SEP/纪要/讲话", "status": "event-text", "explanation": "文本与点阵图是事件型数据，需独立版本化管线；不能用利率时序替代。"},
                {"label": "FF期货/OIS会议概率", "status": "not-integrated", "explanation": "需要市场合约与会议日历映射；当前不把2年期收益率冒充离散概率。"},
                {"label": "信用利差与股权条件", "status": "partial", "explanation": "本次iFinD主源未检出精确可核验的美国IG/HY OAS全序列；NFCI是综合确认而非替代各分项。"},
            ],
        },
    }


def build_dataset(raw: dict[str, dict[str, Any]], raw_snapshot: str) -> dict[str, Any]:
    parsed = {key: fetch_response_series(item["payload"], SERIES_SPEC[key][0]) for key, item in raw.items()}
    modules = module_static()

    # Housing
    housing_charts = [
        chart("housing-front-end", "房贷利率与NAHB", "融资条件先动，建筑商情绪随后确认；两条线量纲不同，分开读方向和拐点。", "双轴原始量纲", [series("mortgage30", parsed), series("nahb", parsed)], eyebrow="5.1/5.4 · FRONT END", what="Freddie Mac 30年固定房贷周利率与NAHB月度住房市场指数。", read="利率上行通常先压NAHB；NAHB见底可领先开工和住宅投资。", caveat="双量纲只比较方向，不比较数值高低；NAHB为扩散调查。", slide="PPT第134、144页", default="10Y"),
        chart("housing-permits-starts", "许可与开工", "许可更偏前瞻，开工更接近当期住宅建造活动。", "千套·折年", [series("permits", parsed), series("starts", parsed)], eyebrow="5.3 · CONSTRUCTION", what="Census新建私人住宅营建许可与开工季调折年数。", read="许可先于开工；两者持续同向下行比单月天气冲击更可信。", caveat="月度噪音和修订较大；总量会混合单户与多户周期。", slide="PPT第138—139页", default="10Y"),
        chart("housing-single-multi", "单户与多户开工", "把家庭购房需求与公寓开发商的供给周期分开。", "千套", [series("starts_single", parsed), series("starts_multi", parsed)], eyebrow="5.3 · TWO CYCLES", what="单户折年开工与5单元以上月度开工。", read="单户对房贷利率更敏感；多户受租金回报、融资和在建管线支配。", caveat="iFinD多户序列为当月值、单户为折年数，只读各自方向，不横比水平。", slide="PPT第139页", default="10Y"),
        chart("housing-sales", "新屋与成屋销售", "签约口径的新屋销售领先过户口径的成屋销售。", "各自原始单位", [series("new_sales", parsed), series("existing_sales", parsed)], eyebrow="5.3 · SALES", what="新屋销售季调折年千套与成屋销售季调折年万套。", read="新屋更靠近链条前端；成屋更能显示低息存量房贷的锁定效应。", caveat="单位和确认时点不同，不能比较两线绝对高低。", slide="PPT第140页", default="10Y"),
        chart("housing-supply", "库存月数", "库存除以当前销售速度，是量价关系最直接的供需温度计。", "月", [series("new_supply", parsed), series("existing_supply", parsed)], eyebrow="5.3 · MONTHS SUPPLY", what="按当前销速计算的新屋和成屋可售月数。", read="高于自身历史且销量弱，价格下行压力增加；6个月是经验参照而非硬阈值。", caveat="库存月数同时受库存和销售分母影响，销量骤降可机械推高比值。", slide="PPT第140、147页", default="10Y", reference=6),
        chart("housing-prices", "两把房价尺", "FHFA覆盖合规贷款，Case-Shiller 20城使用重复销售法。", "%同比", [series("fhfa_yoy", parsed), series("cs_yoy", parsed)], eyebrow="5.3 · PRICE CONFIRMATION", what="FHFA全国季调房价同比与S&P/Case-Shiller 20城同比。", read="方向一致时确认全国房价趋势；分歧时检查贷款覆盖、城市结构与现金成交。", caveat="均显著滞后，不能用于实时拐点；覆盖面和方法不同。", slide="PPT第141—142页", default="ALL", reference=0),
        chart("housing-credit-risk", "住房抵押贷款拖欠率", "用信用质量检查量崩是否演化为2008式被迫出售。", "%", [series("mortgage_delinquency", parsed)], eyebrow="5.5 · CREDIT RISK", what="商业银行住房抵押贷款季调拖欠率。", read="销量下滑但拖欠率低，更多是锁定效应；拖欠和库存共振上升才接近信用周期。", caveat="仅覆盖商业银行贷款，不等于全部按揭市场；季频且滞后。", slide="PPT第145—147页", default="ALL"),
    ]
    modules["housing"]["sections"] = [
        {"id": "transmission", "title": "传导链前端：融资、信心与建造", "description": "先用房贷利率和NAHB识别方向，再由许可、开工与户型结构确认。", "charts": housing_charts[:3]},
        {"id": "market", "title": "交易、库存与价格", "description": "签约和过户时点分开，库存月数连接量与价，两把房价尺用于滞后确认。", "charts": housing_charts[3:6]},
        {"id": "risk", "title": "锁定效应与信用尾部", "description": "区分加息导致的成交冻结与杠杆恶化导致的被迫出售。", "charts": housing_charts[6:]},
    ]

    # Investment
    orders_yoy = pct_change(*parsed["core_orders"], 12)
    shipments_yoy = pct_change(*parsed["core_shipments"], 12)
    mfg_yoy = pct_change(*parsed["mfg_construction"], 12)
    dc_yoy = pct_change(*parsed["dc_construction"], 12)
    investment_charts = [
        chart("investment-orders-shipments", "核心资本品订单与出货", "订单是意愿，出货更接近交付；用同比降低单月耐用品噪音。", "%同比", [series("core_orders", parsed, series_id="core_orders_yoy", label="订单同比", data=orders_yoy, unit="%", transform="由季调名义水平计算12个月同比"), series("core_shipments", parsed, series_id="core_shipments_yoy", label="出货同比", data=shipments_yoy, unit="%", transform="由季调名义水平计算12个月同比")], eyebrow="6.2 · MONTHLY PROXY", what="非国防资本品除飞机的季调订单与出货同比。", read="订单先行1—2个月，出货确认设备投资核算方向。", caveat="均为名义值且会修订；进口结构和价格变化会污染与实际GDP的映射。", slide="PPT第153页", reference=0),
        chart("investment-capacity", "工业产能利用率", "传统投资四因子中的需求与产能约束代理。", "%", [series("capacity_util", parsed)], eyebrow="6.1 · DEMAND DRIVER", what="美联储全部工业部门季调产能利用率。", read="利用率高且订单加速，传统设备投资动机更强。", caveat="利用率不是投资意向；AI投资可能在低利用率下仍受战略竞争驱动。", slide="PPT第152页", default="ALL"),
        chart("investment-three-components", "三类实际投资增速", "建筑、设备和知识产权产品具有不同的周期与调整成本。", "%环比折年", [series("inv_structures_growth", parsed), series("inv_equipment_growth", parsed), series("inv_ipp_growth", parsed)], eyebrow="6.1/6.2 · THREE COMPONENTS", what="BEA实际非住宅固定投资三分项季环比折年率。", read="设备最顺周期，知识产权更平滑，建筑受政策和超长项目周期驱动。", caveat="SAAR放大单季噪音；三条均会随国民账户修订。", slide="PPT第150、155—156页", default="ALL", reference=0),
        chart("investment-ai-construction", "制造业与数据中心建造支出", "把芯片法案建厂潮与AI基础设施投资的官方月度落点分开。", "%同比", [series("mfg_construction", parsed, series_id="mfg_construction_yoy", label="制造业建造同比", data=mfg_yoy, unit="%", transform="由季调折年水平计算12个月同比"), series("dc_construction", parsed, series_id="dc_construction_yoy", label="数据中心建造同比", data=dc_yoy, unit="%", transform="由季调折年水平计算12个月同比")], eyebrow="6.2/6.4 · AI & POLICY", what="Census制造业和办公类数据中心私人建造支出同比。", read="前者偏政策与供应链重构，后者偏AI算力基础设施；方向可交叉验证财报指引。", caveat="建造支出不等于设备投产；数据中心仅是AI投资的一部分，且修订较大。", slide="PPT第154、159页", default="10Y", reference=0),
    ]
    modules["investment"]["sections"] = [
        {"id": "drivers", "title": "驱动与月频代理", "description": "先看需求/产能，再用核心资本品订单和出货追踪设备投资。", "charts": investment_charts[:2]},
        {"id": "composition", "title": "三分项：设备、知识产权、厂房", "description": "季度核算用于确认实际投资；不同分项的周期性质不可混同。", "charts": investment_charts[2:3]},
        {"id": "ai", "title": "AI与政策投资如何在官方数据中显形", "description": "制造业建厂和数据中心建造是官方硬数据，但不等于完整AI capex。", "charts": investment_charts[3:]},
    ]

    # PMI
    ip_yoy = pct_change(*parsed["industrial_production"], 12)
    order_inventory = difference(parsed["ism_orders"], parsed["ism_inventory"])
    pmi_charts = [
        chart("pmi-hard-soft", "ISM与工业生产", "扩散调查先行，工业生产硬数据确认；为避免量纲错觉，工业生产转为同比。", "指数 / %同比", [series("ism", parsed), series("industrial_production", parsed, series_id="industrial_production_yoy", label="工业生产同比", data=ip_yoy, unit="%", transform="由2017=100季调指数计算12个月同比")], eyebrow="7.1/7.2 · SOFT & HARD", what="ISM制造业扩散指数与工业生产同比。", read="ISM方向通常先动；硬数据随后同向确认才构成更完整的周期信号。", caveat="量纲不同，只比较方向；ISM 50不是GDP零增长。", slide="PPT第163、166—167页", default="ALL", reference=50),
        chart("pmi-order-inventory", "新订单−自有库存差", "订单是需求前端，自有库存是供给缓冲；差值用于识别未来增产压力。", "扩散点", [series("ism_orders", parsed, series_id="order_inventory_gap", label="新订单−库存", data=order_inventory, unit="点", transform="ISM新订单减ISM自有库存")], eyebrow="7.3 · LEADING SPREAD", what="两个ISM扩散分项的点差。", read="差值上升通常领先总指数约3个月；订单升、库存降是最强补产组合。", caveat="经验领先关系不是稳定模型；扩散点不等于实际增速百分点。", slide="PPT第169—170页", reference=0),
        chart("pmi-prices", "ISM价格支付", "采购经理最先看到投入品涨价单，是商品通胀与关税传导前哨。", "扩散指数", [series("ism_prices", parsed)], eyebrow="7.3 · PRICES PAID", what="ISM制造业物价扩散指数。", read="持续上行提示成本上涨广度扩大，通常领先PPI/CPI商品项1—3个月。", caveat="关税、交付中断和需求强弱都可推高指数；不是价格涨幅。", slide="PPT第171页", default="ALL", reference=50),
        chart("pmi-employment-delivery", "就业与供应商交付", "两个最容易机械误读的分项：就业不等于非农，交付变慢不一定代表需求强。", "扩散指数", [series("ism_employment", parsed), series("ism_delivery", parsed)], eyebrow="7.3 · MISREADINGS", what="ISM就业与供应商交付扩散指数。", read="就业用于制造业内部广度；交付需结合订单判断需求拉动还是供给受阻。", caveat="制造业就业占比有限；供应链冲击会让交付指数与增长方向相反。", slide="PPT第162、172页", default="ALL", reference=50),
        chart("pmi-inventory-ratios", "批发与零售库存销售比", "供应链不同层级的库存相对销售速度。", "倍", [series("wholesale_ratio", parsed), series("retail_ratio", parsed)], eyebrow="7.3 · INVENTORY CYCLE", what="Census批发商和零售商季调库存销售比。", read="比率上升通常表示销售走弱导致被动补库；需与新订单和销量联合。", caveat="两层级口径和发布时间不同；缺少同口径制造商总库存销售比。", slide="PPT第169页", default="ALL"),
        chart("pmi-regional", "纽约与费城联储制造业调查", "月内更早的地区调查，用于逐次修正全国ISM预期。", "扩散指数", [series("ny_fed", parsed), series("philly_fed", parsed)], eyebrow="7.3 · REGIONAL SURVEYS", what="纽约和费城联储制造业综合扩散指数。", read="两者同向时比单家更可信；费城历史更长，纽约更早但噪音更大。", caveat="单区样本小、行业结构不同；不做标准化就不应平均成全国指数。", slide="PPT第172—173页", reference=0),
        chart("pmi-korea", "韩国出口同比", "作为全球制造业与电子周期较早发布的硬数据观察。", "%同比", [series("korea_exports", parsed)], eyebrow="7.1 · GLOBAL LEAD", what="韩国以美元计价出口金额同比。", read="半导体、汽车和化工占比高，对全球资本开支和电子周期敏感。", caveat="本序列由iFinD计算同比且机构标为同花顺金融；汇率、工作日和价格效应明显。", slide="PPT第165、162页", reference=0),
    ]
    modules["pmi"]["sections"] = [
        {"id": "cycle", "title": "制造业周期：调查先行，硬数据确认", "description": "把ISM的广度信号与工业生产的实际强度分开。", "charts": pmi_charts[:2]},
        {"id": "ism", "title": "ISM深拆：价格、就业与交付", "description": "分项只回答特定问题，不把每条线都当成总增长。", "charts": pmi_charts[2:4]},
        {"id": "inventory", "title": "库存与调查家族", "description": "库存销售比识别被动/主动变化，地区联储提供月内先行信息。", "charts": pmi_charts[4:6]},
        {"id": "global", "title": "全球制造业先行观察", "description": "韩国出口补充美国本土调查，仍需区分价格、汇率与数量。", "charts": pmi_charts[6:]},
    ]

    # Fiscal
    receipts_12m = rolling_sum(*parsed["fiscal_receipts"], 12)
    outlays_12m = rolling_sum(*parsed["fiscal_outlays"], 12)
    deficit_12m = rolling_sum(*parsed["fiscal_deficit"], 12)
    fiscal_charts = [
        chart("fiscal-flows", "滚动12个月财政收入与支出", "用12个月滚动和削弱报税季与退税时点噪音。", "十亿美元", [series("fiscal_receipts", parsed, series_id="receipts_12m", label="12个月收入", data=receipts_12m, unit="十亿美元", scale=.001, transform="月度百万美元滚动12个月求和÷1000"), series("fiscal_outlays", parsed, series_id="outlays_12m", label="12个月支出", data=outlays_12m, unit="十亿美元", scale=.001, transform="月度百万美元滚动12个月求和÷1000")], eyebrow="8.2/8.4 · MTS FLOWS", what="财政部月度收入和支出的滚动12个月累计。", read="支出与收入裂口扩大意味着赤字脉冲增强；再定位税收、转移和利息来源。", caveat="MTS是财政年度现金流口径，不等于BEA国民账户的政府购买。", slide="PPT第182—188、202—203页", default="ALL"),
        chart("fiscal-deficit", "滚动12个月财政赤字", "保留财政部“盈余为负”的原始定义，正值代表赤字。", "十亿美元", [series("fiscal_deficit", parsed, series_id="deficit_12m", label="12个月赤字", data=deficit_12m, unit="十亿美元", scale=.001, transform="月度赤字滚动12个月求和÷1000；盈余为负")], eyebrow="8.2 · FISCAL STANCE", what="MTS月度财政赤字的滚动12个月累计。", read="避免单月季节性，观察赤字趋势和政策/周期变化。", caveat="不能仅凭赤字大小判断财政冲动；需区分自动稳定器、利息和立法变动。", slide="PPT第187—193页", default="ALL", reference=0),
        chart("fiscal-interest", "净利息支出占GDP", "利率×债务存量的交叉项，是财政与货币政策连接处。", "%GDP", [series("net_interest_gdp", parsed)], eyebrow="8.2 · INTEREST BURDEN", what="CBO联邦净利息支出占GDP年度比重。", read="持续上升挤压可自由裁量空间，并提高财政对利率的敏感度。", caveat="年度发布、可能含最新估计；不能与月度现金利息直接对齐。", slide="PPT第186页", default="ALL"),
        chart("fiscal-debt", "公众持有债务占GDP", "更接近市场需要吸收的联邦债务口径。", "%GDP", [series("debt_gdp", parsed)], eyebrow="8.2/8.5 · DEBT PATH", what="公众持有联邦债务占GDP年度比重，iFinD名称明确含预测。", read="用于长期可持续性和利息敏感度，不解释单日收益率。", caveat="历史与预测混在同一来源序列；预测依赖Current Law等假设，页面不把未来值当实际。", slide="PPT第188、204—205页", default="ALL"),
        chart("fiscal-yield-curve", "2年与10年美债收益率", "短端浓缩政策路径，长端叠加期限溢价和久期供需。", "%", [series("ust2", parsed), series("ust10", parsed)], eyebrow="8.3 · FUNDING CONDITIONS", what="美联储H.15日度2年和10年期国债收益率。", read="财政供给主要通过长端和期限溢价起作用，但必须控制增长、通胀和政策预期。", caveat="收益率变动不能单因归于供给；本页未把模型期限溢价伪装成可得数据。", slide="PPT第197—201页", default="10Y"),
        chart("fiscal-auction", "10年期国债竞拍倍数", "拍卖需求三件套中当前可稳定接入的一项。", "倍", [series("auction_10y_btc", parsed)], eyebrow="8.3 · AUCTION CHECK", what="10年期名义国债拍卖总投标额/发行额。", read="低于自身历史且连续走弱才更值得关注；应与间接投标和tail合读。", caveat="单次噪音大；数据源机构标注为同花顺金融，且本页未接入另两项。", slide="PPT第195—196页", default="10Y"),
    ]
    modules["fiscal"]["sections"] = [
        {"id": "flows", "title": "收支与财政立场", "description": "月度现金流先滚动12个月，再区分周期、立法和利息。", "charts": fiscal_charts[:3]},
        {"id": "debt", "title": "长期债务路径", "description": "债务率是慢变量；预测值与实际值必须显式区分。", "charts": fiscal_charts[3:4]},
        {"id": "treasury", "title": "融资条件与拍卖检验", "description": "利率先分短端政策路径与长端风险补偿，拍卖信号只和自身历史比较。", "charts": fiscal_charts[4:]},
    ]

    # Fed
    fed_charts = [
        chart("fed-corridor", "利率走廊与隔夜市场", "管理利率、无抵押与有抵押隔夜利率共同显示政策实施。", "%", [series("effr", parsed), series("iorb", parsed), series("sofr", parsed), series("onrrp_rate", parsed)], eyebrow="9.2 · RATE CORRIDOR", what="EFFR、IORB、SOFR和ON RRP利率。", read="观察市场利率在走廊中的位置；SOFR相对IORB抬升可提示回购资金面收紧。", caveat="EFFR为月频聚合，其他为日频；不同抵押品和参与者意味着不能机械套用单一上下限。", slide="PPT第219—223页", default="5Y"),
        chart("fed-liquidity", "准备金、ON RRP与TGA", "负债端三件套决定流动性在银行、货基与财政部之间的分配。", "十亿美元", [series("reserves", parsed), series("onrrp_amount", parsed), series("tga", parsed, unit="十亿美元", scale=.001, transform="百万美元÷1000")], eyebrow="9.2 · LIABILITY MIX", what="准备金余额、隔夜逆回购用量和财政部一般账户余额。", read="TGA上升通常抽走准备金；ON RRP可在QT早期充当缓冲池。", caveat="三条频率不同且准备金为月频；加总关系受现金和其他负债影响，不是严格三项恒等式。", slide="PPT第218、223页", default="10Y"),
        chart("fed-securities", "联储持有美债与MBS", "资产端直接展示QE/QT吸收或释放的久期。", "万亿美元", [series("fed_treasuries", parsed, unit="万亿美元", scale=.000001, transform="百万美元÷1,000,000"), series("fed_mbs", parsed, unit="万亿美元", scale=.000001, transform="百万美元÷1,000,000")], eyebrow="9.2 · BALANCE SHEET", what="H.4.1联储持有美国国债和机构MBS。", read="持续下降代表QT释放久期；MBS自然到期速度受房贷提前偿还影响。", caveat="iFinD元数据频率标日但原始H.4.1为周度快照；不是每日交易流。", slide="PPT第218、224页", default="ALL"),
        chart("fed-policy-path", "2年与10年美债", "2年浓缩未来政策路径，10年叠加增长、通胀和期限溢价。", "%", [series("ust2", parsed), series("ust10", parsed)], eyebrow="9.3 · MARKET PRICING", what="美联储H.15日度2年和10年收益率。", read="转向前2年往往先动；曲线变化比单点更能显示市场与政策的分歧。", caveat="2年收益率不是会议概率；远端仍含期限溢价和风险补偿。", slide="PPT第225—227页", default="10Y"),
        chart("fed-nfci", "芝加哥联储全国金融状况指数", "把货币、债务和股权市场变量压缩为综合松紧指标。", "标准化指数", [series("nfci", parsed)], eyebrow="9.4 · FINANCIAL CONDITIONS", what="芝加哥联储105项变量合成的NFCI周度指数。", read="高于0通常表示较历史均值更紧，下降表示金融条件放松。", caveat="综合指数会修订；不同FCI的水平不可横比，相关不等于政策因果。", slide="PPT第228—229页", default="ALL", reference=0),
        chart("fed-dollar", "广义名义美元指数", "美元是美国金融条件向全球传导的重要价格。", "1973年3月=100", [series("broad_dollar", parsed)], eyebrow="9.4 · DOLLAR CHANNEL", what="美联储贸易加权广义名义美元指数。", read="美元走强通常收紧全球美元金融条件，并压低进口价格。", caveat="指数权重会更新；美元同时受海外冲击，不能只由美联储政策解释。", slide="PPT第228—231页", default="10Y"),
    ]
    modules["fed"]["sections"] = [
        {"id": "implementation", "title": "政策实施：利率走廊与流动性分配", "description": "先确认隔夜利率是否在走廊内，再看准备金、ON RRP和TGA的结构变化。", "charts": fed_charts[:2]},
        {"id": "balance", "title": "资产负债表：QE/QT与久期", "description": "美债和MBS持仓是政策吸收久期的直接量。", "charts": fed_charts[2:3]},
        {"id": "pricing", "title": "市场定价与金融条件", "description": "利率路径、综合金融条件和美元共同决定政策的实体落点。", "charts": fed_charts[3:]},
    ]

    # Shared headline and quality metadata
    for module_id, module in modules.items():
        all_charts = [item for section in module["sections"] for item in section["charts"]]
        latest_series = [item for item in (series_item for c in all_charts for series_item in c["series"])]
        module["headline"] = [
            {"id": item["id"], "label": "LATEST", "title": item["label"], "value": item["latestValue"], "unit": item["unit"], "observation": item["latestObservation"], "source": item["source"]["provider"]}
            for item in latest_series[:6]
        ]
        module["researchBasis"] = [f"页面按PPT第{module['chapter']}章第{module['slides']}页路线图、数据说明与图例重建。", "PPT定义研究顺序与解释；可更新时序由iFinD EDB重取，不可得项和静态案例明确隔离。"]

    missing = {key: detect_missing_periods(dates, SERIES_SPEC[key][4]) for key, (dates, _values) in parsed.items() if SERIES_SPEC[key][4] in {"月", "季"}}
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "iFinD EDB",
        "sourceProviders": ["iFinD EDB"],
        "frameworkSource": {"file": "研究框架/美国宏观数据培训【0829定稿】.pptx", "slides": "130—231"},
        "modules": modules,
        "dataQuality": {
            "verifiedSeries": len(SERIES_SPEC),
            "missingPeriods": missing,
            "note": "每次刷新逐条核验指标码、精确名称、单位、频率、原始机构与量级；派生同比、点差、滚动12个月和单位换算均由脚本重建。",
        },
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
        raw_path = args.raw_dir / f"{stamp}_ifind_late_modules.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        snapshot = raw_path.relative_to(REPO_ROOT).as_posix()
    dataset = build_dataset(raw, snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    chart_count = sum(len(section["charts"]) for module in dataset["modules"].values() for section in module["sections"])
    print(f"wrote {args.output} ({chart_count} charts, {len(SERIES_SPEC)} verified source series)")


if __name__ == "__main__":
    main()
