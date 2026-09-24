import {
  Archive,
  ArrowLeft,
  BookOpenText,
  ChevronRight,
  CircleDot,
  Database,
  FileText,
  Gauge,
  Library,
  LineChart,
  Plus,
  Search,
  Telescope,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  categoryFromFrameworkHash,
  frameworkSlug,
  US_MACRO_PAGES,
  type UsMacroCategory,
} from './usMacroConfig'
import { UsMacroDetail } from './usMacro'

type PageId = 'today' | 'framework' | 'themes' | 'history' | 'methods'

const navItems = [
  { id: 'today' as const, label: '今日总览', icon: Gauge },
  { id: 'framework' as const, label: '宏观框架', icon: LineChart },
  { id: 'themes' as const, label: '主题跟踪', icon: Telescope },
  { id: 'history' as const, label: '历史复盘', icon: Archive },
  { id: 'methods' as const, label: '数据与方法', icon: Database },
]

const marketRows = [
  ['美债利率', '—', '—', '待接入 Wind'],
  ['通胀定价', '—', '—', '待接入 Wind'],
  ['美元指数', '—', '—', '待接入 Wind'],
  ['人民币', '—', '—', '待接入 Wind'],
  ['权益与商品', '—', '—', '待接入 Wind'],
]

const macroRegimes = [
  {
    number: '01',
    period: '1971.08—1979.10',
    title: '布雷顿森林解体与大通胀',
    thesis: '美元失去黄金锚，通胀与政策可信度共同推动利率中枢上移。',
    boundary: '1971年8月关闭黄金窗口；终点取1979年10月6日美联储改变货币政策操作框架。',
    fed: '政策在增长与通胀之间反复，实际约束不足，直至操作框架发生根本转折。',
    treasury: '名义收益率随通胀和通胀预期抬升，期限风险补偿持续扩张。',
    dollar: '脱离黄金后经历制度性重估，并在美国通胀失控和政策可信度下降时承压。',
    question: '拆分油价冲击、财政扩张、工资—价格机制与货币政策失误各自的贡献。',
    source: 'https://www.federalreservehistory.org/essays/gold-convertibility-ends',
    sourceLabel: '美联储历史：关闭黄金窗口',
  },
  {
    number: '02',
    period: '1979.10—1985.09',
    title: '沃尔克冲击与强美元',
    thesis: '以衰退代价重建反通胀信誉，高实际利率催生美元超级周期。',
    boundary: '1979年10月6日转向储备数量控制；终点取1985年9月广场协议。',
    fed: '转向储备数量控制，以高利率重建反通胀信誉；1982年后操作方式回摆，但紧约束延续。',
    treasury: '短端和长端先冲顶，随后进入长期债券牛市的起点，曲线随衰退与复苏剧烈切换。',
    dollar: '高实际利率、美国增长恢复与财政—货币组合推动美元大幅升值。',
    question: '检验“高利率—强美元—外部失衡”链条，以及通胀预期何时真正被重新锚定。',
    source: 'https://www.federalreservehistory.org/essays/anti-inflation-measures',
    sourceLabel: '美联储历史：1979年反通胀措施',
  },
  {
    number: '03',
    period: '1985.09—1994.02',
    title: '广场协议、协同贬值与软着陆',
    thesis: '汇率政策协调取代单纯利差主导，通胀回落为利率长期下行创造条件。',
    boundary: '起点取1985年9月广场协议；终点取1994年2月美联储首次预防式收紧。',
    fed: '从沃尔克后期到格林斯潘早期，政策在低通胀基础上更重视增长和金融稳定。',
    treasury: '结构性债牛展开，1987年股灾与1990—1991年衰退带来阶段性快速下行。',
    dollar: '广场协议后政策协同促贬，卢浮宫协议后目标逐渐转为稳定主要汇率。',
    question: '区分政策协调、利差收敛、财政调整和日本资产泡沫在美元下行中的作用。',
    source: 'https://home.treasury.gov/system/files/136/archive-documents/occasionalpaper3.pdf',
    sourceLabel: '美国财政部：G7政策协调与广场协议',
  },
  {
    number: '04',
    period: '1994.02—2001.01',
    title: '预防式紧缩、强美元与大缓和',
    thesis: '低通胀信誉、生产率叙事与资本流入共同塑造强美元和低长端利率。',
    boundary: '起点取1994年2月美联储首次公开预防式收紧；终点取2001年1月紧急降息。',
    fed: '先发制人加息强化规则信誉；亚洲危机与LTCM期间采取保险式宽松，随后再度收紧。',
    treasury: '1994年债券熊市后重回下行，生产率改善和低通胀预期压低长期收益率。',
    dollar: '美国增长优势、资本流入和危机避险推动强美元，外部脆弱性向新兴市场传导。',
    question: '判断“新经济”中的真实生产率改善、估值泡沫与美联储保险式宽松如何相互强化。',
    source: 'https://www.federalreserve.gov/FOMC/19940204default.htm',
    sourceLabel: '美联储：1994年2月FOMC声明',
  },
  {
    number: '05',
    period: '2001.01—2007.08',
    title: '低利率、弱美元与全球信用扩张',
    thesis: '政策利率先降后升，但期限溢价和信用条件长期宽松，全球失衡不断累积。',
    boundary: '起点取2001年1月3日降息；终点取2007年8月美元融资市场压力显性化。',
    fed: '快速降息至低位，随后以“可控步伐”连续加息，但广义金融条件未同步收紧。',
    treasury: '长端对加息反应有限，期限溢价偏低，收益率曲线逐步走平乃至倒挂。',
    dollar: '双赤字、利差变化和全球储备再配置推动美元进入较长弱势阶段。',
    question: '复盘全球储蓄过剩、住房金融、证券化与套息交易如何绕开政策利率约束。',
    source: 'https://www.federalreserve.gov/boarddocs/press/general/2001/20010103',
    sourceLabel: '美联储：2001年1月3日FOMC声明',
  },
  {
    number: '06',
    period: '2007.08—2013.05',
    title: '全球金融危机、零利率与QE',
    thesis: '美元融资体系失灵后，政策从利率工具扩展到流动性、资产负债表与前瞻指引。',
    boundary: '起点取2007年8月融资压力与贴现率行动；终点取2013年5月首次公开讨论缩减购债。',
    fed: '从紧急流动性工具、零利率转向多轮资产购买和前瞻指引，政策传导机制被重构。',
    treasury: '安全需求和QE压低国债收益率，无风险利率与信用利差在危机期剧烈分化。',
    dollar: '危机阶段因全球美元荒走强，宽松和风险修复阶段转弱，呈现典型“美元微笑”。',
    question: '沿美元融资链、银行资产负债表和抵押品机制复盘危机，而非只看联邦基金利率。',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20070817a.htm',
    sourceLabel: '美联储：2007年8月贴现率行动',
  },
  {
    number: '07',
    period: '2013.05—2019.07',
    title: '缩减恐慌、政策正常化与美元再定价',
    thesis: '退出非常规宽松的预期先于实际行动，期限溢价与全球美元负债重新定价。',
    boundary: '起点取2013年5月缩减购债沟通；终点取2019年7月十年来首次降息。',
    fed: '先缩减购债，2015年启动加息，2017年启动缩表；2018年末后转向耐心。',
    treasury: '期限溢价先跳升，随后受低中性利率压制；短端随加息上行并推动曲线趋平、倒挂。',
    dollar: '美国政策分化与增长差支撑美元，强美元对新兴市场美元负债形成外溢冲击。',
    question: '区分政策利率、缩表、期限溢价与海外增长差对美元和长端收益率的边际贡献。',
    source: 'https://www.federalreserve.gov/monetarypolicy/timeline-balance-sheet-policies.htm',
    sourceLabel: '美联储：资产负债表政策时间线',
  },
  {
    number: '08',
    period: '2019.07—2022.03',
    title: '预防式降息、疫情冲击与政策合流',
    thesis: '从保险式降息转入疫情应急，货币、财政与美元流动性工具形成罕见合力。',
    boundary: '起点取2019年7月31日降息；终点取2022年3月首次加息并准备缩表。',
    fed: '2019年保险式降息；2020年迅速回到零利率、大规模购债和流动性工具。',
    treasury: '短端锚定零附近，长端先因避险下探，随后随再通胀和财政扩张上行。',
    dollar: '疫情美元荒带来急升，全球流动性修复和风险偏好回升随后压低美元。',
    question: '识别货币—财政合流对需求的拉动，并区分供给约束、基数效应和持续性通胀。',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20190731a.htm',
    sourceLabel: '美联储：2019年7月FOMC声明',
  },
  {
    number: '09',
    period: '2022.03—2024.09',
    title: '通胀反击、QT与利率体系重估',
    thesis: '价格稳定重新压倒增长目标，政策利率、实际利率和期限溢价共同上修。',
    boundary: '起点取2022年3月16日首次加息；终点取2024年9月首次降息。',
    fed: '快速连续加息并缩表，从“暂时性”判断转为优先恢复价格稳定。',
    treasury: '短端急升、曲线深度倒挂，长端在更高通胀风险和期限溢价下重新定价。',
    dollar: '激进加息和避险需求推动强美元，随后随增长差和降息预期反复。',
    question: '拆分供给冲击、需求过热、财政脉冲和政策迟滞，并检验曲线倒挂的信号是否失真。',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20220316a.htm',
    sourceLabel: '美联储：2022年3月FOMC声明',
  },
  {
    number: '10',
    period: '2024.09—至今',
    title: '降息起步后的双向政策时代',
    thesis: '政策由单向抗通胀转为双向风险管理，短端反复而长端更受财政与期限溢价约束。',
    boundary: '起点取2024年9月18日首次降息；本期仍在演化，终点暂不设定。',
    fed: '先因风险平衡改善而降息，随后在通胀韧性与就业风险之间转入双向调整。',
    treasury: '短端围绕政策路径反复，长端更多受财政供给、期限溢价和通胀可信度约束。',
    dollar: '增长差、利差和避险需求交替主导，单边美元周期特征减弱。',
    question: '重点检验降息是否仍能带动长端下行，以及财政约束、中性利率和政策信誉的权重。',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm',
    sourceLabel: '美联储：2024年9月FOMC声明',
  },
]

const recentSubperiods = [
  {
    number: '10.1',
    period: '2024.09—2024.12',
    title: '前置式降息',
    status: '待复盘',
    thesis: '政策由单向抗通胀转向兼顾就业风险，三次会议累计降息100个基点，但缩表仍继续。',
    fed: '9月以50个基点启动降息，11月和12月各降25个基点，年底目标区间降至4.25%—4.50%。',
    treasury: '工作假说：短端随政策利率回落，长端对增长、财政供给和期限溢价的反应可能更强。',
    dollar: '工作假说：降息压低利差支撑，但美国相对增长和避险需求限制美元单边走弱。',
    question: '为什么降息启动后，长端利率和美元没有必然同步下行？',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20241218a.htm',
    sourceLabel: '美联储：2024年12月FOMC声明',
  },
  {
    number: '10.2',
    period: '2025.01—2025.08',
    title: '关税迷雾下的暂停',
    status: '待复盘',
    thesis: '通胀黏性、政策不确定性与就业韧性促使美联储连续维持利率，交易重心转向滞胀风险与期限溢价。',
    fed: '1月起维持4.25%—4.50%；到7月仍未降息，但已有两名委员主张降息，显示就业风险权重上升。',
    treasury: '工作假说：短端受政策暂停约束，长端更多交易财政供给、期限溢价与名义增长预期。',
    dollar: '工作假说：美元从降息预期交易转为增长差、实际利差和风险偏好的复合定价。',
    question: '利率暂停主要来自需求韧性还是供给型通胀风险，曲线应如何区分“更久更高”和滞胀定价？',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20250730a.htm',
    sourceLabel: '美联储：2025年7月FOMC声明',
  },
  {
    number: '10.3',
    period: '2025.09—2025.12',
    title: '再降息与QT收官',
    status: '待复盘',
    thesis: '就业风险推动连续三次降息，同时QT结束、准备金管理购买启动，价格型宽松与流动性操作开始分轨。',
    fed: '9月、10月和12月连续降息至3.50%—3.75%；12月结束QT，并按需购买短期国债以维持充裕准备金。',
    treasury: '工作假说：短端重定价较直接，长端仍取决于降息能否压低名义增长与财政风险补偿。',
    dollar: '工作假说：利差收窄形成下行压力，但增长相对优势可能继续提供缓冲。',
    question: '如何区分降息、QT结束和准备金管理购买对曲线、美元与风险资产的不同传导？',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20251210a.htm',
    sourceLabel: '美联储：2025年12月FOMC声明',
  },
  {
    number: '10.4',
    period: '2026.01—2026.08',
    title: '鹰派换届与反转酝酿',
    status: '待复盘',
    thesis: '增长韧性与通胀压力使政策讨论从是否续降转向是否重启加息，短端重新计入紧缩风险。',
    fed: '年初维持3.50%—3.75%；7月会议出现三张加息反对票，政策内部重心明显转向通胀风险。',
    treasury: '工作假说：曲线对下一步方向产生分歧，长端对中性利率和财政约束更敏感。',
    dollar: '工作假说：美元更多反映美国相对增长、真实利差与全球避险需求的拉扯。',
    question: '转鹰是数据驱动的暂时调整，还是美联储反应函数与中性利率判断已经改变？',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm',
    sourceLabel: '美联储：2026年7月FOMC声明',
  },
  {
    number: '10.5',
    period: '2026.09—至今',
    title: '重启加息：政策反转',
    status: '进行中 · 暂定',
    thesis: '2026年9月FOMC一致同意加息25个基点，正式逆转此前的降息方向；本段终点仍未形成。',
    fed: '目标区间上调至3.75%—4.00%；开放期尚未形成稳定终点，后续边界必须随政策与数据更新。',
    treasury: '待验证：短端重新计价加息概率，长端取决于通胀信誉改善能否抵消期限溢价上升。',
    dollar: '待验证：利差支撑与政策可信度可能推升美元，但增长代价会构成反向约束。',
    question: '这是一次短暂纠偏，还是更高通胀与更高中性利率制度的确认？',
    source: 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm',
    sourceLabel: '美联储：2026年9月FOMC声明',
  },
]

function EmptyState({ children }: { children: string }) {
  return (
    <div className="empty-state">
      <CircleDot size={16} aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}

function MacroFramework({ onOpenUsCategory }: { onOpenUsCategory: (category: UsMacroCategory) => void }) {
  const coverageLabel = {
    deep: '深度数据页',
    partial: '已接入部分序列',
    framework: '指标框架已建',
  } as const

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">MACRO FRAMEWORK</p>
          <h1>宏观框架</h1>
          <p>先沿数据生产—加工—定价链识别信息，再按九个模块判断美国经济与政策传导。</p>
        </div>
        <div className="as-of"><span>框架版本</span><strong>V0.2 · PPT 0829</strong></div>
      </div>

      <section className="framework-methodology" aria-label="美国宏观数据三层读法">
        {[
          ['01', '生产端', '谁统计、调查谁、覆盖多广', '机构 · 样本 · 频率 · 滞后'],
          ['02', '加工端', '数据经过哪些处理，初值多可靠', '季调 · SAAR · 修正 · 平减'],
          ['03', '定价端', '市场为何在乎，以及在乎到什么程度', '预期差 · 主题权重 · 可交易性'],
        ].map(([index, title, question, detail]) => (
          <article key={title}>
            <span>{index}</span>
            <div><h2>{title}</h2><p>{question}</p><small>{detail}</small></div>
          </article>
        ))}
      </section>

      <section className="us-framework-map" aria-labelledby="us-framework-title">
        <header>
          <div>
            <span>US ECONOMY · NINE-MODULE MAP</span>
            <h2 id="us-framework-title">美国宏观九模块</h2>
            <p>按培训材料第1—9章展开。就业与通胀保留深度页；现有增长、政策数据拆入对应模块；尚无可核验序列的页面只展示指标字典。</p>
          </div>
          <strong>9 个研究模块</strong>
        </header>
        <div className="macro-module-grid">
          {US_MACRO_PAGES.map((page) => (
            <button
              aria-label={`打开美国${page.label}模块`}
              key={page.category}
              type="button"
              onClick={() => onOpenUsCategory(page.category)}
            >
              <span className="module-chapter">CH.{page.chapter}</span>
              <div>
                <h3>{page.label}</h3>
                <p>{page.detail}</p>
              </div>
              <footer>
                <small className={`coverage-${page.coverage}`}>{coverageLabel[page.coverage]}</small>
                <ChevronRight size={15} aria-hidden="true" />
              </footer>
            </button>
          ))}
        </div>
      </section>

      <div className="framework-support-grid">
        <section className="framework-support-card">
          <span>CN · ECONOMY</span>
          <h2>中国经济</h2>
          <p>继续保留内需、生产与出口、房地产、信用和政策脉冲一级框架；本轮不使用美国培训材料替代中国口径。</p>
          <div className="support-tags">{['内需', '生产与出口', '房地产', '信用政策'].map((item) => <span key={item}>{item}<i>待接入</i></span>)}</div>
        </section>
        <section className="framework-support-card dark" aria-labelledby="financial-title">
          <span>GLOBAL · PRICING LAYER</span>
          <h2 id="financial-title">全球金融条件</h2>
          <p>把政策落点放在实体真正感受到的价格变量，而不是另建与美国模块重复的基本面页。</p>
          <div className="support-tags">{['美债曲线与实际利率', '美元与主要汇率', '信用利差与股权', 'FCI与流动性'].map((item) => <span key={item}>{item}<i>待补充</i></span>)}</div>
        </section>
      </div>
    </>
  )
}

function ThemeTracker() {
  const [isCreating, setIsCreating] = useState(false)
  const [draftTitle, setDraftTitle] = useState('')
  const [themes, setThemes] = useState<string[]>([])

  const saveTheme = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const title = draftTitle.trim()
    if (!title) return
    setThemes((current) => [...current, title])
    setDraftTitle('')
    setIsCreating(false)
  }

  return (
    <>
      <div className="page-heading theme-heading">
        <div>
          <p className="eyebrow">RESEARCH THEMES</p>
          <h1>主题跟踪</h1>
          <p>只在出现明确研究问题时建立主题，不预设复杂分类。</p>
        </div>
        <button className="primary-action" type="button" onClick={() => setIsCreating(true)}>
          <Plus size={16} />新建主题
        </button>
      </div>

      <section className="theme-workspace" aria-label="研究主题列表">
        {isCreating && (
          <form className="theme-form" onSubmit={saveTheme}>
            <label htmlFor="theme-title">主题名称</label>
            <div>
              <input
                id="theme-title"
                value={draftTitle}
                onChange={(event) => setDraftTitle(event.target.value)}
                placeholder="输入一个明确的研究问题"
                autoFocus
              />
              <button type="submit">保存主题</button>
              <button className="cancel-button" type="button" onClick={() => setIsCreating(false)}>取消</button>
            </div>
          </form>
        )}

        {themes.length === 0 ? (
          <div className="large-empty-state">
            <Telescope size={28} strokeWidth={1.5} />
            <h2>尚未建立研究主题</h2>
            <p>当出现需要持续验证的问题时再添加；首版保持清单简洁。</p>
          </div>
        ) : (
          <div className="theme-list">
            {themes.map((theme, index) => (
              <article key={`${theme}-${index}`}>
                <span className="theme-index">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <span className="theme-status">研究中</span>
                  <h2>{theme}</h2>
                  <p>尚未添加结论与证据。</p>
                </div>
                <ChevronRight size={18} />
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  )
}

function RecentHistoryReview({ onBack }: { onBack: () => void }) {
  const regime = macroRegimes[9]

  return (
    <>
      <div className="page-heading history-detail-heading">
        <div>
          <button className="history-back" type="button" onClick={onBack}>
            <ArrowLeft size={15} />返回宏观分期总览
          </button>
          <p className="eyebrow">EASING-TO-TIGHTENING · SECOND-ORDER REPLAY</p>
          <h1>{regime.title}</h1>
          <p>{regime.period} · {regime.thesis}</p>
        </div>
        <div className="as-of"><span>阶段状态</span><strong>进行中 · 边界暂定</strong></div>
      </div>

      <section className="recent-stage-overview" aria-label="当前阶段总览">
        <div className="recent-stage-boundary">
          <span>一级边界</span>
          <p>{regime.boundary}</p>
          <a href={regime.source} target="_blank" rel="noreferrer">{regime.sourceLabel} ↗</a>
        </div>
        <div className="recent-stage-axes">
          {[
            ['FED', '美联储', regime.fed],
            ['UST', '美债收益率', regime.treasury],
            ['USD', '美元', regime.dollar],
            ['FOCUS', '一级复盘主线', regime.question],
          ].map(([code, title, description]) => (
            <section key={code}>
              <span>{code}</span>
              <h2>{title}</h2>
              <p>{description}</p>
            </section>
          ))}
        </div>
      </section>

      <section className="subperiod-review" aria-label="当前阶段细分时段">
        <header>
          <div>
            <span>SECOND-ORDER PERIODS</span>
            <h2>细分时段复盘</h2>
            <p>先按政策方向与传导机制拆成五段。美债和美元部分是待检验的工作假说，不作为既定结论。</p>
          </div>
          <strong>5 个二级时段</strong>
        </header>

        <div className="subperiod-list">
          {recentSubperiods.map((subperiod) => (
            <article key={subperiod.number}>
              <div className="subperiod-index">
                <small>{subperiod.period}</small>
              </div>
              <div className="subperiod-body">
                <div className="subperiod-title">
                  <div>
                    <h3>{subperiod.title}</h3>
                    <p>{subperiod.thesis}</p>
                  </div>
                  <small className={subperiod.status.includes('进行中') ? 'provisional' : ''}>{subperiod.status}</small>
                </div>
                <div className="subperiod-axes">
                  <div><span>FED</span><strong>美联储</strong><p>{subperiod.fed}</p></div>
                  <div><span>UST</span><strong>美债收益率</strong><p>{subperiod.treasury}</p></div>
                  <div><span>USD</span><strong>美元</strong><p>{subperiod.dollar}</p></div>
                </div>
                <div className="subperiod-question">
                  <div><span>复盘问题</span><p>{subperiod.question}</p></div>
                  <a href={subperiod.source} target="_blank" rel="noreferrer">{subperiod.sourceLabel} ↗</a>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  )
}

function HistoryReview({ onOpenRecent }: { onOpenRecent: () => void }) {
  const [selectedRegime, setSelectedRegime] = useState(0)
  const activeRegime = macroRegimes[selectedRegime]

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">HISTORICAL REPLAY</p>
          <h1>近50年宏观分期</h1>
          <p>以美元、美债收益率和美联储政策的共同拐点划分一级时期。</p>
        </div>
      </div>

      <section className="regime-map" aria-labelledby="regime-map-title">
        <header className="regime-map-head">
          <div>
            <span>REGIME MAP · 1971—PRESENT</span>
            <h2 id="regime-map-title">一级时期总览</h2>
            <p>以美元制度、美国利率结构与美联储政策反应函数的共同拐点划分；它是可修订的研究假说，不等同于NBER经济周期。</p>
          </div>
          <strong>覆盖 1971 年至今</strong>
        </header>

        <div className="regime-workbench">
          <div className="regime-list" role="list" aria-label="宏观时期列表">
            {macroRegimes.map((regime, index) => (
              <button
                aria-label={`宏观阶段：${regime.title}`}
                aria-pressed={selectedRegime === index}
                className={selectedRegime === index ? 'active' : ''}
                key={regime.number}
                onClick={() => setSelectedRegime(index)}
                type="button"
              >
                <div>
                  <small>{regime.period}</small>
                  <b>{regime.title}</b>
                </div>
                <ChevronRight size={15} aria-hidden="true" />
              </button>
            ))}
          </div>

          <article className="regime-detail" aria-live="polite">
            <header>
              <div>
                <span>{activeRegime.period}</span>
                <h2>{activeRegime.title}</h2>
                <p>{activeRegime.thesis}</p>
              </div>
              <small>{activeRegime.number === '10' ? '已拆分 5 个时段' : '一级框架暂保留'}</small>
            </header>

            <div className="regime-boundary">
              <span>划分边界</span>
              <p>{activeRegime.boundary}</p>
              <a href={activeRegime.source} target="_blank" rel="noreferrer">{activeRegime.sourceLabel} ↗</a>
            </div>

            <div className="regime-axes">
              {[
                ['FED', '美联储', activeRegime.fed],
                ['UST', '美债收益率', activeRegime.treasury],
                ['USD', '美元', activeRegime.dollar],
                ['FOCUS', '复盘主线', activeRegime.question],
              ].map(([code, title, description]) => (
                <section key={code}>
                  <span>{code}</span>
                  <h3>{title}</h3>
                  <p>{description}</p>
                </section>
              ))}
            </div>
            {activeRegime.number === '10' && (
              <button className="regime-detail-action" type="button" onClick={onOpenRecent}>
                进入当前阶段细分复盘 <ChevronRight size={16} />
              </button>
            )}
          </article>
        </div>
      </section>
    </>
  )
}

function DataMethods() {
  const metadata = [
    ['观测期', '数据描述的月份、季度或日期'],
    ['发布日期', '市场首次获得该信息的时间'],
    ['数据版本', '初值、修订值或终值'],
    ['抓取时间', '系统取得该版本的时间'],
  ]
  const passportFields = [
    ['发布机构', '方法论文化与修订习惯'],
    ['调查对象与样本', '覆盖面、代表性与噪音'],
    ['频率与滞后', '信息新鲜度和链条位置'],
    ['季调方式', '环比是否可比'],
    ['修正规则', '初值可信度与历史版本'],
    ['一致预期', '预期差能否直接衡量'],
    ['市场重要性', '五因子分数与主题乘数'],
    ['单位与转换', '水平、同比、环比、SAAR、名义或实际'],
  ]
  const processing = [
    ['季节调整 SA', '剔除固定日历形态', '季调因子漂移与残余季节性'],
    ['季环比折年 SAAR', '把月/季环比折算为年率', '同时放大短期噪音'],
    ['多轮修正', '用更完整样本逼近终值', '初值和终值可能讲出不同故事'],
    ['通胀调整', '名义值经平减得到实际量', '平减指数选错会翻转结论'],
  ]
  const importanceFactors = [
    ['时效性 / 先发权', '同主题链条中是否最早发布'],
    ['政策关联度', '离双重使命与反应函数有多近'],
    ['覆盖面与代表性', '样本能否代表总量经济'],
    ['信噪比与修正', '初值可靠度和修正风险'],
    ['可交易性', '是否有衍生品或可推算关键数据'],
    ['预期差与当期主题', '结构分还要乘以动态主题权重'],
  ]

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">DATA & METHODOLOGY</p>
          <h1>数据与方法</h1>
          <p>把培训材料中的数据身份证、加工规则与定价框架落实为可审计的指标字典。</p>
        </div>
        <div className="as-of"><span>研究依据</span><strong>PPT · 231页</strong></div>
      </div>

      <div className="methods-grid">
        <section className="method-card terminology">
          <div className="method-card-head"><BookOpenText size={18} /><span>01 · PASSPORT</span></div>
          <h2>指标口径</h2>
          <p>每条序列先回答发布机构、调查对象、频率滞后、季调、修正、一致预期与市场重要性，再进入图表。</p>
          <div className="passport-grid" aria-label="数据身份证字段">
            {passportFields.map(([name, description]) => (
              <div key={name}><strong>{name}</strong><span>{description}</span></div>
            ))}
          </div>
          <div className="indicator-index-wrap">
            <table className="indicator-index">
              <thead><tr><th>模块</th><th>核心指标组</th><th>覆盖状态</th></tr></thead>
              <tbody>
                {US_MACRO_PAGES.map((page) => (
                  <tr aria-label={`指标字典：${page.label}`} key={page.category}>
                    <th scope="row"><span>CH.{page.chapter}</span>{page.label}</th>
                    <td>{page.indicators.map((item) => item.name).join(' · ')}</td>
                    <td>{page.coverage === 'deep' ? '深度页' : page.coverage === 'partial' ? '部分序列' : '框架待取数'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="method-card processing-card">
          <div className="method-card-head"><Database size={18} /><span>02 · PROCESSING</span></div>
          <h2>数据加工四件套</h2>
          <p>网页必须显式标出转换，不能把同比、环比、折年率、名义量和实际量混为一谈。</p>
          <div className="method-list">
            {processing.map(([name, purpose, trap]) => (
              <article key={name}><strong>{name}</strong><span>{purpose}</span><small>{trap}</small></article>
            ))}
          </div>
        </section>

        <section className="method-card importance-card">
          <div className="method-card-head"><Gauge size={18} /><span>03 · PRICING</span></div>
          <h2>市场重要性五因子</h2>
          <p>固定结构分之外，还要乘以当期宏观主题；市场交易的是相对预期的信息增量，而不是数据水平本身。</p>
          <div className="method-list compact">
            {importanceFactors.map(([name, description]) => (
              <article key={name}><strong>{name}</strong><span>{description}</span></article>
            ))}
          </div>
        </section>

        <section className="method-card report-library">
          <div className="method-card-head"><FileText size={18} /><span>04 · LIBRARY</span></div>
          <h2>研报资料库</h2>
          <p>保留机构、作者、发布日期、主题标签、摘要和原文路径；框架源文件登记为《美国宏观数据培训【0829定稿】》。</p>
          <div className="source-connectors">
            <span>培训材料<i>已纳入框架</i></span>
            <span>知识星球<i>待接入</i></span>
            <span>Wind 研报与观点<i>待接入</i></span>
          </div>
        </section>

        <section className="method-card versioning">
          <div className="method-card-head"><Database size={18} /><span>05 · VINTAGE</span></div>
          <h2>数据版本与来源</h2>
          <p>历史复盘以当时可得版本为准，并保留修订链路；各卡片使用自己的最新观测期，不制造共同“截至日”。</p>
          <div className="metadata-grid">
            {metadata.map(([name, description]) => (
              <div key={name}><strong>{name}</strong><span>{description}</span></div>
            ))}
          </div>
        </section>
      </div>
    </>
  )
}

function App() {
  const [activePage, setActivePage] = useState<PageId>(() => {
    const pageFromHash = window.location.hash.slice(1).split('/')[0]
    return navItems.some((item) => item.id === pageFromHash) ? pageFromHash as PageId : 'today'
  })
  const [historyDetail, setHistoryDetail] = useState(() => window.location.hash === '#history/easing-to-tightening')
  const [frameworkDetail, setFrameworkDetail] = useState<UsMacroCategory | null>(() => categoryFromFrameworkHash(window.location.hash))

  useEffect(() => {
    const syncFromHash = () => {
      const pageFromHash = window.location.hash.slice(1).split('/')[0]
      const nextPage = navItems.some((item) => item.id === pageFromHash) ? pageFromHash as PageId : 'today'
      setActivePage(nextPage)
      setHistoryDetail(window.location.hash === '#history/easing-to-tightening')
      setFrameworkDetail(categoryFromFrameworkHash(window.location.hash))
    }

    window.addEventListener('popstate', syncFromHash)
    window.addEventListener('hashchange', syncFromHash)
    return () => {
      window.removeEventListener('popstate', syncFromHash)
      window.removeEventListener('hashchange', syncFromHash)
    }
  }, [])

  const navigateTo = (page: PageId) => {
    window.history.pushState(null, '', `#${page}`)
    setActivePage(page)
    setHistoryDetail(false)
    setFrameworkDetail(null)
  }

  const openUsMacro = (category: UsMacroCategory) => {
    window.history.pushState(null, '', `#framework/${frameworkSlug(category)}`)
    setActivePage('framework')
    setFrameworkDetail(category)
  }

  const closeUsMacro = () => {
    window.history.pushState(null, '', '#framework')
    setFrameworkDetail(null)
  }

  const openRecentHistory = () => {
    window.history.pushState(null, '', '#history/easing-to-tightening')
    setActivePage('history')
    setHistoryDetail(true)
  }

  const closeRecentHistory = () => {
    window.history.pushState(null, '', '#history')
    setHistoryDetail(false)
  }

  return (
    <div className="app-shell">
      <header className="masthead">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">M</div>
          <div>
            <strong>宏观研究工作台</strong>
            <span>研究 · 跟踪 · 复盘</span>
          </div>
        </div>
        <div className="masthead-actions">
          <button className="search-button" type="button" aria-label="搜索">
            <Search size={17} />
            <span>搜索研究内容</span>
            <kbd>⌘ K</kbd>
          </button>
          <div className="source-state" aria-label="数据源状态">
            <span className="connected"><i />OpenBB 已接入</span>
            <span className="connected"><i />Wind 已接入</span>
            <span><i />知识星球待接入</span>
          </div>
        </div>
      </header>

      <aside className="sidebar">
        <nav aria-label="主导航">
          <p className="nav-eyebrow">工作区</p>
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              className={activePage === id ? 'nav-item active' : 'nav-item'}
              key={label}
              type="button"
              onClick={() => navigateTo(id)}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p>数据原则</p>
          <span>事实、观点与内部判断分层呈现；无数据时不生成结论。</span>
        </div>
      </aside>

      <main className="workspace">
        {activePage === 'today' ? (
          <>
        <div className="page-heading">
          <div>
            <p className="eyebrow">DAILY MONITOR</p>
            <h1>今日总览</h1>
            <p>从宏观事实、市场定价与卖方观点三个层面形成每日判断。</p>
          </div>
          <div className="as-of">
            <span>最后更新</span>
            <strong>尚无数据</strong>
          </div>
        </div>

        <section className="daily-thesis" aria-labelledby="today-thesis">
          <div className="section-label">
            <span>01</span>
            <h2 id="today-thesis">今日结论</h2>
          </div>
          <div className="thesis-copy">
            <p>尚未生成今日研究结论</p>
            <span>接入宏观数据、市场行情与研报后，由研究员确认并发布。</span>
          </div>
          <button className="quiet-action" type="button">进入编辑 <ChevronRight size={16} /></button>
        </section>

        <div className="monitor-grid">
          <section className="panel facts-panel" aria-labelledby="macro-facts">
            <div className="panel-head">
              <div>
                <span>02 · FACTS</span>
                <h2 id="macro-facts">宏观事实</h2>
              </div>
              <small>客观数据层</small>
            </div>
            <div className="fact-columns">
              {['美国数据', '中国数据', '政策与事件'].map((title) => (
                <article key={title}>
                  <h3>{title}</h3>
                  <EmptyState>等待数据接入</EmptyState>
                </article>
              ))}
            </div>
          </section>

          <section className="panel pricing-panel" aria-labelledby="market-pricing">
            <div className="panel-head">
              <div>
                <span>03 · PRICING</span>
                <h2 id="market-pricing">市场定价</h2>
              </div>
              <small>价格验证层</small>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>维度</th><th>水平</th><th>变化</th><th>状态</th></tr>
                </thead>
                <tbody>
                  {marketRows.map((row) => (
                    <tr key={row[0]}>{row.map((cell, index) => <td key={`${row[0]}-${index}`}>{cell}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel views-panel" aria-labelledby="sell-side-views">
            <div className="panel-head">
              <div>
                <span>04 · CONSENSUS</span>
                <h2 id="sell-side-views">卖方观点雷达</h2>
              </div>
              <small>观点层</small>
            </div>
            <div className="views-layout">
              <div className="view-axis">
                <div><span>共识方向</span><strong>待梳理</strong></div>
                <div><span>主要分歧</span><strong>待梳理</strong></div>
                <div><span>观点变化</span><strong>待梳理</strong></div>
              </div>
              <EmptyState>等待 Wind 卖方观点与知识星球研报接入</EmptyState>
            </div>
          </section>

          <section className="panel reports-panel" aria-labelledby="key-reports">
            <div className="panel-head">
              <div>
                <span>05 · RESEARCH</span>
                <h2 id="key-reports">重点研报</h2>
              </div>
              <button type="button" className="text-link">查看资料库 <ChevronRight size={15} /></button>
            </div>
            <div className="report-empty">
              <div className="report-icon"><FileText size={22} /></div>
              <div>
                <h3>今日暂无研报</h3>
                <p>接入后展示机构、标题、核心新增信息、影响主题与原文路径。</p>
              </div>
            </div>
          </section>
        </div>

        <footer className="workspace-footer">
          <div><BookOpenText size={15} /> 所有结论需保留来源与时间戳</div>
          <div><Library size={15} /> 原始资料进入研报资料库</div>
        </footer>
          </>
        ) : activePage === 'framework' ? (
          frameworkDetail ? <UsMacroDetail category={frameworkDetail} onBack={closeUsMacro} /> : <MacroFramework onOpenUsCategory={openUsMacro} />
        ) : activePage === 'themes' ? (
          <ThemeTracker />
        ) : activePage === 'history' ? (
          historyDetail ? <RecentHistoryReview onBack={closeRecentHistory} /> : <HistoryReview onOpenRecent={openRecentHistory} />
        ) : activePage === 'methods' ? (
          <DataMethods />
        ) : (
          <div className="page-heading">
            <div>
              <p className="eyebrow">WORKSPACE</p>
              <h1>{navItems.find((item) => item.id === activePage)?.label}</h1>
              <p>该模块将在下一步完成。</p>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
