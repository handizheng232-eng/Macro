export type UsMacroCategory =
  | 'employment'
  | 'inflation'
  | 'growth'
  | 'consumption'
  | 'housing'
  | 'investment'
  | 'pmi'
  | 'fiscal'
  | 'fed'

export type UsMacroDatasetCategory = 'growth' | 'employment' | 'inflation' | 'policy'

export type UsMacroIndicator = {
  name: string
  role: string
  source: string
  frequency: string
  trap: string
}

export type UsMacroPage = {
  category: UsMacroCategory
  chapter: string
  slug: string
  label: string
  detail: string
  description: string
  thesis: string
  chain: string[]
  indicators: UsMacroIndicator[]
  dataCategory?: UsMacroDatasetCategory
  metricIds?: string[]
  coverage: 'deep' | 'partial' | 'framework'
}

export const US_MACRO_PAGES: UsMacroPage[] = [
  {
    category: 'employment',
    chapter: '01',
    slug: 'us-employment',
    label: '就业',
    detail: '供给 · 松弛 · 需求 · 工资工时',
    description: '从CES与CPS双调查出发，联结岗位、人员、工时和工资压力。',
    thesis: '就业既是美联储双重使命的目标，也是工资—服务通胀链条的上游变量。',
    chain: ['招聘与岗位空缺', '就业与总工时', '失业与参与', '工资与服务通胀', '美联储反应函数'],
    indicators: [
      { name: '非农就业与修正', role: '岗位流量与行业广度', source: 'BLS · CES', frequency: '月频', trap: '初值修正、出生死亡模型与基准修订' },
      { name: '失业率与参与率', role: '劳动力供需相抵后的结果', source: 'BLS · CPS', frequency: '月频', trap: '每年1月人口控制跳变；优先看25—54岁参与率' },
      { name: '初请与续请失业金', role: '裁员与再就业难度的周频信号', source: 'DOL', frequency: '周频', trap: '假日、车厂停工与单州异动；看4周均值' },
      { name: 'JOLTS V/U', role: '每名失业者对应的岗位空缺', source: 'BLS · JOLTS', frequency: '月频', trap: '发布滞后且回复率下降' },
      { name: 'AHE / ECI / Wage Tracker', role: '工资压力的快报、确认与同人跟踪', source: 'BLS / Atlanta Fed', frequency: '月/季频', trap: 'AHE有组成偏差，三口径不可混用' },
    ],
    coverage: 'deep',
  },
  {
    category: 'inflation',
    chapter: '02',
    slug: 'us-inflation',
    label: '通胀',
    detail: 'CPI · PCE · 预期 · 市场定价',
    description: '拆分商品、住房与非住房核心服务，并区分实际通胀、调查预期和市场定价。',
    thesis: '市场交易信息增量最大的CPI，政策目标则是PCE；两者的重要性不能混同。',
    chain: ['上游成本与供给', 'CPI分项', 'PCE目标口径', '通胀预期', '实际利率与政策'],
    indicators: [
      { name: 'CPI总项与核心', role: '最早的月度消费价格硬数据', source: 'BLS', frequency: '月频', trap: '1月季调漂移；住房权重大且滞后' },
      { name: 'PCE总项与核心', role: '美联储2%目标的正式口径', source: 'BEA', frequency: '月频', trap: '发布较晚且随国民账户反复修订' },
      { name: 'PPI与投入成本', role: '推算PCE并识别上游价格压力', source: 'BLS', frequency: '月频', trap: '不是简单的“批发价”，需按PCE映射权重' },
      { name: '调查通胀预期', role: '家庭与专业预测者的价格锚', source: 'Michigan / NY Fed / SPF', frequency: '月/季频', trap: '问卷措辞、党派与汽油价格会污染结果' },
      { name: '盈亏平衡通胀与5y5y', role: '市场定价的通胀补偿', source: 'Treasury / FRED', frequency: '日频', trap: '含流动性与风险溢价，不等于纯预期' },
    ],
    coverage: 'deep',
  },
  {
    category: 'growth',
    chapter: '03',
    slug: 'us-growth',
    label: 'GDP与核算',
    detail: '潜在增速 · GDP/GDI · Nowcast',
    description: '以潜在增速为标尺，从支出、收入与最终私人内需三个口径判断总量。',
    thesis: 'GDP是季度内已知数据的会计汇总；读数应与潜在增速、GDI和修订历史一起解释。',
    chain: ['潜在增速', '最终私人内需', 'GDP与GDI', '初值与年度修订', 'Nowcast与WEI'],
    indicators: [
      { name: '实际GDP环比折年', role: '季度总量增长', source: 'BEA', frequency: '季频', trap: 'SAAR放大噪音；初值会多轮修订' },
      { name: '最终私人国内需求', role: '剔除库存、贸易与政府后的核心内需', source: 'BEA', frequency: '季频', trap: '不能替代GDP，只用于识别内生动能' },
      { name: 'GDI与GDP/GDI平均值', role: '从收入侧交叉验证产出', source: 'BEA', frequency: '季频', trap: '两者均会修订，背离不是即时定论' },
      { name: 'GDPNow / NY Fed Nowcast', role: '填补季度统计滞后', source: 'Atlanta / NY Fed', frequency: '高频', trap: 'Nowcasting不是预测未来' },
    ],
    dataCategory: 'growth',
    metricIds: ['real-gdp-growth'],
    coverage: 'partial',
  },
  {
    category: 'consumption',
    chapter: '04',
    slug: 'us-consumption',
    label: '消费',
    detail: '零售 · PCE · 收入储蓄 · 高频',
    description: '围绕收入、财富、信贷和信心四个驱动轮，区分商品快报与服务慢报。',
    thesis: '消费占GDP约三分之二且相对平滑；体量看服务，波动看耐用品，最快硬数据看零售控制组。',
    chain: ['就业与收入', '财富与信贷', '零售控制组', '实际PCE', '储蓄与消费韧性'],
    indicators: [
      { name: '零售销售控制组', role: '商品消费与GDP核算的最快代理', source: 'Census', frequency: '月频', trap: '全部是名义值，不能直接当实际消费量' },
      { name: '实际个人消费支出', role: '商品与服务的完整实际消费', source: 'BEA', frequency: '月频', trap: '发布较慢且受价格平减选择影响' },
      { name: '可支配收入与储蓄率', role: '消费资金来源与缓冲', source: 'BEA', frequency: '月频', trap: '储蓄率是残差，修订幅度大' },
      { name: '信用卡与服务高频', role: '弥补服务消费的统计滞后', source: '银行 / 私人机构', frequency: '周频', trap: '覆盖人群、名义口径与样本漂移' },
      { name: 'Michigan / Conference Board', role: '情绪与劳动力市场感知', source: '调查机构', frequency: '月频', trap: '党派劈叉；软数据对实际消费指示力下降' },
    ],
    dataCategory: 'growth',
    metricIds: ['retail-sales-mom', 'nominal-pce-yoy'],
    coverage: 'partial',
  },
  {
    category: 'housing',
    chapter: '05',
    slug: 'us-housing',
    label: '住房',
    detail: '房贷 · 开工 · 销量库存 · 房价房租',
    description: '按利率—申请—销售—开工—价格—住房通胀的顺序跟踪最利率敏感的部门。',
    thesis: '住房是货币政策最先传导的实体部门；30年固定房贷的锁定效应会造成量崩而价稳。',
    chain: ['国债与MBS利率', '房贷申请', '新屋销售与许可', '开工与建造', '库存与房价', 'CPI住房项'],
    indicators: [
      { name: '30年房贷利率与MBA申请', role: '融资条件与需求第一环', source: 'Freddie Mac / MBA', frequency: '周频', trap: '再融资与购房申请需分开' },
      { name: '营建许可与新屋开工', role: '住宅投资领先量', source: 'Census', frequency: '月频', trap: '天气与多户型项目造成月度噪音' },
      { name: '新屋/成屋销售与库存', role: '交易量、供给与锁定效应', source: 'Census / NAR', frequency: '月频', trap: '新屋和成屋统计口径、样本与签约时点不同' },
      { name: 'FHFA / Case-Shiller / Zillow', role: '房价趋势与覆盖差异', source: 'FHFA / S&P / Zillow', frequency: '月频', trap: '房价是滞后指标，指数口径不可直接拼接' },
      { name: '新租约租金与OER', role: '领先并解释CPI住房通胀', source: 'BLS / Zillow', frequency: '月频', trap: 'CPI租金样本轮换导致约一年滞后' },
    ],
    coverage: 'framework',
  },
  {
    category: 'investment',
    chapter: '06',
    slug: 'us-investment',
    label: '企业投资',
    detail: '设备 · 建筑 · 知识产权 · AI资本开支',
    description: '把投资作为当期需求与未来供给，联结订单、出货、建造和企业微观资本开支。',
    thesis: '设备、建筑和知识产权有不同周期；AI资本开支必须用官方核算与企业财报双向验证。',
    chain: ['需求与产能利用率', '核心资本品订单', '出货与设备投资', '建造支出', '知识产权与生产率'],
    indicators: [
      { name: '核心资本品订单', role: '设备投资的月频前瞻代理', source: 'Census · Durable Goods', frequency: '月频', trap: '剔除国防与飞机，订单不能直接当GDP投资' },
      { name: '核心资本品出货', role: '设备投资核算的同步代理', source: 'Census', frequency: '月频', trap: '名义值需结合价格与进口结构' },
      { name: '私人非住宅建造支出', role: '厂房与数据中心建设周期', source: 'Census', frequency: '月频', trap: '项目长、修订大，制造业与数据中心需分项' },
      { name: 'Hyperscaler Capex', role: 'AI投资的企业前瞻信号', source: '公司财报', frequency: '季频', trap: '含土地与海外，不能与美国GDP口径直接相加' },
      { name: 'NFIB资本开支计划', role: '中小企业投资广度', source: 'NFIB', frequency: '月频', trap: '意向是软数据，需与订单和建造交叉验证' },
    ],
    coverage: 'framework',
  },
  {
    category: 'pmi',
    chapter: '07',
    slug: 'us-pmi',
    label: 'PMI与库存',
    detail: '制造业 · 新订单库存 · 价格 · 地区联储',
    description: '用制造业的高波动和牛鞭效应识别3—4年库存周期及跨资产共同因子。',
    thesis: 'PMI衡量改善的广度而非强度；50并非GDP零增长，新订单—库存差才是更领先的组合。',
    chain: ['地区联储调查', 'S&P Flash PMI', 'ISM新订单', '库存与生产', '商品价格与资产'],
    indicators: [
      { name: 'ISM制造业PMI', role: '最早的全国制造业扩散指数', source: 'ISM', frequency: '月频', trap: '50约对应潜在增长，约40才接近GDP零增长' },
      { name: '新订单−库存差', role: '领先总指数与生产约3个月', source: 'ISM', frequency: '月频', trap: '扩散指数不等于实际增速幅度' },
      { name: 'ISM价格支付', role: 'PPI/CPI商品项的1—3个月先行信号', source: 'ISM', frequency: '月频', trap: '关税与交付时间会改变传导强度' },
      { name: '制造/批发/零售库存销售比', role: '识别主动与被动补去库', source: 'Census', frequency: '月频', trap: '库存通常滞后需求，需与订单联合判断' },
      { name: '地区联储与S&P Flash', role: '月内逐次修正ISM预期', source: 'Regional Feds / S&P', frequency: '月频', trap: '单区样本噪音大，宜合成而非单看' },
    ],
    dataCategory: 'growth',
    metricIds: ['ism-manufacturing', 'manufacturing-production'],
    coverage: 'partial',
  },
  {
    category: 'fiscal',
    chapter: '08',
    slug: 'us-fiscal-treasury',
    label: '财政与国债',
    detail: '赤字 · QRA · 拍卖 · 期限溢价',
    description: '把国会决定的赤字与财政部决定的融资结构分开，连接现金流、久期供给与利率。',
    thesis: '“为什么借、借多少”主要由国会决定；“怎么借、借多久”由财政部通过QRA和拍卖执行。',
    chain: ['立法与拨款', '收入支出与赤字', '借款需求', 'QRA期限结构', '拍卖需求', '期限溢价与流动性'],
    indicators: [
      { name: 'DTS / MTS', role: '日度现金流与月度官方收支', source: 'US Treasury', frequency: '日/月频', trap: '强季节性；税收时点与退税会扭曲短期同比' },
      { name: 'CBO评分与基线', role: '法案和十年赤字路径的市场基准', source: 'CBO', frequency: '事件/年度', trap: '基线依赖法律延续假设，不等于最可能情景' },
      { name: 'QRA与TBAC', role: '总借款与券种期限结构', source: 'US Treasury', frequency: '季频', trap: '总融资量和coupon久期供给必须分开' },
      { name: '拍卖三指标', role: 'BTC、indirect与tail/through识别需求', source: 'US Treasury', frequency: '每周多次', trap: '单次拍卖噪音大，需和自身历史及连续信号比较' },
      { name: '期限溢价', role: '久期供需对长端的风险补偿', source: 'NY Fed / Fed models', frequency: '日频', trap: '模型水平差异大，重方向轻绝对值' },
    ],
    dataCategory: 'policy',
    metricIds: ['federal-deficit', 'federal-spending-growth'],
    coverage: 'partial',
  },
  {
    category: 'fed',
    chapter: '09',
    slug: 'us-fed-financial-conditions',
    label: '美联储与金融条件',
    detail: '反应函数 · 流动性 · 定价 · 传导',
    description: '从双重使命、FOMC信息流和资产负债表，走到政策路径定价与实体传导。',
    thesis: '政策利率只是起点，实体经济感受到的是国债、房贷、信用、美元和股价共同构成的金融条件。',
    chain: ['就业与通胀缺口', 'FOMC沟通', '政策路径定价', '准备金与货币市场', '金融条件', '实体经济'],
    indicators: [
      { name: '声明 / 记者会 / SEP / 纪要', role: '政策行动、路径与分歧', source: 'Federal Reserve', frequency: '每次会议', trap: '点阵图是个人预测集合，不是委员会承诺' },
      { name: 'EFFR / IORB / ON RRP / SOFR', role: '利率走廊与资金面松紧', source: 'NY Fed / Federal Reserve', frequency: '日频', trap: '无抵押与回购市场口径不同' },
      { name: '准备金 / TGA / ON RRP', role: '联储负债端的流动性分配', source: 'H.4.1 / Treasury', frequency: '日/周频', trap: '三者此消彼长，不能只看总资产' },
      { name: 'FF期货与OIS', role: '会议概率、路径与终点利率定价', source: 'CME / market', frequency: '日内', trap: '概率依赖离散情景假设；远月更多是路径而非单次会议' },
      { name: 'FCI / 2Y / 曲线 / 美元 / 利差', role: '政策传导与经济自稳定器', source: 'Fed / Chicago Fed / market', frequency: '日/周/月频', trap: '不同FCI水平不可横比，相关不等于因果' },
    ],
    dataCategory: 'policy',
    metricIds: ['effective-fed-funds', 'fed-total-assets'],
    coverage: 'partial',
  },
]

export function categoryFromFrameworkHash(hash: string): UsMacroCategory | null {
  const slug = hash.replace(/^#framework\/?/, '')
  return US_MACRO_PAGES.find((page) => page.slug === slug)?.category ?? null
}

export function frameworkSlug(category: UsMacroCategory): string {
  return US_MACRO_PAGES.find((page) => page.category === category)?.slug ?? 'us-growth'
}
