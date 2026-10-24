import type { OverviewSubperiod } from './inflationOverview'

const statement = (date: string) => `https://www.federalreserve.gov/newsevents/pressreleases/monetary${date}a.htm`

// Research organization only: policy anchors do not certify market outcomes.
export const pandemicOverview = {
  period: '2019-07-31至2022-03-15',
  thesis: '分期方案 / 待复盘：从预防式降息与准备金管理，转入疫情应急、政策合流，再到Taper与加息准备。',
  boundary: '沿用既有一级边界：2019年7月31日降息开始，覆盖至2022年3月15日。2022年3月16日首次加息归入下一时期，不重复计入本期。',
  fed: '区分政策利率、准备金管理、QE、紧急信贷及美元流动性工具；Taper减慢净购债，不等于QT或当即加息。',
  treasury: '待检验问题：政策路径、市场流动性、通胀补偿与期限溢价，如何分别影响美债短端、长端和曲线？',
  dollar: '待检验问题：美元融资需求、避险、利差与相对复苏，如何在各段共同作用？尚未核验行情。',
  question: '研究主线：危机救助如何转向复苏支持，供需失衡与通胀风险又如何改变政策权衡？不预设政策或市场结果。',
  source: statement('20190731'),
  sourceLabel: '美联储：2019-07-31 降息声明',
}

export const pandemicSubperiods: OverviewSubperiod[] = [
  {
    number: '08.1', period: '2019-07-31至2020-02-29', title: '预防式降息与准备金管理', status: '待复盘',
    thesis: '阶段观察：维持扩张的利率调整，与缓解货币市场压力的操作安排并存；两者目的不同。',
    fed: '2019年7月31日降息至2.00%—2.25%，并宣布8月结束缩表；10月11日宣布国库券购买及回购安排，明确为技术措施、不改变政策立场，不直接等同于QE。',
    treasury: '待检验问题：增长担忧驱动的利率路径变化，如何与回购市场压力及准备金供给效应区分？',
    dollar: '待检验问题：降息与美元融资环境变化，是否经由不同渠道影响美元？',
    question: '预防式降息和准备金管理，分别针对经济风险还是政策执行问题？',
    source: statement('20190731'), sourceLabel: '2019-07-31 FOMC声明',
    extraSources: [{ href: statement('20191011'), label: '2019-10-11 政策实施安排' }],
  },
  {
    number: '08.2', period: '2020-03-01至2020-03-31', title: '疫情紧急冲击与市场功能修复', status: '待复盘',
    thesis: '阶段观察：疫情冲击下，利率、证券购买、信贷设施与美元流动性安排同时进入应急响应。',
    fed: '3月15日降至0—0.25%，宣布大规模国债和机构MBS购买及协调美元互换安排；3月23日改为按市场平稳运作所需规模购债，并扩展紧急信贷支持。购债与信贷、互换工具不能混为一谈。',
    treasury: '待检验问题：避险需求和现金需求，对国债收益率与市场流动性的影响是否出现背离？',
    dollar: '待检验问题：美元融资紧张与传统避险需求，如何分别识别？互换安排缓解的是哪类约束？',
    question: '降低政策利率为何不足以单独修复市场功能和信用传导？',
    source: statement('20200315'), sourceLabel: '2020-03-15 紧急FOMC声明',
    extraSources: [{ href: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323b.htm', label: '2020-03-23 购债与信贷支持' }],
  },
  {
    number: '08.3', period: '2020-04-01至2020-12-31', title: '财政货币合流与复苏支持', status: '待复盘',
    thesis: '阶段观察：救助与恢复信用传导并进，财政风险支持和央行贷款各有分工；政策框架也发生调整。',
    fed: '4月9日公布进一步信贷支持，包括财政部以CARES法案资金为部分设施提供资本或信用保护；宣布的额度不等于实际投放。8月27日鲍威尔阐释灵活平均通胀目标，并非机械补偿公式。',
    treasury: '待检验问题：财政支持、净发债、购债和复苏预期，对长端利率的影响如何拆分？',
    dollar: '待检验问题：美元流动性修复与全球复苏预期，是否改变前期融资溢价和避险需求？',
    question: '如何区别财政转移、财政信用保护与央行贷款，而不把政策合流简化为单一货币投放？',
    source: statement('20200409'), sourceLabel: '2020-04-09 信贷支持安排',
    extraSources: [{ href: 'https://www.federalreserve.gov/newsevents/speech/powell20200827a.htm', label: '鲍威尔：2020-08-27 政策框架' }],
  },
  {
    number: '08.4', period: '2021-01-01至2021-08-31', title: '再通胀与暂时性判断', status: '待复盘',
    thesis: '阶段观察：重启中的价格上涨、供需错配及通胀持续性，成为继续宽松的关键判断条件。',
    fed: '8月27日鲍威尔认为若干因素支持高通胀读数可能暂时性的判断，但强调持续核查数据；若持续高通胀成为严重担忧，FOMC将回应。他同时区分缩减购债与加息的条件。',
    treasury: '待检验问题：再通胀交易中，实际利率、通胀补偿和期限溢价各扮演什么角色？',
    dollar: '待检验问题：美国与海外复苏差异，如何与政策预期共同影响美元？',
    question: '当时哪些证据支持暂时性判断，哪些证据可能推翻它？不以事后结果替代当时信息集。',
    source: 'https://www.federalreserve.gov/newsevents/speech/powell20210827a.htm', sourceLabel: '鲍威尔：2021-08-27 经济展望',
  },
  {
    number: '08.5', period: '2021-09-01至2021-11-30', title: 'Taper预告与购债减速启动', status: '待复盘',
    thesis: '阶段观察：政策讨论从何时具备减购条件，转向实际降低每月净购买速度。',
    fed: '9月22日声明称若进展符合预期，可能很快适合放慢购债；11月3日决定当月开始减购，国债和机构MBS的月度净购买速度分别减少100亿和50亿美元，利率仍为0—0.25%。',
    treasury: '待检验问题：购债流量减速与未来加息预期，分别如何作用于曲线和期限溢价？',
    dollar: '待检验问题：减购沟通对美元的影响，是否主要经由利差预期而非当期利率？',
    question: '如何区分减慢扩表、停止净购债和真正缩表？不能把Taper启动当作QT启动。',
    source: statement('20211103'), sourceLabel: '2021-11-03 Taper声明',
    extraSources: [{ href: statement('20210922'), label: '2021-09-22 FOMC声明' }],
  },
  {
    number: '08.6', period: '2021-12-01至2022-03-15', title: '加速Taper与转鹰准备', status: '待复盘',
    thesis: '阶段观察：通胀与就业变化推动退出宽松提速；结束净购债和首次加息仍需分开定位。',
    fed: '12月15日宣布将国债和机构MBS月度净购买速度的减幅提高至200亿和100亿美元；2022年1月26日表示预计很快适合加息，净购债将于3月初结束。本段不包含3月16日首次加息，也不称已启动QT。',
    treasury: '待检验问题：短端对加息准备的反应，是否与长端对通胀、增长及未来缩表的反应不同？',
    dollar: '待检验问题：政策分化、相对增长及地缘风险，如何分别影响美元定价？',
    question: '从减购提速到加息准备，政策反应函数发生了什么变化，需要哪些当时证据验证？',
    source: statement('20211215'), sourceLabel: '2021-12-15 加速Taper声明',
    extraSources: [{ href: statement('20220126'), label: '2022-01-26 加息准备声明' }],
  },
]
