"""Build a US inflation workspace from iFinD 经济数据库 (EDB).

Reads the local iFinD client session token from its logs, fetches the US
inflation indicators via the gateway HTTP API, validates identity/units, and
writes ``src/data/usInflationData.json``.
"""

from __future__ import annotations

import argparse
import calendar
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
    "median_cpi_yoy": ("G038486841", "中位数CPI同比", "#1c3557"),
    "trimmed_mean_cpi_yoy": ("G038486842", "16%截尾均值CPI同比", "#c94c4c"),
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
    "mich_1y": ("G012274201", "密歇根大学1年预期", "#c94c4c"),
    "mich_5y": ("G012937589", "密歇根大学5年预期", "#8a9096"),
    "nyfed_sce_1y": ("G020186193", "纽约联储SCE 1年预期", "#1c3557"),
    "cleve_1y": ("G014102434", "克利夫兰联储1年预期", "#2f7fa3"),
    "cleve_5y": ("G014102439", "克利夫兰联储5年预期", "#765a9b"),
    "cleve_10y": ("G014102444", "克利夫兰联储10年预期", "#c94c4c"),
    "be_5y": ("G013233145", "5年盈亏平衡通胀率", "#765a9b"),
    "be_7y": ("G013233146", "7年盈亏平衡通胀率", "#ba7a2e"),
    "be_10y": ("G013233147", "10年盈亏平衡通胀率", "#c94c4c"),
    "be_20y": ("G013233148", "20年盈亏平衡通胀率", "#3c8b6d"),
    "five_year_five_year": ("G013233150", "5年后5年远期通胀补偿", "#1c3557"),
    "gasoline_weekly": ("S005948592", "EIA全美汽油零售价", "#c94c4c"),
    "manheim_yoy": ("G013050786", "Manheim二手车批发价同比", "#c94c4c"),
    "used_cars_cpi_yoy": ("G005419604", "CPI二手车和卡车同比", "#1c3557"),
    "gscpi": ("G016318950", "全球供应链压力指数", "#ba7a2e"),
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


def build_framework() -> dict[str, Any]:
    route = [
        {"id": "headline", "label": "总量读数", "question": "本月通胀有多高，环比动量是否加速？", "signals": ["CPI / 核心CPI", "PCE / 核心PCE", "环比分项贡献"]},
        {"id": "anatomy", "label": "结构拆分", "question": "冲击来自食品能源、核心商品、住房还是超级核心服务？", "signals": ["6211结构", "核心三分法", "23项温度表"]},
        {"id": "underlying", "label": "底层中枢", "question": "剔除极端项目后，价格分布的中部走到哪里？", "signals": ["中位CPI", "16%截尾均值CPI", "工资与单位劳动成本"]},
        {"id": "expectations", "label": "预期与锚", "question": "短期冲击是否进入家庭预期和长端市场定价？", "signals": ["密歇根 / 纽约联储SCE", "5y5y", "盈亏平衡通胀率"]},
        {"id": "leading", "label": "发布前先行", "question": "CPI公布前哪些分项可以被高频价格提前映射？", "signals": ["EIA汽油", "Manheim二手车", "供应链压力", "住房滞后链"]},
        {"id": "scenario", "label": "情景与复盘", "question": "油价冲击会停留在总体CPI，还是扩散成持续滞胀？", "signals": ["一阶直接效应", "二阶核心传导", "增长与就业", "制度缓冲"]},
    ]
    attribution = [
        {"id": "demand-gap", "label": "需求缺口", "equation": "菲利普斯曲线斜率", "signals": "V/U、失业率缺口、产出缺口", "reading": "区分经济是否进入低失业率下的非线性陡峭段。"},
        {"id": "supply-shock", "label": "供给冲击", "equation": "成本与供给项", "signals": "油价、PPI、供应链、关税", "reading": "先判断一次性价格水平位移，再判断是否向核心服务扩散。"},
        {"id": "expectation-anchor", "label": "预期与锚", "equation": "菲利普斯曲线截距", "signals": "Michigan、SCE、5y5y", "reading": "短端可波动，关键是长端对短期冲击的敏感度是否接近零。"},
        {"id": "policy-reaction", "label": "政策反应", "equation": "泰勒规则家族", "signals": "实际利率、r*、就业缺口、PCE", "reading": "规则是松紧标尺而非政策本身；双重使命冲突时需结合反应函数。"},
    ]
    passports = [
        {
            "id": "cpi", "name": "CPI", "publisher": "BLS 美国劳工统计局", "frequency": "月频；参考月后约两周发布",
            "coverage": "城市消费者现金支出，CPI-U覆盖约93%人口", "revision": "非季调指数原则上不修正；季调序列每年重估季调因子",
            "role": "市场定价之王；TIPS、通胀互换和fixing最终挂钩非季调指数水平",
            "caveat": "住房权重大且传导慢；单月环比须警惕残余季节性与特殊小分项。",
        },
        {
            "id": "pce", "name": "PCE物价指数", "publisher": "BEA 美国经济分析局", "frequency": "月频；通常月末发布",
            "coverage": "全部个人消费，含雇主或政府第三方代付支出", "revision": "随国民账户多轮修正，年度基准修订可改写历史",
            "role": "美联储2%通胀目标的正式口径；SEP预测采用该口径",
            "caveat": "发布时间晚于CPI/PPI，新增信息较少；链式权重、覆盖范围与CPI不可直接混同。",
        },
    ]
    dictionary = [
        ("headline_cpi", "总体CPI", "月", "%同比 / 季调环比", "iFinD直接值", "居民最终支付价格的总量温度计", "食品能源扰动大；同比受基数效应影响"),
        ("core_cpi", "核心CPI", "月", "%同比 / 季调环比", "iFinD直接值", "剔除食品能源后观察潜在通胀", "仍会被住房、二手车、机票等单项扰动"),
        ("core_goods", "核心商品CPI", "月", "%同比", "iFinD直接值", "供应链、美元与关税驱动的周期分项", "2021后结构可能变化；不能只按疫前零通胀外推"),
        ("shelter", "住房CPI", "月", "%同比 / 季调环比", "iFinD直接值", "核心通胀中权重最大、滞后最强", "OER不是房价或按揭成本；存量租约使拐点滞后"),
        ("supercore", "超级核心服务", "月", "%同比 / 季调环比", "CPI服务剔除住房", "观察工资密集型服务与就业市场紧度", "不同机构对能源、二手车等排除项定义不完全一致"),
        ("core_pce", "核心PCE", "月", "%同比", "iFinD直接值", "美联储观察底层通胀的主要总量指标", "2%目标正式对应总体PCE而非核心PCE"),
        ("median_cpi", "中位数CPI", "月", "%同比", "iFinD直接值", "读取价格变动分布的典型分项", "与核心CPI不同；历史起点和样本定义需看元数据"),
        ("trimmed_cpi", "16%截尾均值CPI", "月", "%同比", "iFinD直接值", "剔除分布两端后估计通胀中枢", "不是PPT所示Dallas截尾均值PCE，不能混称"),
        ("michigan", "密歇根通胀预期", "月", "%", "iFinD直接值", "家庭短期与长期通胀感受", "受汽油价格、问卷方式和党派情绪影响"),
        ("sce", "纽约联储SCE 1年预期", "月", "%中位数", "iFinD直接值", "概率式问法下的家庭短期预期", "与密歇根问法和样本不同，分歧本身是信息"),
        ("fiveyfivey", "5年后5年远期通胀补偿", "月", "%", "iFinD直接值", "观察长端预期对短期冲击的敏感度", "包含风险溢价和流动性溢价，不是纯预期"),
        ("gasoline", "EIA全美汽油零售价", "周→月", "美元/加仑；派生同比", "周频月均后计算同比", "CPI能源分项的发布前同步映射", "采价窗口与CPI不完全相同；还需电力和管道燃气"),
        ("manheim", "Manheim二手车价格指数", "月", "%同比", "iFinD直接值并向后平移2个月", "批发价领先CPI二手车零售价约两个月", "领先期是经验关系，不是固定机械映射"),
        ("gscpi", "纽约联储全球供应链压力指数", "月", "标准差", "iFinD直接值", "核心商品通胀的方向性管道信号", "不等于消费价格；传导时滞和弹性随周期变化"),
        ("eci", "ECI私营企业工资", "季", "%同比", "iFinD直接值", "工资密集型服务通胀的结构锚", "季度低频且行业结构变化会影响读数"),
        ("ulc", "非农商业单位劳动成本", "季", "%同比", "由iFinD指数计算4季同比", "把工资与生产率合并为成本标尺", "初值修订较大；短期异常季度不宜外推"),
    ]
    oil_shock_framework = {
        "title": "油价冲击：先分一阶、二阶与滞胀条件",
        "evidenceType": "PPT教学框架，不是实时预测",
        "steps": [
            {"id": "shock-type", "label": "识别冲击类型", "question": "油价上涨来自供给中断还是需求走强？", "boundary": "供给型与需求型油价上涨对增长和政策的含义不同。"},
            {"id": "first-round", "label": "一阶直接效应", "question": "能源权重×能源价格传导，再加食品直接影响是多少？", "boundary": "油价涨幅不能直接写成CPI贡献；PPT的10%油价→约0.2pp只是一组教学假设。"},
            {"id": "second-round", "label": "二阶核心传导", "question": "运输、投入成本、工资和预期是否进入核心服务？", "boundary": "传导间接、滞后且状态依赖，不能把0—0.2pp文献区间当固定系数。"},
            {"id": "stagflation", "label": "滞胀条件", "question": "弱增长、高失业、高通胀与预期松动是否持续共存？", "boundary": "单次油价上冲或短期衰退都不足以判定滞胀。"},
            {"id": "buffers", "label": "制度缓冲", "question": "能源依赖、净进口、工会/COLA、央行信誉是否不同于1970年代？", "boundary": "历史类比必须同时核对能源结构、劳动制度和政策反应，而非只比较油价。"},
        ],
        "pptPages": "85—93",
    }
    return {
        "title": "从读数到机制，再到发布前映射",
        "description": "依据培训材料第二章重排：先判总量，再拆结构；用底层指标验证广度，用调查与市场检验锚，接入可提前观察的高频价格，最后以情景框架检验油价冲击是否扩散为滞胀。",
        "route": route,
        "attribution": attribution,
        "oilShockFramework": oil_shock_framework,
        "passports": passports,
        "indicatorDictionary": [
            {"id": item_id, "name": name, "frequency": frequency, "unit": unit, "transformation": transformation, "interpretation": interpretation, "caveat": caveat, "definition": name}
            for item_id, name, frequency, unit, transformation, interpretation, caveat in dictionary
        ],
    }


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


def monthly_average(dates: list[str], values: list[float]) -> tuple[list[str], list[float]]:
    buckets: dict[str, list[float]] = {}
    for date, value in zip(dates, values):
        buckets.setdefault(date[:6], []).append(value)
    rows = []
    for period in sorted(buckets):
        year, month = int(period[:4]), int(period[4:6])
        month_end = calendar.monthrange(year, month)[1]
        rows.append((f"{period}{month_end:02d}", statistics.fmean(buckets[period])))
    return [date for date, _ in rows], [value for _, value in rows]


def shift_months(dates: list[str], months: int) -> list[str]:
    shifted = []
    for date in dates:
        absolute = int(date[:4]) * 12 + int(date[4:6]) - 1 + months
        year, month_zero = divmod(absolute, 12)
        month = month_zero + 1
        shifted.append(f"{year:04d}{month:02d}{calendar.monthrange(year, month)[1]:02d}")
    return shifted


def difference_series(
    left: tuple[list[str], list[float]],
    right: tuple[list[str], list[float]],
) -> tuple[list[str], list[float]]:
    left_map = {date[:6]: (date, value) for date, value in zip(*left)}
    right_map = {date[:6]: value for date, value in zip(*right)}
    rows = [
        (left_map[period][0], round(left_map[period][1] - right_map[period], 10))
        for period in sorted(set(left_map) & set(right_map))
    ]
    return [date for date, _ in rows], [value for _, value in rows]


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
    frequency: str = "月",
    raw_unit: str = "%",
    transformation: str = "iFinD直接值",
) -> dict[str, Any]:
    return {
        "id": series_id,
        "label": label,
        "dates": dates,
        "values": values,
        "color": color,
        "frequency": frequency,
        "defaultActive": True,
        "latestObservation": dates[-1],
        "latestValue": values[-1],
        "source": {
            "provider": "iFinD EDB",
            "institution": "iFinD 经济数据库",
            "code": code,
            "name": label,
            "rawUnit": raw_unit,
            "transformation": transformation,
            "url": "https://ft.51ifind.com",
            "latestObservation": dates[-1],
        },
    }


def build_chart(parsed: dict[str, tuple[list[str], list[float]]], keys: list[str]) -> list[dict[str, Any]]:
    return [
        series(
            series_id=key, label=SERIES_SPEC[key][1], dates=parsed[key][0],
            values=parsed[key][1], color=SERIES_SPEC[key][2], code=SERIES_SPEC[key][0],
            raw_unit="百分点" if key in CONTRIBUTION_KEYS else "%",
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
    goods_services = build_chart(parsed, ["cpi_goods_yoy", "cpi_services_yoy"])
    shelter_lag = build_chart(parsed, ["rent_yoy", "oer_yoy"])
    underlying = build_chart(parsed, ["core_cpi_yoy", "median_cpi_yoy", "trimmed_mean_cpi_yoy"])
    gap_dates, gap_values = difference_series(parsed["core_cpi_yoy"], parsed["core_pce_yoy"])
    cpi_pce_gap = [
        *build_chart(parsed, ["core_cpi_yoy", "core_pce_yoy"]),
        series(
            series_id="core_cpi_pce_gap", label="核心CPI－核心PCE（百分点）",
            dates=gap_dates, values=gap_values, color="#9aa0a6",
            code="DERIVED:G002600363-G003586807",
            raw_unit="%", transformation="核心CPI同比减核心PCE同比，结果单位为百分点",
        ),
    ]

    def monthly_profile(start_year: int, end_year: int) -> list[float]:
        buckets: dict[int, list[float]] = {month: [] for month in range(1, 13)}
        for date, value in zip(*parsed["core_cpi_mom"]):
            year, month = int(date[:4]), int(date[4:6])
            if start_year <= year <= end_year:
                buckets[month].append(value)
        return [round(statistics.fmean(buckets[month]), 4) if buckets[month] else 0.0 for month in range(1, 13)]

    january_effect = {
        "title": "季调后仍有1月效应",
        "description": "比较2015—2019与2022—2025各自然月核心CPI季调环比均值；若季调完全吸收稳定季节模式，各月均值不应系统性分化。",
        "months": list(range(1, 13)),
        "unit": "% m/m（季调后）",
        "series": [
            {"id": "pre_pandemic", "label": "2015—2019各月均值", "values": monthly_profile(2015, 2019), "color": "#929292"},
            {"id": "post_pandemic", "label": "2022—2025各月均值", "values": monthly_profile(2022, 2025), "color": "#c94c4c"},
        ],
        "source": {"provider": "iFinD EDB", "code": SERIES_SPEC["core_cpi_mom"][0]},
        "caveat": "2022—2025只有四个同月样本，图形用于提示残余季节性，不等于已通过显著性检验。",
    }
    cycle_rows = cycle_structure_stats(parsed)
    heatmap = build_heatmap(parsed)

    contribution_series = build_chart(parsed, CONTRIBUTION_KEYS)
    contribution_maps = [dict(zip(parsed[key][0], parsed[key][1])) for key in CONTRIBUTION_KEYS]
    cpi_mom_map = dict(zip(*parsed["cpi_mom"]))
    contribution_dates = sorted(set(cpi_mom_map).intersection(*(set(item) for item in contribution_maps)))
    contribution_residual = [
        round(cpi_mom_map[date] - sum(item[date] for item in contribution_maps), 10)
        for date in contribution_dates
    ]
    contribution_series.append(series(
        series_id="contribution_residual", label="残差/未覆盖",
        dates=contribution_dates, values=contribution_residual,
        color="#9aa0a6", code="DERIVED:CPI-MOM-MAPPED-COMPONENTS",
        raw_unit="百分点", transformation="总CPI季调环比减去四项iFinD直接影响值之和",
    ))

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
            raw_unit="2017年=100", transformation="由月度指数计算环比：(I_t / I_t-1 - 1) × 100%",
        ),
    ]

    ulc_dates, ulc_values = pct_change_series(*parsed["unit_labor_cost_index"], lag=4)
    wage_anchor = [
        series(
            series_id="eci_wage_yoy", label="ECI私营企业工资同比",
            dates=parsed["eci_wage_yoy"][0], values=parsed["eci_wage_yoy"][1],
            color="#c94c4c", code=SERIES_SPEC["eci_wage_yoy"][0], frequency="季",
        ),
        series(
            series_id="unit_labor_cost_yoy", label="单位劳动成本同比",
            dates=ulc_dates, values=[round(value, 4) for value in ulc_values],
            color="#ba7a2e", code=SERIES_SPEC["unit_labor_cost_index"][0], frequency="季",
            raw_unit="2017年=100", transformation="由季度指数计算4季同比：(I_t / I_t-4 - 1) × 100%",
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
        yoy_date_map = {date[:6]: date for date in yoy_dates}
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
            "observation": yoy_date_map[period],
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
                "latestObservation": yoy_date_map[period],
            },
        })

    survey_series = build_chart(parsed, SURVEY_KEYS)
    for item in survey_series:
        if item["id"] in ("cleve_1y", "cleve_5y", "cleve_10y"):
            item["dash"] = "3 4"
    survey_divergence = build_chart(parsed, ["mich_1y", "nyfed_sce_1y", "mich_5y"])
    survey_divergence[2]["dash"] = "5 4"

    five_year_five_year = build_chart(parsed, ["five_year_five_year"])

    gas_monthly_dates, gas_monthly_values = monthly_average(*parsed["gasoline_weekly"])
    gas_yoy_dates, gas_yoy_values = pct_change_series(gas_monthly_dates, gas_monthly_values, lag=12)
    energy_nowcast = [
        series(
            series_id="gasoline_yoy", label="EIA全美汽油零售价同比（月均）",
            dates=gas_yoy_dates, values=[round(value, 4) for value in gas_yoy_values],
            color="#c94c4c", code=SERIES_SPEC["gasoline_weekly"][0],
            raw_unit="美元/加仑", transformation="周频价格按月取算术平均，再计算12个月同比",
        ),
        series(
            series_id="cpi_energy_yoy", label="CPI能源同比",
            dates=parsed["cpi_energy_yoy"][0], values=parsed["cpi_energy_yoy"][1],
            color="#1c3557", code=SERIES_SPEC["cpi_energy_yoy"][0],
        ),
    ]
    gasoline_coverage_end = parsed["gasoline_weekly"][0][-1]
    energy_nowcast[0]["latestObservation"] = gasoline_coverage_end
    energy_nowcast[0]["source"]["latestObservation"] = gasoline_coverage_end
    energy_nowcast[0]["observationCoverageEnd"] = gasoline_coverage_end
    energy_nowcast[0]["displayPeriod"] = gas_yoy_dates[-1][:6]
    used_car_lead = [
        series(
            series_id="manheim_yoy_shifted", label="Manheim同比（向后平移2个月）",
            dates=shift_months(parsed["manheim_yoy"][0], 2), values=parsed["manheim_yoy"][1],
            color="#c94c4c", code=SERIES_SPEC["manheim_yoy"][0],
        ),
        series(
            series_id="used_cars_cpi_yoy", label="CPI二手车和卡车同比",
            dates=parsed["used_cars_cpi_yoy"][0], values=parsed["used_cars_cpi_yoy"][1],
            color="#1c3557", code=SERIES_SPEC["used_cars_cpi_yoy"][0],
        ),
    ]
    manheim_source_date = parsed["manheim_yoy"][0][-1]
    used_car_lead[0]["displayDateShiftMonths"] = 2
    used_car_lead[0]["latestObservation"] = manheim_source_date
    used_car_lead[0]["source"]["latestObservation"] = manheim_source_date

    def standardized(key: str) -> tuple[list[str], list[float]]:
        dates, values = parsed[key]
        sample = [value for date, value in zip(dates, values) if date >= "20150101"]
        mean = statistics.fmean(sample)
        scale = statistics.pstdev(sample) or 1.0
        return dates, [round((value - mean) / scale, 4) for value in values]

    gscpi_dates, gscpi_values = standardized("gscpi")
    goods_dates, goods_values = standardized("cpi_goods_yoy")
    goods_pipeline = [
        series(series_id="gscpi", label="全球供应链压力（标准化）", dates=gscpi_dates, values=gscpi_values, color="#ba7a2e", code=SERIES_SPEC["gscpi"][0], raw_unit="标准差", transformation="按2015年以来样本计算z-score"),
        series(series_id="cpi_goods_yoy", label="核心商品CPI同比（标准化）", dates=goods_dates, values=goods_values, color="#1c3557", code=SERIES_SPEC["cpi_goods_yoy"][0], raw_unit="%", transformation="按2015年以来样本计算z-score"),
    ]

    breakeven_series = build_chart(parsed, BREAKEVEN_KEYS)
    latest_curve = [
        {"tenor": item["label"].replace("盈亏平衡通胀率", ""), "value": item["latestValue"], "observation": item["latestObservation"]}
        for item in breakeven_series
    ]

    headline_lookup = {item["id"]: item for item in survey_series + breakeven_series}
    pce_lookup = {item["id"]: item for item in pce_trend}

    return {
        "schemaVersion": 5,
        "generatedAt": generated_at,
        "source": "iFinD EDB",
        "sourceProviders": ["iFinD EDB"],
        "framework": build_framework(),
        "headline": [
            {"id": "actual", "label": "实际通胀", "title": "核心PCE同比", "value": pce_lookup["core_pce_yoy"]["latestValue"], "unit": "%", "observation": pce_lookup["core_pce_yoy"]["latestObservation"], "source": "iFinD EDB"},
            {"id": "survey", "label": "调查通胀", "title": "密歇根大学1年预期", "value": headline_lookup["mich_1y"]["latestValue"], "unit": "%", "observation": headline_lookup["mich_1y"]["latestObservation"], "source": "iFinD EDB"},
            {"id": "implied", "label": "市场隐含", "title": "5y5y远期通胀补偿", "value": five_year_five_year[0]["latestValue"], "unit": "%", "observation": five_year_five_year[0]["latestObservation"], "source": "iFinD EDB"},
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
            "goodsServices": {
                "id": "goods-services", "eyebrow": "ANATOMY · GOODS vs SERVICES",
                "title": "商品通胀与服务通胀的分化", "description": "1995—2020年核心商品长期接近零；2021年后供应链、需求与关税冲击使商品通胀重返分析中心。服务价格更受住房和工资约束，回落通常更慢。",
                "unit": "%", "reference": 0, "defaultRange": "ALL", "series": goods_services,
            },
            "shelterLag": {
                "id": "shelter-lag", "eyebrow": "ANATOMY · SHELTER LAG",
                "title": "租金与业主等价租金", "description": "CPI租金衡量存量租约平均，OER用可比租赁房租金插补自住住房服务；二者不是房价或按揭支出，并因样本轮换与租约更新而滞后即时市场租金。",
                "unit": "%", "reference": 0, "defaultRange": "10Y", "series": shelter_lag,
                "availability": "iFinD暂未检索到BLS新租户租金研究序列，因此本图不伪造4—6季度领先线。",
            },
            "underlying": {
                "id": "underlying-inflation", "eyebrow": "UNDERLYING · DISTRIBUTION",
                "title": "底层通胀：核心、中位数与截尾均值", "description": "核心CPI固定剔除食品能源；中位数CPI读取价格变动分布中部；16%截尾均值CPI逐月剔除两端。共同方向比单个读数更能判断通胀广度。",
                "unit": "%", "reference": 2, "defaultRange": "ALL", "series": underlying,
                "caveat": "iFinD可得的是16%截尾均值CPI，不是PPT图中的Dallas截尾均值PCE；页面严格按源名称标注。",
            },
            "cpiPceGap": {
                "id": "cpi-pce-gap", "eyebrow": "MEASUREMENT · CPI vs PCE",
                "title": "核心CPI、核心PCE及其差值", "description": "差值＝核心CPI同比－核心PCE同比。住房、医疗权重，覆盖范围与指数公式共同决定差值；不能用固定0.3—0.5个百分点机械换算。",
                "unit": "%", "reference": 2, "defaultRange": "10Y", "series": cpi_pce_gap,
            },
            "januaryEffect": january_effect,
            "cpiPceWeights": {
                "title": "同一经济，两套近似权重",
                "description": "PPT教学近似：住房在CPI权重更高，医疗和其他项目在PCE权重更高，是两指数长期差异的重要结构来源。",
                "categories": ["住房", "医疗保健", "交通（含能源）", "食品饮料", "其他商品与服务"],
                "cpi": [36, 8, 16, 14, 26],
                "pce": [15, 17, 10, 13, 45],
                "unit": "%",
                "asOf": "PPT教学近似，非当期精确权重",
                "caveat": "CPI为BLS相对重要性、PCE为BEA支出构成推算；权重随时间变化，正式定量分解应读取对应期官方权重。",
            },
            "specialComponents": [
                {"name": "医疗保险", "mechanism": "用保险公司留存收益而非保费直接测价，年度基期切换可造成连续机械涨跌。", "use": "出现异常时先判断算法效应，不把它当作当期医疗成本。"},
                {"name": "机票", "mechanism": "抽样票价受油价、假日和里程兑换口径影响，月度波动很大。", "use": "单月异动不构成趋势；CPI与PCE映射口径不同。"},
                {"name": "酒店", "mechanism": "样本较小、季节性强，是核心CPI单月意外的常见来源。", "use": "与住房存量租金分开阅读。"},
                {"name": "服装", "mechanism": "清仓、新品上架与样本轮换导致残余季节性。", "use": "尤其谨慎解读1月季调后环比。"},
                {"name": "二手车", "mechanism": "CPI零售价约滞后Manheim批发拍卖价两个月。", "use": "可在CPI发布前判断方向，但领先期不是恒定参数。"},
            ],
            "coreSplit": {
                "id": "core-split", "eyebrow": "ACTUAL · CYCLE vs STRUCTURE",
                "title": "核心通胀三分项", "description": "按核心商品、住房与超级核心服务拆分；总量核心CPI只是三者的加权平均，不直接携带机制信息。",
                "unit": "%", "reference": 2, "defaultRange": "5Y", "series": core_split,
            },
            "cpiContributions": {
                "id": "cpi-contributions", "eyebrow": "ACTUAL · CONTRIBUTION",
                "title": "CPI环比分项贡献", "description": "四项为iFinD季调分项对CPI环比的直接影响值；另列“残差/未覆盖”使堆叠与总CPI环比逐月闭合，残差不解释为独立经济分项。",
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
                "title": "周期与结构：四项描述性诊断",
                "description": "年度波动率、年度均值AR(1)半衰期、与ECI工资同比的相关性、相对2015—2019均值的归位度共同描述分项特征；分类为研究框架预设，不是统计模型自动识别，相关性也不代表因果。",
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
            "divergence": {
                "id": "survey-divergence", "eyebrow": "EXPECTATIONS · SURVEY DIVERGENCE",
                "title": "两大消费者调查及长期预期", "description": "密歇根调查与纽约联储SCE在问法、样本和统计量上不同。两者劈叉时，不把任何一条机械称为真实值，而是结合市场定价和长期预期判断情绪污染程度。",
                "unit": "%", "reference": 2, "defaultRange": "10Y", "series": survey_divergence,
            },
            "expectations": {
                "id": "survey-expectations", "eyebrow": "SURVEY · EXPECTATIONS",
                "title": "居民与模型通胀预期", "description": "密歇根大学居民调查与克利夫兰联储模型预期，二者口径不同，分开阅读。",
                "unit": "%", "reference": 2, "defaultRange": "5Y", "series": survey_series,
            },
        },
        "implied": {
            "fiveYearFiveYear": {
                "id": "five-year-five-year", "eyebrow": "MARKET · LONG-TERM ANCHOR",
                "title": "5年后5年远期通胀补偿", "description": "观察未来第6—10年的平均通胀补偿。长端对当期通胀冲击不敏感，是“锚定”的操作性证据；但该指标仍包含通胀风险溢价与TIPS流动性因素。",
                "unit": "%", "reference": 2, "defaultRange": "ALL", "series": five_year_five_year,
            },
            "breakeven": {
                "id": "breakeven-curve", "eyebrow": "MARKET · BREAKEVEN",
                "title": "盈亏平衡通胀率期限结构", "description": "名义国债与TIPS价差隐含的通胀定价，含风险与流动性溢价，非无偏预测。",
                "unit": "%", "reference": 2, "defaultRange": "3Y", "series": breakeven_series,
            },
            "latestCurve": latest_curve,
        },
        "leading": {
            "energyNowcast": {
                "id": "energy-nowcast", "eyebrow": "LEADING · ENERGY",
                "title": "汽油零售价与CPI能源", "description": f"EIA周频全美汽油零售价先按月取算术平均，再计算同比，与CPI能源同比对齐。它的领先主要来自发布时间更早，而不是固定跨月领先；最新月内均值仅覆盖至{gasoline_coverage_end[:4]}-{gasoline_coverage_end[4:6]}-{gasoline_coverage_end[6:8]}。",
                "unit": "%", "reference": 0, "defaultRange": "10Y", "series": energy_nowcast,
                "formula": "Gasoline YoY_t = (当月周频汽油价均值 / 上年同月均值 - 1) × 100%",
            },
            "usedCarLead": {
                "id": "used-car-lead", "eyebrow": "LEADING · USED CARS",
                "title": "Manheim批发价领先CPI二手车", "description": "按PPT经验关系将Manheim同比向后平移2个月，与CPI二手车和卡车同比比较。平移只服务于拐点对照，不改变源观测值。",
                "unit": "%", "reference": 0, "defaultRange": "10Y", "series": used_car_lead,
                "formula": "图上日期 = Manheim原观测月 + 2个月；数值不变",
            },
            "goodsPipeline": {
                "id": "goods-pipeline", "eyebrow": "LEADING · SUPPLY CHAIN",
                "title": "供应链压力与核心商品通胀", "description": "两条序列单位不同，均按各自2015年以来样本做z-score标准化后比较方向；不把标准化值解释为通胀百分点。",
                "unit": "z-score", "reference": 0, "defaultRange": "10Y", "series": goods_pipeline,
                "formula": "z = (x - 2015年以来样本均值) / 样本标准差",
            },
            "toolkit": [
                {"name": "Cleveland Fed Inflation Nowcast", "target": "总体与核心CPI/PCE当月估计", "lead": "发布前", "status": "unavailable", "note": "本轮iFinD检索未发现可验证序列，不用替代值冒充。"},
                {"name": "EIA全美汽油零售价", "target": "CPI能源与总体CPI", "lead": "周频、同月映射", "status": "derived", "note": "iFinD周频价格聚合为月均后计算同比。"},
                {"name": "Manheim二手车批发价", "target": "CPI二手车分项", "lead": "约2个月", "status": "direct", "note": "iFinD直接同比，图中仅平移日期以观察对应关系。"},
                {"name": "BLS新租户租金", "target": "未来CPI租金/OER", "lead": "约4—6季度", "status": "unavailable", "note": "iFinD暂未检索到该研究序列，住房图只展示存量租金口径。"},
                {"name": "PPI映射", "target": "当月核心PCE", "lead": "PCE发布前", "status": "partial", "note": "页面保留方法说明；医疗、机票等需逐项维护映射，不用单一PPI总量替代。"},
                {"name": "全球供应链压力指数", "target": "核心商品CPI方向", "lead": "经验上3—6个月", "status": "direct", "note": "iFinD直接序列；页面标准化比较，领先期不作固定参数。"},
            ],
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
