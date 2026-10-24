// Overview only: official policy anchors are not completed market research.
export type OverviewSubperiod = {
  number: string
  period: string
  title: string
  status: string
  thesis: string
  fed: string
  treasury: string
  dollar: string
  question: string
  source: string
  sourceLabel: string
  extraSources?: { href: string; label: string }[]
}

const statement = (date: string) => `https://www.federalreserve.gov/newsevents/pressreleases/monetary${date}a.htm`
const qtPlan = 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20220504b.htm'

export const inflationOverview = {
  period: '2022-03-16至2024-09-17',
  thesis: '分期方案 / 待复盘：从加息与QT并行，转向高利率维持，再到QT减速与降息准备。',
  boundary: '以2022年3月16日首次加息为起点，覆盖至2024年9月17日。2024年9月18日首次降息仅作下一时期衔接，不重复归入本期正文。',
  fed: '政策事实见下方官方锚点：分别观察加息节奏、利率维持时间与缩表安排，不将QT减速等同于降息。',
  treasury: '待检验问题：政策路径、实际利率与期限溢价，分别如何影响短端、长端及曲线？',
  dollar: '待检验问题：利差、相对增长和避险需求，在不同政策阶段如何共同影响美元？',
  question: '研究主线：抗通胀约束如何演变，银行压力与就业风险何时改变政策权衡？本页不预先给出行情结论。',
  source: statement('20220316'),
  sourceLabel: '美联储：2022-03-16 加息声明',
}

export const inflationSubperiods: OverviewSubperiod[] = [
  {
    number: '09.1', period: '2022-03-16至2022-05-31', title: '加息启动与缩表定调', status: '待复盘',
    thesis: '阶段观察：政策利率开始上调，缩表由讨论转为明确的实施安排。',
    fed: '3月16日上调目标区间至0.25%—0.50%；5月4日升至0.75%—1.00%，并公布6月1日开始缩表的计划。',
    treasury: '待检验问题：短端对加息路径的调整，与长端对实际利率及缩表的调整是否同步？',
    dollar: '待检验问题：美国政策转向与海外政策差异，对美元的支撑如何区分？',
    question: '加息启动和缩表预告，分别改变了哪些预期？',
    source: statement('20220316'), sourceLabel: '美联储：2022-03-16 声明',
    extraSources: [{ href: statement('20220504'), label: '2022-05-04 声明' }, { href: qtPlan, label: '2022-05-04 缩表计划' }],
  },
  {
    number: '09.2', period: '2022-06-01至2022-11-30', title: '激进加息与QT并行', status: '待复盘',
    thesis: '阶段观察：加息与资产负债表收缩并行，累计紧缩及传导时滞进入政策表述。',
    fed: '缩表按计划从6月1日启动；6月15日目标区间升至1.50%—1.75%，11月2日升至3.75%—4.00%，并明确考虑累计紧缩及政策时滞。',
    treasury: '待检验问题：曲线变化更多来自终点利率上修，还是增长风险与通胀补偿的变化？',
    dollar: '待检验问题：利差和避险需求能否分别解释美元的阶段表现？',
    question: '如何区分加息幅度、累计限制性与QT的传导？',
    source: statement('20221102'), sourceLabel: '美联储：2022-11-02 声明',
    extraSources: [{ href: qtPlan, label: '缩表实施计划' }, { href: statement('20220615'), label: '2022-06-15 声明' }],
  },
  {
    number: '09.3', period: '2022-12-01至2023-02-28', title: '加息降速与终点之争', status: '待复盘',
    thesis: '阶段观察：加息步幅收窄，但继续收紧的方向并未在当时结束。',
    fed: '12月14日目标区间升至4.25%—4.50%，2月1日升至4.50%—4.75%；两次声明仍预计继续加息，QT继续。',
    treasury: '待检验问题：加息降速是否被定价为更低的终点，或只是更慢到达同一终点？',
    dollar: '待检验问题：美元对加息速度和最终利差的反应是否不同？',
    question: '“加得更慢”为何不能直接等同于转向宽松？',
    source: statement('20221214'), sourceLabel: '美联储：2022-12-14 声明',
    extraSources: [{ href: statement('20230201'), label: '2023-02-01 声明' }],
  },
  {
    number: '09.4', period: '2023-03-01至2023-06-30', title: '银行压力与紧缩权衡', status: '待复盘',
    thesis: '阶段观察：信贷条件收紧的影响，与仍然偏高的通胀并列进入政策权衡。',
    fed: '3月22日声明提示银行业发展可能收紧信贷、影响活动与就业，影响程度不确定；6月14日维持5.00%—5.25%以评估新增信息，QT继续。',
    treasury: '待检验问题：短端降息预期与长端避险需求，是否反映不同风险？',
    dollar: '待检验问题：美国银行压力下，避险需求与政策路径重估如何拉扯美元？',
    question: '信贷收紧在多大程度上改变继续加息的必要性？',
    source: statement('20230322'), sourceLabel: '美联储：2023-03-22 声明',
    extraSources: [{ href: statement('20230614'), label: '2023-06-14 声明' }],
  },
  {
    number: '09.5', period: '2023-07-01至2023-10-31', title: '高利率维持与长端重估', status: '待复盘',
    thesis: '阶段观察：关注点由加息步幅，扩展到限制性维持时间与长端金融条件。',
    fed: '7月26日目标区间升至5.25%—5.50%；10月19日鲍威尔指出，长期债券收益率是近期金融条件收紧的重要驱动因素。',
    treasury: '待检验问题：长端变化中，政策路径、实际利率与期限溢价各有多大作用？',
    dollar: '待检验问题：较高长端收益率是否必然增强美元，还是取决于背后的增长与风险因素？',
    question: '金融条件收紧与政策利率上调，何时可能形成替代或叠加？',
    source: statement('20230726'), sourceLabel: '美联储：2023-07-26 声明',
    extraSources: [{ href: 'https://www.federalreserve.gov/newsevents/speech/powell20231019a.htm', label: '鲍威尔：2023-10-19 讲话' }],
  },
  {
    number: '09.6', period: '2023-11-01至2023-12-31', title: '通胀降温与降息路径浮现', status: '待复盘',
    thesis: '阶段观察：通胀降温的确认，与未来适当利率路径的讨论并列出现。',
    fed: '12月13日声明称过去一年通胀有所缓解但仍偏高，维持5.25%—5.50%；同期SEP展示与会者的条件性利率预测，不是委员会降息承诺。',
    treasury: '待检验问题：政策路径预期的变化，与期限溢价变化能否分开识别？',
    dollar: '待检验问题：降息预期与海外增长差异，哪一项更能解释美元变化？',
    question: '如何区分与会者预测、市场定价与真正的政策决定？',
    source: statement('20231213'), sourceLabel: '美联储：2023-12-13 声明',
    extraSources: [{ href: 'https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20231213.htm', label: '2023-12 SEP 预测' }],
  },
  {
    number: '09.7', period: '2024-01-01至2024-05-31', title: '通胀反复与降息等待', status: '待复盘',
    thesis: '阶段观察：通胀进展不足使降息继续等待，缩表减速则先行宣布。',
    fed: '5月1日声明称近月通胀目标缺乏进一步进展，维持5.25%—5.50%，降息需更有信心；同时宣布6月起降低国债月度缩表上限。',
    treasury: '待检验问题：降息时点推后，对短端与长端的影响是否一致？',
    dollar: '待检验问题：政策分化与相对增长，如何影响美元利差支撑？',
    question: '降息等待与QT减速为何可以同时出现？',
    source: statement('20240501'), sourceLabel: '美联储：2024-05-01 声明',
  },
  {
    number: '09.8', period: '2024-06-01至2024-09-17', title: 'QT减速与降息准备', status: '待复盘',
    thesis: '阶段观察：缩表减速实施，政策讨论逐步转向通胀与就业风险的再平衡。',
    fed: '6月起国债月度缩表上限由600亿降至250亿美元；8月23日鲍威尔表示政策调整时机已到，降息时间与节奏仍取决于数据、前景和风险平衡。',
    treasury: '待检验问题：短端对降息准备的反应，如何区别于QT减速对资金与期限结构的影响？',
    dollar: '待检验问题：利差预期回落与增长风险，是否对美元产生同向影响？',
    question: '从降息准备走向实际降息，需要哪些进一步条件？',
    source: statement('20240501'), sourceLabel: '美联储：QT减速安排',
    extraSources: [{ href: 'https://www.federalreserve.gov/newsevents/speech/powell20240823a.htm', label: '鲍威尔：2024-08-23 讲话' }],
  },
]
