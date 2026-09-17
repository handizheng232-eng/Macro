import {
  Archive,
  BookOpenText,
  CalendarRange,
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
import { useState } from 'react'

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

function EmptyState({ children }: { children: string }) {
  return (
    <div className="empty-state">
      <CircleDot size={16} aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}

function MacroFramework() {
  const regions = [
    {
      code: 'US · ECONOMY',
      title: '美国经济',
      description: '跟踪增长、就业、实际通胀、消费以及货币与财政政策。',
      dimensions: ['增长', '就业', '实际通胀', '政策'],
    },
    {
      code: 'CN · ECONOMY',
      title: '中国经济',
      description: '跟踪内需、工业与出口、房地产、信用和政策脉冲。',
      dimensions: ['内需', '生产', '房地产', '信用政策'],
    },
  ]

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">MACRO FRAMEWORK</p>
          <h1>宏观框架</h1>
          <p>先判断经济状态，再观察以美国为核心的全球金融条件。</p>
        </div>
        <div className="as-of"><span>框架版本</span><strong>V0.1</strong></div>
      </div>

      <div className="framework-layout">
        <div className="economy-grid">
          {regions.map((region, index) => (
            <section className="framework-card" key={region.title}>
              <div className="framework-number">0{index + 1}</div>
              <div className="framework-copy">
                <span>{region.code}</span>
                <h2>{region.title}</h2>
                <p>{region.description}</p>
                <div className="dimension-list">
                  {region.dimensions.map((item) => <span key={item}>{item}<i>待接入</i></span>)}
                </div>
              </div>
            </section>
          ))}
        </div>

        <section className="financial-conditions" aria-labelledby="financial-title">
          <div className="conditions-intro">
            <span>03 · GLOBAL FINANCIAL CONDITIONS</span>
            <h2 id="financial-title">全球金融条件</h2>
            <p>以美国定价变量为主轴，其他经济体作为补充。</p>
          </div>
          <div className="condition-pillars">
            {[
              ['美债利率', '名义利率 · 实际利率 · 收益率曲线'],
              ['通胀', '实际通胀 · 通胀预期 · 盈亏平衡通胀率'],
              ['美元', '美元指数 · 人民币 · 主要货币政策差'],
            ].map(([title, detail], index) => (
              <article key={title}>
                <span>0{index + 1}</span>
                <h3>{title}</h3>
                <p>{detail}</p>
                <div className="data-placeholder">等待数据源接入</div>
              </article>
            ))}
          </div>
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

function HistoryReview() {
  const steps = [
    ['01', '事前背景', '还原事件前的增长、通胀、政策与市场预期。'],
    ['02', '当时信息集', '仅使用截至所选日期已经发布的数据与研报。'],
    ['03', '事件发生', '记录数据公布、政策决定或突发事件。'],
    ['04', '即时反应', '观察当日美债、美元、权益与商品反应。'],
    ['05', '后续演化', '追踪事件后1周、1个月与3个月的路径。'],
    ['06', '复盘结论', '判断错误来自方向、时点、幅度还是资产表达。'],
  ]

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">HISTORICAL REPLAY</p>
          <h1>日期与事件复盘</h1>
          <p>以同一条时间轴还原当时信息、事件冲击与后续演化。</p>
        </div>
      </div>

      <section className="replay-query" aria-label="复盘入口">
        <div className="query-field">
          <label htmlFor="replay-date">选择日期</label>
          <div><CalendarRange size={16} /><input id="replay-date" type="date" /></div>
        </div>
        <span className="query-separator">或</span>
        <div className="query-field event-query">
          <label htmlFor="event-search">搜索事件</label>
          <div><Search size={16} /><input id="event-search" type="search" placeholder="例如：CPI、FOMC、财政政策" /></div>
        </div>
        <button type="button">开始复盘</button>
      </section>

      <section className="replay-timeline" aria-label="复盘时间轴">
        <div className="timeline-intro">
          <span>REPLAY STRUCTURE</span>
          <h2>统一复盘路径</h2>
          <p>选择日期或事件后，六个环节使用同一信息截止点，避免引入未来信息。</p>
        </div>
        <div className="timeline-steps">
          {steps.map(([number, title, description]) => (
            <article key={number}>
              <span>{number}</span>
              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
              <small>等待选择入口</small>
            </article>
          ))}
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

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">DATA & METHODOLOGY</p>
          <h1>数据与方法</h1>
          <p>统一管理指标定义、原始研报和历史数据版本。</p>
        </div>
      </div>

      <div className="methods-grid">
        <section className="method-card terminology">
          <div className="method-card-head"><BookOpenText size={18} /><span>01</span></div>
          <h2>指标口径</h2>
          <p>记录指标单位、频率、季调方式、同比环比及转换方法。</p>
          <div className="method-placeholder">尚未建立指标字典</div>
        </section>

        <section className="method-card report-library">
          <div className="method-card-head"><FileText size={18} /><span>02</span></div>
          <h2>研报资料库</h2>
          <p>保留机构、作者、发布日期、主题标签、摘要和原文路径。</p>
          <div className="source-connectors">
            <span>知识星球<i>待接入</i></span>
            <span>Wind 研报与观点<i>待接入</i></span>
          </div>
        </section>

        <section className="method-card versioning">
          <div className="method-card-head"><Database size={18} /><span>03</span></div>
          <h2>数据版本与来源</h2>
          <p>历史复盘以当时可得版本为准，并保留修订链路。</p>
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
    const pageFromHash = window.location.hash.slice(1)
    return navItems.some((item) => item.id === pageFromHash) ? pageFromHash as PageId : 'today'
  })

  const navigateTo = (page: PageId) => {
    window.history.pushState(null, '', `#${page}`)
    setActivePage(page)
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
            <span><i />Wind 待接入</span>
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
          <MacroFramework />
        ) : activePage === 'themes' ? (
          <ThemeTracker />
        ) : activePage === 'history' ? (
          <HistoryReview />
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
