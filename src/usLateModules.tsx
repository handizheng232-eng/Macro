import { useMemo, useState } from 'react'
import { ArrowLeft, CheckCircle2, ChevronRight, Info } from 'lucide-react'
import lateModulesData from './data/usLateModulesData.json'
import type { UsMacroCategory } from './usMacroConfig'

type LateCategory = Extract<UsMacroCategory, 'housing' | 'investment' | 'pmi' | 'fiscal' | 'fed'>
type RangeKey = '3Y' | '5Y' | '10Y' | 'ALL'
type SourceMeta = { provider: string; institution: string; code: string; name: string; rawUnit: string; url: string; latestObservation: string }
type ChartSeries = { id: string; label: string; dates: string[]; values: number[]; color: string; unit: string; frequency: '日' | '周' | '月' | '季' | '年'; latestValue: number; latestObservation: string; source: SourceMeta; transformLabel?: string }
type ChartExplanation = { what: string; howToRead: string; caveat: string; pptSlide: string }
type ChartDefinition = { id: string; kind: 'line'; eyebrow: string; title: string; description: string; unit: string; defaultRange: RangeKey; reference?: number; series: ChartSeries[]; explanation: ChartExplanation }
type ModuleSection = { id: string; title: string; description: string; charts: ChartDefinition[] }
type ModuleData = {
  chapter: string; label: string; accent: string; slides: string; routeSlide: number; title: string; subtitle: string; core: string
  routeMap: Array<{ id: string; title: string; subtitle: string; nodes: Array<{ title: string; detail: string }> }>
  passports: Array<{ id: string; title: string; producer: string; frequency: string; coverage: string; revision: string; use: string; pitfall: string; pptSlide: string }>
  availability: Array<{ label: string; status: string; explanation: string }>
  sections: ModuleSection[]
  headline: Array<{ id: string; label: string; title: string; value: number; unit: string; observation: string; source: string }>
  researchBasis: string[]
}
type Dataset = {
  schemaVersion: number; generatedAt: string; source: string; frameworkSource: { file: string; slides: string }
  modules: Record<LateCategory, ModuleData>
  dataQuality: { verifiedSeries: number; missingPeriods: Record<string, string[]>; note: string }
}

const dataset = lateModulesData as Dataset
const RANGE_OPTIONS: Array<{ key: RangeKey; label: string; years: number | null }> = [
  { key: '3Y', label: '3年', years: 3 }, { key: '5Y', label: '5年', years: 5 },
  { key: '10Y', label: '10年', years: 10 }, { key: 'ALL', label: '全部', years: null },
]
const ACCENT_CLASS: Record<string, string> = { teal: 'late-teal', blue: 'late-blue', purple: 'late-purple', red: 'late-red', cyan: 'late-cyan' }

function formatValue(value: number) {
  const decimals = Math.abs(value) >= 100 ? 0 : Math.abs(value) >= 10 ? 1 : 2
  return new Intl.NumberFormat('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)
}
function formatDate(date: string) {
  if (date.length < 6) return date
  return date.length >= 8 ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}` : `${date.slice(0, 4)}-${date.slice(4, 6)}`
}
function dateToTimestamp(date: string) { return Date.UTC(Number(date.slice(0, 4)), Number(date.slice(4, 6) || '1') - 1, Number(date.slice(6, 8) || '1')) }
function timestampLabel(timestamp: number) { const date = new Date(timestamp); return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}` }
function chartValue(value: number, unit: string) { return `${formatValue(value)}${unit === '%' || unit.includes('%') ? '%' : unit ? ` ${unit}` : ''}` }
function cutoffFor(range: RangeKey, latest: number) { const years = RANGE_OPTIONS.find((item) => item.key === range)?.years; return years == null ? Number.NEGATIVE_INFINITY : latest - years * 365.25 * 86_400_000 }
function scrollToSection(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }

function ResearchChart({ chart }: { chart: ChartDefinition }) {
  const width = 920; const height = 350; const left = 64; const right = 24; const top = 18; const bottom = 42
  const [range, setRange] = useState<RangeKey>(chart.defaultRange)
  const [active, setActive] = useState<Record<string, boolean>>(() => Object.fromEntries(chart.series.map((item) => [item.id, true])))
  const [hoverTimestamp, setHoverTimestamp] = useState<number | null>(null)
  const latestTimestamp = Math.max(...chart.series.flatMap((item) => item.dates.map(dateToTimestamp)))
  const cutoff = cutoffFor(range, latestTimestamp)
  const visible = useMemo(() => chart.series.map((item) => ({ ...item, points: item.dates.map((date, index) => ({ date, timestamp: dateToTimestamp(date), value: item.values[index] })).filter((point) => point.timestamp >= cutoff) })).filter((item) => active[item.id]), [active, chart.series, cutoff])
  const timestamps = visible.flatMap((item) => item.points.map((point) => point.timestamp))
  const minTimestamp = Math.min(...timestamps); const maxTimestamp = Math.max(...timestamps)
  const plotWidth = width - left - right; const plotHeight = height - top - bottom
  const x = (timestamp: number) => left + (timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1) * plotWidth
  const allValues = visible.flatMap((item) => item.points.map((point) => point.value)); if (typeof chart.reference === 'number') allValues.push(chart.reference)
  const rawMin = Math.min(...allValues); const rawMax = Math.max(...allValues); const padding = Math.max((rawMax - rawMin) * .12, Math.abs(rawMax || 1) * .02, .15)
  const minValue = rawMin - padding; const maxValue = rawMax + padding
  const y = (value: number) => top + (maxValue - value) / Math.max(maxValue - minValue, .001) * plotHeight
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + index / 5 * (maxTimestamp - minTimestamp))
  const yTicks = Array.from({ length: 5 }, (_, index) => maxValue - index / 4 * (maxValue - minValue))
  const maxGap: Record<ChartSeries['frequency'], number> = { '日': 7, '周': 18, '月': 45, '季': 130, '年': 400 }
  const path = (item: typeof visible[number]) => item.points.map((point, index) => { const previous = index ? item.points[index - 1] : null; const gap = previous ? (point.timestamp - previous.timestamp) / 86_400_000 : 0; return `${index === 0 || gap > maxGap[item.frequency] ? 'M' : 'L'} ${x(point.timestamp).toFixed(2)} ${y(point.value).toFixed(2)}` }).join(' ')
  const toggle = (id: string) => setActive((current) => current[id] && Object.values(current).filter(Boolean).length === 1 ? current : { ...current, [id]: !current[id] })
  const hoverRows = hoverTimestamp === null ? [] : visible.map((item) => ({ item, point: item.points.reduce((nearest, point) => Math.abs(point.timestamp - hoverTimestamp) < Math.abs(nearest.timestamp - hoverTimestamp) ? point : nearest) }))

  return <article className="employment-chart-card gdp-chart-card consumption-chart-card late-module-chart-card">
    <header><div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div><div className="range-switch" role="group" aria-label={`${chart.title}时间范围`}>{RANGE_OPTIONS.map((option) => <button className={range === option.key ? 'active' : ''} key={option.key} type="button" onClick={() => setRange(option.key)}>{option.label}</button>)}</div></header>
    <div className="series-switches" role="group" aria-label={`${chart.title}序列开关`}>{chart.series.map((item) => <button aria-pressed={active[item.id]} className={active[item.id] ? 'active' : ''} key={item.id} type="button" onClick={() => toggle(item.id)}><i style={{ background: item.color }} /><span>{item.label}</span><strong>{chartValue(item.latestValue, item.unit)}</strong><small>{formatDate(item.latestObservation)}</small></button>)}</div>
    <div className="multi-chart-wrap"><svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}折线图`} onPointerLeave={() => setHoverTimestamp(null)} onPointerMove={(event) => { const bounds = event.currentTarget.getBoundingClientRect(); const svgX = (event.clientX - bounds.left) / bounds.width * width; setHoverTimestamp(minTimestamp + Math.min(1, Math.max(0, (svgX - left) / plotWidth)) * (maxTimestamp - minTimestamp)) }}>
      {yTicks.map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" /><text x={left - 9} y={y(tick) + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick)}</text></g>)}
      <text x={left} y={12} className="employment-axis-label gdp-axis-unit">{chart.unit}</text>
      {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">{timestampLabel(tick)}</text>)}
      {typeof chart.reference === 'number' && chart.reference >= minValue && chart.reference <= maxValue && <line x1={left} x2={width - right} y1={y(chart.reference)} y2={y(chart.reference)} className="chart-reference-line" />}
      {visible.map((item) => <path key={item.id} d={path(item)} fill="none" stroke={item.color} strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />)}
      {hoverTimestamp !== null && <line className="employment-hover-line" x1={x(hoverTimestamp)} x2={x(hoverTimestamp)} y1={top} y2={height - bottom} />}
    </svg></div><small className="gdp-chart-scroll-hint">图表可横向滑动查看完整区间</small>
    <div className="chart-readout" aria-live="polite">{hoverRows.length ? hoverRows.map(({ item, point }) => <span key={item.id}><i style={{ background: item.color }} />{item.label}<strong>{chartValue(point.value, item.unit)}</strong><small>{formatDate(point.date)}</small></span>) : <span className="chart-readout-hint">移动鼠标读取各序列同一时点附近的数值</span>}</div>
    <footer><div className="chart-source-list">{chart.series.map((item) => <a href={item.source.url} key={item.id} target="_blank" rel="noreferrer"><strong>{item.label}</strong><span>{item.source.institution} · {item.source.code}</span><small>{item.transformLabel || item.source.rawUnit}</small></a>)}</div></footer>
    <div className="employment-explanation"><div><span>数据是什么</span><p>{chart.explanation.what}</p></div><div><span>怎么读</span><p>{chart.explanation.howToRead}</p></div><div><span>口径警示</span><p>{chart.explanation.caveat}</p></div><small>{chart.explanation.pptSlide}</small></div>
  </article>
}

function RouteMap({ module }: { module: ModuleData }) { return <section className="employment-route-map" aria-label={`美国${module.label}研究路线图`}><header><div><span>CHAPTER {module.chapter} · ROUTE MAP</span><h2>{module.title}</h2><p>{module.subtitle}</p></div><aside><strong>第{module.slides}页</strong><span>{dataset.frameworkSource.file}</span></aside></header><div className="employment-route-core"><span>核心判断</span><strong>{module.core}</strong></div><div className="employment-route-grid">{module.routeMap.map((branch) => <article key={branch.id}><header><span>{branch.subtitle}</span><h3>{branch.title}</h3></header><ol>{branch.nodes.map((node) => <li key={node.title}><strong>{node.title}</strong><span>{node.detail}</span></li>)}</ol></article>)}</div></section> }
function Passports({ module }: { module: ModuleData }) { return <section className="employment-passports" aria-label={`${module.label}数据身份证`}><header><span>DATA PASSPORTS</span><h2>先分清生产方式、覆盖面与修订风险</h2><p>发布时间、覆盖面和市场影响力是不同维度；每条序列保留自己的观测日期、频率、单位与机构。</p></header><div className="employment-passport-wrap"><table aria-label={`${module.label}数据身份证`}><thead><tr><th>数据</th><th>生产者/方法</th><th>频率</th><th>覆盖</th><th>修订</th><th>主要用途</th><th>首要陷阱</th></tr></thead><tbody>{module.passports.map((item) => <tr key={item.id}><th><strong>{item.title}</strong><span>{item.pptSlide}</span></th><td>{item.producer}</td><td>{item.frequency}</td><td>{item.coverage}</td><td>{item.revision}</td><td>{item.use}</td><td>{item.pitfall}</td></tr>)}</tbody></table></div></section> }

export function UsLateModuleDetail({ category, onBack }: { category: LateCategory; onBack: () => void }) {
  const module = dataset.modules[category]
  const observations = module.sections.flatMap((section) => section.charts.flatMap((item) => item.series.map((item) => item.latestObservation)))
  const latestObservation = observations.reduce((latest, item) => item > latest ? item : latest, '')
  const missingCount = Object.values(dataset.dataQuality.missingPeriods).filter((items) => items.length).length
  return <div className={`deep-research-page deep-research-page--${ACCENT_CLASS[module.accent]}`} role="document" aria-label={`美国${module.label}深度数据页`}>
    <div className="page-heading us-macro-heading"><div><button className="history-back" type="button" onClick={onBack}><ArrowLeft size={15} />返回宏观框架</button><p className="eyebrow">US ECONOMY · IFIND CHAPTER {module.chapter}</p><h1>美国{module.label}</h1><p>{module.subtitle}</p></div><div className="as-of"><span>本页最近观测</span><strong>{formatDate(latestObservation)}</strong></div></div>
    <section className="employment-headline-grid late-headline-grid" aria-label={`美国${module.label}状态摘要`}>{module.headline.map((item, index) => <article key={`${item.id}-${index}`}><span>0{index + 1} · {item.label}</span><h2>{item.title}</h2><div><strong>{formatValue(item.value)}</strong><b>{item.unit}</b></div><footer><small>{formatDate(item.observation)}</small><em>{item.source}</em></footer></article>)}</section>
    <RouteMap module={module} /><Passports module={module} />
    <nav className="inflation-section-nav employment-section-nav late-section-nav" aria-label={`${module.label}栏目分区`}>{module.sections.map((section, index) => <button key={section.id} type="button" onClick={() => scrollToSection(`${category}-${section.id}`)}><span>{String(index + 1).padStart(2, '0')}</span>{section.title.split('：')[0]}</button>)}</nav>
    {module.sections.map((section, index) => <section className="inflation-section" id={`${category}-${section.id}`} key={section.id}><header className="inflation-section-heading"><span>{String(index + 1).padStart(2, '0')} · DATA WORKSPACE</span><div><h2>{section.title}</h2><p>{section.description}</p></div></header><div className="employment-chart-grid">{section.charts.map((item) => <ResearchChart chart={item} key={item.id} />)}</div></section>)}
    <section className="late-availability" aria-label={`${module.label}数据边界`}><header><span>AVAILABILITY & RESEARCH BOUNDARY</span><h2>明确不可得项、事件数据与静态案例</h2><p>不以相近序列替代PPT指定口径，也不把历史快照伪装成可更新数据。</p></header><div>{module.availability.map((item) => <article key={item.label}><span>{item.status.replaceAll('-', ' ').toUpperCase()}</span><h3>{item.label}</h3><p>{item.explanation}</p></article>)}</div></section>
    <section className="inflation-method-card employment-method-card late-method-card"><div><span>DATA CONTRACT</span><h2>iFinD数据口径与定期更新</h2><p>{dataset.dataQuality.note}</p></div><div className="cross-check-list"><article><CheckCircle2 size={15} /><div><strong>{dataset.dataQuality.verifiedSeries}条源序列</strong><span>五个模块共用一份可回放原始快照，逐条核验元数据和量级</span></div></article><article><CheckCircle2 size={15} /><div><strong>异步时间透明</strong><span>日、周、月、季、年频各保留独立最新观测，不制造共同as-of</span></div></article><article><CheckCircle2 size={15} /><div><strong>缺口检查</strong><span>{missingCount}条月/季频序列存在日历缺口，图表按时间间隔断线</span></div></article></div><footer><Info size={14} /><span>快照生成 {dataset.generatedAt.slice(0, 10)}；定期更新运行 <code>npm run refresh:us-late-modules</code>。</span></footer></section>
    <footer className="us-macro-source"><div><strong>数据来源：iFinD经济数据库（EDB）。</strong><span>{module.researchBasis[0]} · {dataset.frameworkSource.file}</span></div><button type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button></footer>
  </div>
}
