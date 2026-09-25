import { useMemo, useState } from 'react'
import { ArrowLeft, CheckCircle2, ChevronRight, Info } from 'lucide-react'
import consumptionData from './data/usConsumptionData.json'

type RangeKey = '3Y' | '5Y' | '10Y' | 'ALL'
type SourceMeta = { provider: string; institution: string; code: string; name: string; rawUnit: string; url: string; latestObservation: string }
type ChartSeries = { id: string; label: string; dates: string[]; values: number[]; color: string; unit: string; frequency: '月' | '季' | '年'; latestValue: number; latestObservation: string; source: SourceMeta; transformLabel?: string }
type ChartExplanation = { what: string; howToRead: string; caveat: string; pptSlide: string }
type ChartDefinition = { id: string; kind: 'line'; eyebrow: string; title: string; description: string; unit: string; defaultRange: RangeKey; reference?: number; series: ChartSeries[]; explanation: ChartExplanation }
type Section = { title: string; description: string; charts: ChartDefinition[] }
type ConsumptionDataset = {
  schemaVersion: number; generatedAt: string; source: string
  frameworkSource: { file: string; slides: string; routeSlide: number }
  routeMap: Array<{ id: string; title: string; subtitle: string; nodes: Array<{ title: string; detail: string }> }>
  dataPassports: Array<{ id: string; title: string; producer: string; frequency: string; coverage: string; revision: string; use: string; pitfall: string; pptSlide: string }>
  headline: Array<{ id: string; label: string; title: string; value: number; unit: string; observation: string; source: string }>
  drivers: Array<{ id: string; title: string; mechanism: string; signal: string; status: string; note: string }>
  sections: { anchor: Section; retail: Section; income: Section; structure: Section; sentiment: Section }
  highFrequency: Array<{ name: string; frequency: string; coverage: string; use: string; status: string; caveat: string }>
  caseStudy: { title: string; summary: string; formula: string; caveat: string; pptSlide: string }
  availability: Array<{ id: string; label: string; status: string; explanation: string }>
  dataQuality: { missingPeriods: Record<string, string[]>; accountingChecks: Record<string, number | boolean>; note: string }
  researchBasis: string[]
}

const dataset = consumptionData as ConsumptionDataset
const RANGE_OPTIONS: Array<{ key: RangeKey; label: string; years: number | null }> = [
  { key: '3Y', label: '3年', years: 3 }, { key: '5Y', label: '5年', years: 5 },
  { key: '10Y', label: '10年', years: 10 }, { key: 'ALL', label: '全部', years: null },
]

function formatValue(value: number, digits?: number) {
  const decimals = digits ?? (Math.abs(value) >= 100 ? 0 : 1)
  return new Intl.NumberFormat('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)
}
function formatDate(date: string) {
  if (date.length < 6) return date
  return date.length >= 8 ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}` : `${date.slice(0, 4)}-${date.slice(4, 6)}`
}
function dateToTimestamp(date: string) { return Date.UTC(Number(date.slice(0, 4)), Number(date.slice(4, 6) || '1') - 1, Number(date.slice(6, 8) || '1')) }
function timestampLabel(timestamp: number) { const date = new Date(timestamp); return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}` }
function chartValue(value: number, unit: string) { return `${formatValue(value)}${unit.includes('%') || unit === 'σ' ? unit === 'σ' ? 'σ' : '%' : unit ? ` ${unit}` : ''}` }
function cutoffFor(range: RangeKey, latest: number) { const years = RANGE_OPTIONS.find((item) => item.key === range)?.years; return years == null ? Number.NEGATIVE_INFINITY : latest - years * 365.25 * 86_400_000 }
function scrollToSection(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }

function ConsumptionChart({ chart }: { chart: ChartDefinition }) {
  const width = 920; const height = 350; const left = 64; const right = 24; const top = 18; const bottom = 42
  const [range, setRange] = useState<RangeKey>(chart.defaultRange)
  const [active, setActive] = useState<Record<string, boolean>>(() => Object.fromEntries(chart.series.map((series) => [series.id, true])))
  const [hoverTimestamp, setHoverTimestamp] = useState<number | null>(null)
  const latestTimestamp = Math.max(...chart.series.flatMap((series) => series.dates.map(dateToTimestamp)))
  const cutoff = cutoffFor(range, latestTimestamp)
  const visible = useMemo(() => chart.series.map((series) => ({ ...series, points: series.dates.map((date, index) => ({ date, timestamp: dateToTimestamp(date), value: series.values[index] })).filter((point) => point.timestamp >= cutoff) })).filter((series) => active[series.id]), [active, chart.series, cutoff])
  const timestamps = visible.flatMap((series) => series.points.map((point) => point.timestamp)); const minTimestamp = Math.min(...timestamps); const maxTimestamp = Math.max(...timestamps)
  const plotWidth = width - left - right; const plotHeight = height - top - bottom
  const x = (timestamp: number) => left + (timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1) * plotWidth
  const allValues = visible.flatMap((series) => series.points.map((point) => point.value)); if (typeof chart.reference === 'number') allValues.push(chart.reference)
  const rawMin = Math.min(...allValues); const rawMax = Math.max(...allValues); const padding = Math.max((rawMax - rawMin) * .12, Math.abs(rawMax || 1) * .02, .15)
  const minValue = rawMin - padding; const maxValue = rawMax + padding; const y = (value: number) => top + (maxValue - value) / Math.max(maxValue - minValue, .001) * plotHeight
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + index / 5 * (maxTimestamp - minTimestamp)); const yTicks = Array.from({ length: 5 }, (_, index) => maxValue - index / 4 * (maxValue - minValue))
  const path = (series: typeof visible[number]) => series.points.map((point, index) => { const previous = index ? series.points[index - 1] : null; const maxGap = series.frequency === '月' ? 45 : series.frequency === '季' ? 130 : 400; const gap = previous ? (point.timestamp - previous.timestamp) / 86_400_000 : 0; return `${index === 0 || gap > maxGap ? 'M' : 'L'} ${x(point.timestamp).toFixed(2)} ${y(point.value).toFixed(2)}` }).join(' ')
  const toggle = (id: string) => setActive((current) => current[id] && Object.values(current).filter(Boolean).length === 1 ? current : { ...current, [id]: !current[id] })
  const hoverRows = hoverTimestamp === null ? [] : visible.map((series) => ({ series, point: series.points.reduce((nearest, point) => Math.abs(point.timestamp - hoverTimestamp) < Math.abs(nearest.timestamp - hoverTimestamp) ? point : nearest) }))
  return <article className="employment-chart-card gdp-chart-card consumption-chart-card">
    <header><div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div><div className="range-switch" role="group" aria-label={`${chart.title}时间范围`}>{RANGE_OPTIONS.map((option) => <button className={range === option.key ? 'active' : ''} key={option.key} type="button" onClick={() => setRange(option.key)}>{option.label}</button>)}</div></header>
    <div className="series-switches" role="group" aria-label={`${chart.title}序列开关`}>{chart.series.map((series) => <button aria-pressed={active[series.id]} className={active[series.id] ? 'active' : ''} key={series.id} type="button" onClick={() => toggle(series.id)}><i style={{ background: series.color }} /><span>{series.label}</span><strong>{chartValue(series.latestValue, series.unit)}</strong><small>{formatDate(series.latestObservation)}</small></button>)}</div>
    <div className="multi-chart-wrap"><svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}折线图`} onPointerLeave={() => setHoverTimestamp(null)} onPointerMove={(event) => { const bounds = event.currentTarget.getBoundingClientRect(); const svgX = (event.clientX - bounds.left) / bounds.width * width; setHoverTimestamp(minTimestamp + Math.min(1, Math.max(0, (svgX - left) / plotWidth)) * (maxTimestamp - minTimestamp)) }}>
      {yTicks.map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" /><text x={left - 9} y={y(tick) + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick)}</text></g>)}
      <text x={left} y={12} className="employment-axis-label gdp-axis-unit">{chart.unit}</text>
      {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">{timestampLabel(tick)}</text>)}
      {typeof chart.reference === 'number' && chart.reference >= minValue && chart.reference <= maxValue && <line x1={left} x2={width - right} y1={y(chart.reference)} y2={y(chart.reference)} className="chart-reference-line" />}
      {visible.map((series) => <path key={series.id} data-series-id={series.id} d={path(series)} fill="none" stroke={series.color} strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />)}
      {hoverTimestamp !== null && <line className="employment-hover-line" x1={x(hoverTimestamp)} x2={x(hoverTimestamp)} y1={top} y2={height - bottom} />}
    </svg></div><small className="gdp-chart-scroll-hint">图表可横向滑动查看完整区间</small>
    <div className="chart-readout" aria-live="polite">{hoverRows.length ? hoverRows.map(({ series, point }) => <span key={series.id}><i style={{ background: series.color }} />{series.label}<strong>{chartValue(point.value, series.unit)}</strong><small>{formatDate(point.date)}</small></span>) : <span className="chart-readout-hint">移动鼠标读取各序列同一时点附近的数值</span>}</div>
    <footer><div className="chart-source-list">{chart.series.map((series) => <a href={series.source.url} key={series.id} target="_blank" rel="noreferrer"><strong>{series.label}</strong><span>{series.source.institution} · {series.source.code}</span><small>{series.transformLabel || series.source.rawUnit}</small></a>)}</div></footer>
    <div className="employment-explanation"><div><span>数据是什么</span><p>{chart.explanation.what}</p></div><div><span>怎么读</span><p>{chart.explanation.howToRead}</p></div><div><span>口径警示</span><p>{chart.explanation.caveat}</p></div><small>{chart.explanation.pptSlide}</small></div>
  </article>
}

function RouteMap() { return <section className="employment-route-map" aria-label="美国消费研究路线图"><header><div><span>CHAPTER 4 · ROUTE MAP</span><h2>双轨数据，三大背离</h2><p>消费占GDP约三分之二且高度平滑：先看收入、财富、信贷和预期四个驱动轮，再用零售与个人收支两条官方数据链确认，最后排除软硬、名实与总量结构三类错觉。</p></div><aside><strong>第{dataset.frameworkSource.slides}页</strong><span>{dataset.frameworkSource.file}</span></aside></header><div className="employment-route-core"><span>核心判断</span><strong>C = f（收入，财富，信贷，预期）× MPC异质性</strong></div><div className="employment-route-grid">{dataset.routeMap.map((branch) => <article key={branch.id}><header><span>{branch.subtitle}</span><h3>{branch.title}</h3></header><ol>{branch.nodes.map((node) => <li key={node.title}><strong>{node.title}</strong><span>{node.detail}</span></li>)}</ol></article>)}</div></section> }
function PassportTable() { return <section className="employment-passports" aria-label="消费数据身份证"><header><span>DATA PASSPORTS</span><h2>先分清生产方式、覆盖面与修订风险</h2><p>零售、个人收支、信贷和调查数据位于不同信息链条；发布时间更快不等于口径更全，覆盖更全也不等于适合交易单月意外。</p></header><div className="employment-passport-wrap"><table aria-label="消费数据身份证"><thead><tr><th>数据</th><th>生产者/方法</th><th>频率</th><th>覆盖</th><th>修订</th><th>主要用途</th><th>首要陷阱</th></tr></thead><tbody>{dataset.dataPassports.map((item) => <tr key={item.id}><th><strong>{item.title}</strong><span>{item.pptSlide}</span></th><td>{item.producer}</td><td>{item.frequency}</td><td>{item.coverage}</td><td>{item.revision}</td><td>{item.use}</td><td>{item.pitfall}</td></tr>)}</tbody></table></div></section> }
function Drivers() { return <section className="consumption-drivers" aria-label="消费四个驱动轮"><header><span>FOUR DRIVERS</span><h2>四个驱动轮要逐项核对</h2><p>MPC异质性决定冲击落在谁身上：低收入家庭的边际消费倾向更高，总量稳定不能代替分布判断。</p></header><div>{dataset.drivers.map((driver) => <article key={driver.id}><span>{driver.title}</span><h3>{driver.mechanism}</h3><strong>{driver.status}</strong><p>{driver.signal}</p><small>{driver.note}</small></article>)}</div></section> }
function HighFrequency() { return <section className="consumption-hf"><header><span>THIRD-PARTY & HIGH FREQUENCY</span><h2>高频只做预告和结构校验</h2><p>刷卡、航空、餐饮和同店销售补足官方服务统计滞后，但不把私人样本的水平冒充全体消费。</p></header><div>{dataset.highFrequency.map((item) => <article key={item.name}><span>{item.status}</span><h3>{item.name}</h3><strong>{item.frequency} · {item.coverage}</strong><p>{item.use}</p><small>{item.caveat}</small></article>)}</div></section> }
function AvailabilityPanel() { return <div className="employment-availability">{dataset.availability.map((item) => <article key={item.id}><span>{item.status.replaceAll('-', ' ').toUpperCase()}</span><h3>{item.label}</h3><p>{item.explanation}</p></article>)}</div> }
function SectionHeading({ code, section }: { code: string; section: Section }) { return <header className="inflation-section-heading"><span>{code}</span><div><h2>{section.title}</h2><p>{section.description}</p></div></header> }

export function UsConsumptionDetail({ onBack }: { onBack: () => void }) {
  const latestObservation = dataset.headline.reduce((latest, item) => item.observation > latest ? item.observation : latest, '')
  const missingCount = Object.values(dataset.dataQuality.missingPeriods).filter((items) => items.length).length
  return <>
    <div className="page-heading us-macro-heading"><div><button className="history-back" type="button" onClick={onBack}><ArrowLeft size={15} />返回宏观框架</button><p className="eyebrow">US ECONOMY · IFIND CONSUMPTION</p><h1>美国消费</h1><p>沿“四个驱动轮—官方双轨—三大背离”判断消费韧性：体量看服务，波动看耐用品，最快硬数据看零售控制组。</p></div><div className="as-of"><span>本页最近观测</span><strong>{formatDate(latestObservation)}</strong></div></div>
    <section className="employment-headline-grid consumption-headline-grid" aria-label="美国消费状态摘要">{dataset.headline.map((item, index) => <article key={item.id}><span>0{index + 1} · {item.label}</span><h2>{item.title}</h2><div><strong>{formatValue(item.value)}</strong><b>{item.unit}</b></div><footer><small>{formatDate(item.observation)}</small><em>{item.source}</em></footer></article>)}</section>
    <RouteMap /><Drivers /><PassportTable />
    <nav className="inflation-section-nav employment-section-nav" aria-label="消费栏目分区"><button type="button" onClick={() => scrollToSection('consumption-anchor')}><span>01</span>驱动轮</button><button type="button" onClick={() => scrollToSection('consumption-retail')}><span>02</span>零售快轨</button><button type="button" onClick={() => scrollToSection('consumption-income')}><span>03</span>收支慢轨</button><button type="button" onClick={() => scrollToSection('consumption-structure')}><span>04</span>消费结构</button><button type="button" onClick={() => scrollToSection('consumption-sentiment')}><span>05</span>软硬背离</button></nav>
    {([['consumption-anchor', '01 · ANCHOR & DRIVERS', dataset.sections.anchor], ['consumption-retail', '02 · RETAIL FAST TRACK', dataset.sections.retail], ['consumption-income', '03 · INCOME, SAVING & CREDIT', dataset.sections.income], ['consumption-structure', '04 · MIX & CYCLICAL AMPLIFIER', dataset.sections.structure], ['consumption-sentiment', '05 · SENTIMENT & DIVERGENCE', dataset.sections.sentiment]] as const).map(([id, code, section]) => <section className="inflation-section" id={id} key={id}><SectionHeading code={code} section={section} /><div className="employment-chart-grid">{section.charts.map((chart) => <ConsumptionChart chart={chart} key={chart.id} />)}</div>{id === 'consumption-income' && <HighFrequency />}{id === 'consumption-sentiment' && <AvailabilityPanel />}</section>)}
    <section className="consumption-case" aria-label="超额储蓄历史案例"><header><span>06 · HISTORICAL CASE</span><h2>{dataset.caseStudy.title}</h2><p>{dataset.caseStudy.summary}</p></header><div><strong>{dataset.caseStudy.formula}</strong><p>{dataset.caseStudy.caveat}</p><small>{dataset.caseStudy.pptSlide}</small></div></section>
    <section className="inflation-method-card employment-method-card"><div><span>07 · DATA CONTRACT</span><h2>iFinD数据口径与定期更新</h2><p>23条源序列逐条绑定指标码、精确名称、单位、频率、原始机构、合理区间与独立观测日期；派生序列可重复构建。</p></div><div className="cross-check-list"><article><CheckCircle2 size={15} /><div><strong>身份与量级核验</strong><span>每次刷新均先搜索并验证元数据，再下载完整时序</span></div></article><article><CheckCircle2 size={15} /><div><strong>确定性变换</strong><span>控制组、CPI实际化、结构份额、同比与z分数均由脚本重建</span></div></article><article><CheckCircle2 size={15} /><div><strong>缺口与频率透明</strong><span>{missingCount}条月/季频序列存在日历缺口；年、季、月数据各保留自己的最新日期</span></div></article></div><footer><Info size={14} /><span>{dataset.dataQuality.note} 快照生成 {dataset.generatedAt.slice(0, 10)}；定期更新运行 <code>npm run refresh:us-consumption</code>。</span></footer></section>
    <footer className="us-macro-source"><div><strong>数据来源：iFinD经济数据库（EDB）。</strong><span>{dataset.researchBasis[0]} · {dataset.frameworkSource.file}</span></div><button type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button></footer>
  </>
}
