import { useMemo, useState } from 'react'
import { ArrowLeft, CheckCircle2, ChevronRight, Info } from 'lucide-react'
import gdpData from './data/usGdpData.json'

type RangeKey = '3Y' | '5Y' | '10Y' | 'ALL'
type SourceMeta = { provider: string; institution: string; code: string; name: string; rawUnit: string; url: string; latestObservation: string }
type ChartExplanation = { what: string; howToRead: string; caveat: string; pptSlide: string }
type ChartSeries = {
  id: string; label: string; dates: string[]; values: number[]; color: string; unit: string
  frequency: '月' | '周' | '季' | '年'; latestValue: number; latestObservation: string
  source: SourceMeta; transformLabel?: string
}
type ChartDefinition = {
  id: string; kind: 'line' | 'bar'; eyebrow: string; title: string; description: string; unit: string
  defaultRange: RangeKey; reference?: number; rebasedAt?: string; series: ChartSeries[]; totalSeries?: ChartSeries
  explanation: ChartExplanation
}
type Section = { title: string; description: string; charts: ChartDefinition[]; expenditureShares?: ExpenditureShares }
type ExpenditureShares = {
  period: string; identityTotal: number; note: string
  rows: Array<{ id: string; label: string; value: number; color: string; source: SourceMeta }>
}
type GdpDataset = {
  schemaVersion: number; generatedAt: string; source: string; sourceProviders: string[]
  frameworkSource: { file: string; slides: string; routeSlide: number }
  routeMap: Array<{ id: string; title: string; subtitle: string; nodes: Array<{ title: string; detail: string }> }>
  dataPassports: Array<{ id: string; title: string; producer: string; frequency: string; revision: string; use: string; pitfall: string; pptSlide: string }>
  headline: Array<{ id: string; label: string; title: string; value: number; unit: string; observation: string; source: string }>
  sections: { benchmark: Section; coreDemand: Section; incomePrices: Section; cycleTracking: Section }
  revisionCase: { title: string; unit: string; rows: Array<{ period: string; advance: number; third: number; latest: number }>; source: string; caveat: string }
  informationFlow: Array<{ timing: string; release: string; target: string }>
  availability: Array<{ id: string; label: string; status: 'available' | 'not-integrated'; explanation: string }>
  dataQuality: { missingPeriods: Record<string, string[]>; accountingChecks: Record<string, number | string>; note: string }
  researchBasis: string[]
}

const dataset = gdpData as GdpDataset
const RANGE_OPTIONS: Array<{ key: RangeKey; label: string; years: number | null }> = [
  { key: '3Y', label: '3年', years: 3 }, { key: '5Y', label: '5年', years: 5 },
  { key: '10Y', label: '10年', years: 10 }, { key: 'ALL', label: '全部', years: null },
]

function formatValue(value: number, digits?: number): string {
  const decimals = digits ?? (Math.abs(value) >= 100 ? 0 : 1)
  return new Intl.NumberFormat('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)
}
function formatDate(date: string): string {
  if (date.length < 6) return date
  return date.length >= 8 ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}` : `${date.slice(0, 4)}-${date.slice(4, 6)}`
}
function dateToTimestamp(date: string): number {
  return Date.UTC(Number(date.slice(0, 4)), Number(date.slice(4, 6)) - 1, Number(date.slice(6, 8) || '1'))
}
function timestampLabel(timestamp: number): string {
  const date = new Date(timestamp)
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`
}
function chartValue(value: number, unit: string): string {
  return `${formatValue(value)}${unit === '%' || unit.includes('%') ? '%' : unit ? ` ${unit}` : ''}`
}
function cutoffFor(range: RangeKey, latest: number): number {
  const years = RANGE_OPTIONS.find((item) => item.key === range)?.years
  return years == null ? Number.NEGATIVE_INFINITY : latest - years * 365.25 * 86_400_000
}

function RangeSwitch({ title, value, onChange }: { title: string; value: RangeKey; onChange: (value: RangeKey) => void }) {
  return <div className="range-switch" role="group" aria-label={`${title}时间范围`}>{RANGE_OPTIONS.map((option) => <button className={value === option.key ? 'active' : ''} key={option.key} type="button" onClick={() => onChange(option.key)}>{option.label}</button>)}</div>
}

function SeriesSwitches({ chart, active, onToggle }: { chart: ChartDefinition; active: Record<string, boolean>; onToggle: (id: string) => void }) {
  return <div className="series-switches" role="group" aria-label={`${chart.title}序列开关`}>{chart.series.map((series) => <button aria-pressed={active[series.id]} className={active[series.id] ? 'active' : ''} key={series.id} type="button" onClick={() => onToggle(series.id)}><i style={{ background: series.color }} /><span>{series.label}</span><strong>{chartValue(series.latestValue, series.unit)}</strong><small>{formatDate(series.latestObservation)}</small></button>)}</div>
}

function SourceList({ series }: { series: ChartSeries[] }) {
  return <div className="chart-source-list">{series.map((item) => <a href={item.source.url} key={item.id} target="_blank" rel="noreferrer"><strong>{item.label}</strong><span>{item.source.provider} · {item.source.code}</span><small>{item.transformLabel || item.source.rawUnit || 'iFinD未提供单位'}</small></a>)}</div>
}

function ExplanationPanel({ explanation }: { explanation: ChartExplanation }) {
  return <div className="employment-explanation"><div><span>数据是什么</span><p>{explanation.what}</p></div><div><span>怎么读</span><p>{explanation.howToRead}</p></div><div><span>口径警示</span><p>{explanation.caveat}</p></div><small>{explanation.pptSlide}</small></div>
}

function GdpLineChart({ chart }: { chart: ChartDefinition }) {
  const width = 920; const height = 350; const left = 64; const right = 24; const top = 18; const bottom = 42
  const [range, setRange] = useState<RangeKey>(chart.defaultRange)
  const [active, setActive] = useState<Record<string, boolean>>(() => Object.fromEntries(chart.series.map((series) => [series.id, true])))
  const [hoverTimestamp, setHoverTimestamp] = useState<number | null>(null)
  const latestTimestamp = Math.max(...chart.series.flatMap((series) => series.dates.map(dateToTimestamp)))
  const cutoff = cutoffFor(range, latestTimestamp)
  const visible = useMemo(() => chart.series.map((series) => ({ ...series, points: series.dates.map((date, index) => ({ date, timestamp: dateToTimestamp(date), value: series.values[index] })).filter((point) => point.timestamp >= cutoff) })).filter((series) => active[series.id]), [active, chart.series, cutoff])
  const timestamps = visible.flatMap((series) => series.points.map((point) => point.timestamp))
  const minTimestamp = Math.min(...timestamps); const maxTimestamp = Math.max(...timestamps)
  const plotWidth = width - left - right; const plotHeight = height - top - bottom
  const x = (timestamp: number) => left + (timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1) * plotWidth
  const allValues = visible.flatMap((series) => series.points.map((point) => point.value))
  if (typeof chart.reference === 'number') allValues.push(chart.reference)
  const rawMin = Math.min(...allValues); const rawMax = Math.max(...allValues)
  const padding = Math.max((rawMax - rawMin) * .12, Math.abs(rawMax || 1) * .02, .15)
  const minValue = rawMin - padding; const maxValue = rawMax + padding
  const y = (value: number) => top + (maxValue - value) / Math.max(maxValue - minValue, .001) * plotHeight
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + index / 5 * (maxTimestamp - minTimestamp))
  const yTicks = Array.from({ length: 5 }, (_, index) => maxValue - index / 4 * (maxValue - minValue))
  const linePath = (series: typeof visible[number]) => series.points.map((point, index) => {
    const previous = index ? series.points[index - 1] : null
    const maxGap = series.frequency === '周' ? 12 : series.frequency === '月' ? 45 : series.frequency === '季' ? 130 : 400
    const gap = previous ? (point.timestamp - previous.timestamp) / 86_400_000 : 0
    return `${index === 0 || gap > maxGap ? 'M' : 'L'} ${x(point.timestamp).toFixed(2)} ${y(point.value).toFixed(2)}`
  }).join(' ')
  const toggle = (id: string) => setActive((current) => current[id] && Object.values(current).filter(Boolean).length === 1 ? current : { ...current, [id]: !current[id] })
  const hoverRows = hoverTimestamp === null ? [] : visible.map((series) => ({ series, point: series.points.reduce((nearest, point) => Math.abs(point.timestamp - hoverTimestamp) < Math.abs(nearest.timestamp - hoverTimestamp) ? point : nearest) }))

  return <article className="employment-chart-card gdp-chart-card">
    <header><div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div><RangeSwitch title={chart.title} value={range} onChange={setRange} /></header>
    <SeriesSwitches chart={chart} active={active} onToggle={toggle} />
    <div className="multi-chart-wrap"><svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}折线图`} onPointerLeave={() => setHoverTimestamp(null)} onPointerMove={(event) => { const bounds = event.currentTarget.getBoundingClientRect(); const svgX = (event.clientX - bounds.left) / bounds.width * width; const ratio = Math.min(1, Math.max(0, (svgX - left) / plotWidth)); setHoverTimestamp(minTimestamp + ratio * (maxTimestamp - minTimestamp)) }}>
      {yTicks.map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" /><text x={left - 9} y={y(tick) + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick)}</text></g>)}
      <text x={left} y={12} className="employment-axis-label gdp-axis-unit">{chart.unit}</text>
      {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">{timestampLabel(tick)}</text>)}
      {typeof chart.reference === 'number' && chart.reference >= minValue && chart.reference <= maxValue && <line x1={left} x2={width - right} y1={y(chart.reference)} y2={y(chart.reference)} className="chart-reference-line" />}
      {visible.map((series) => <path key={series.id} data-series-id={series.id} d={linePath(series)} fill="none" stroke={series.color} strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />)}
      {hoverTimestamp !== null && <line className="employment-hover-line" x1={x(hoverTimestamp)} x2={x(hoverTimestamp)} y1={top} y2={height - bottom} />}
    </svg></div><small className="gdp-chart-scroll-hint">图表可横向滑动查看完整区间</small>
    <div className="chart-readout" aria-live="polite">{hoverRows.length ? hoverRows.map(({ series, point }) => <span key={series.id}><i style={{ background: series.color }} />{series.label}<strong>{chartValue(point.value, series.unit)}</strong><small>{formatDate(point.date)}</small></span>) : <span className="chart-readout-hint">移动鼠标读取各序列同一时点附近的数值</span>}</div>
    <footer><SourceList series={chart.series} /></footer><ExplanationPanel explanation={chart.explanation} />
  </article>
}

function GdpContributionChart({ chart }: { chart: ChartDefinition }) {
  const width = 920; const height = 350; const left = 58; const right = 24; const top = 18; const bottom = 42
  const [range, setRange] = useState<RangeKey>(chart.defaultRange)
  const latestTimestamp = Math.max(...chart.series.flatMap((series) => series.dates.map(dateToTimestamp)))
  const cutoff = cutoffFor(range, latestTimestamp)
  const maps = chart.series.map((series) => new Map(series.dates.map((date, index) => [date, series.values[index]])))
  const totalMap = new Map((chart.totalSeries?.dates ?? []).map((date, index) => [date, chart.totalSeries?.values[index] ?? 0]))
  const rows = chart.series[0].dates.filter((date) => dateToTimestamp(date) >= cutoff).map((date) => ({ date, timestamp: dateToTimestamp(date), values: maps.map((map) => map.get(date) ?? 0), total: totalMap.get(date) ?? 0 }))
  const extrema = rows.flatMap((row) => [row.values.filter((v) => v > 0).reduce((a, b) => a + b, 0), row.values.filter((v) => v < 0).reduce((a, b) => a + b, 0), row.total])
  const rawMin = Math.min(...extrema, 0); const rawMax = Math.max(...extrema, 0); const padding = Math.max((rawMax - rawMin) * .1, .5)
  const minValue = rawMin - padding; const maxValue = rawMax + padding; const plotWidth = width - left - right; const plotHeight = height - top - bottom
  const minTimestamp = rows[0]?.timestamp ?? 0; const maxTimestamp = rows.at(-1)?.timestamp ?? 1
  const x = (timestamp: number) => left + (timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1) * plotWidth
  const y = (value: number) => top + (maxValue - value) / Math.max(maxValue - minValue, .001) * plotHeight
  const barWidth = Math.max(3, Math.min(26, plotWidth / Math.max(rows.length, 1) * .65))
  const ticks = Array.from({ length: 5 }, (_, index) => maxValue - index / 4 * (maxValue - minValue))
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + index / 5 * (maxTimestamp - minTimestamp))
  const totalPath = rows.map((row, index) => `${index ? 'L' : 'M'} ${x(row.timestamp).toFixed(2)} ${y(row.total).toFixed(2)}`).join(' ')
  return <article className="employment-chart-card gdp-chart-card employment-bar-card">
    <header><div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div><RangeSwitch title={chart.title} value={range} onChange={setRange} /></header>
    <div className="employment-bar-legend">{chart.series.map((series) => <span key={series.id}><i style={{ background: series.color }} />{series.label}</span>)}{chart.totalSeries && <span><i className="employment-total-line" />{chart.totalSeries.label}</span>}</div>
    <div className="multi-chart-wrap"><svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}堆叠柱图`}>
      {ticks.map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" /><text x={left - 9} y={y(tick) + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick)}</text></g>)}
      <text x={left} y={12} className="employment-axis-label gdp-axis-unit">{chart.unit}（柱） / % SAAR（线）</text>
      {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">{timestampLabel(tick)}</text>)}
      <line x1={left} x2={width - right} y1={y(0)} y2={y(0)} className="chart-reference-line" />
      {rows.flatMap((row) => { let positive = 0; let negative = 0; return row.values.map((value, index) => { const start = value >= 0 ? positive : negative; const end = start + value; if (value >= 0) positive = end; else negative = end; return <rect key={`${row.date}-${chart.series[index].id}`} x={x(row.timestamp) - barWidth / 2} y={Math.min(y(start), y(end))} width={barWidth} height={Math.max(1, Math.abs(y(start) - y(end)))} fill={chart.series[index].color}><title>{`${row.date}: ${chart.series[index].label} ${formatValue(value, 2)}个百分点`}</title></rect> }) })}
      {chart.totalSeries && <path d={totalPath} fill="none" stroke={chart.totalSeries.color} strokeWidth="2.2" />}
    </svg></div><small className="gdp-chart-scroll-hint">图表可横向滑动查看完整区间</small>
    <footer><SourceList series={[...chart.series, ...(chart.totalSeries ? [chart.totalSeries] : [])]} /></footer><ExplanationPanel explanation={chart.explanation} />
  </article>
}
function ChartCard({ chart }: { chart: ChartDefinition }) { return chart.kind === 'bar' ? <GdpContributionChart chart={chart} /> : <GdpLineChart chart={chart} /> }

function RouteMap() {
  return <section className="employment-route-map gdp-route-map" aria-label="GDP与经济核算路线图"><header><div><span>CHAPTER 3 · ROUTE MAP</span><h2>先立标尺，再读数据</h2><p>把PPT第95页的5个分支与12个节点转成可更新页面：潜在增速、支出核算、官方多轮估计、高频跟踪、口径陷阱与历史修订复盘。</p></div><aside><strong>第{dataset.frameworkSource.slides}页</strong><span>{dataset.frameworkSource.file}</span></aside></header><div className="employment-route-core"><span>核心判断</span><strong>潜在增速 → 支出结构 → 核心内需 → 双核算 → 高频确认</strong></div><div className="employment-route-grid">{dataset.routeMap.map((branch) => <article key={branch.id}><header><span>{branch.subtitle}</span><h3>{branch.title}</h3></header><ol>{branch.nodes.map((node) => <li key={node.title}><strong>{node.title}</strong><span>{node.detail}</span></li>)}</ol></article>)}</div></section>
}
function PassportTable() {
  return <section className="employment-passports" aria-label="GDP数据身份证"><header><span>DATA PASSPORTS</span><h2>五类数据先分生产方式与修订机制</h2><p>GDP是多源数据的再加工结果；advance、latest、模型估计和高频代理不属于同一信息集。</p></header><div className="employment-passport-wrap"><table aria-label="GDP数据身份证"><thead><tr><th>数据</th><th>生产者/方法</th><th>频率</th><th>修订</th><th>主要用途</th><th>常见误读</th></tr></thead><tbody>{dataset.dataPassports.map((item) => <tr key={item.id}><th><strong>{item.title}</strong><span>{item.pptSlide}</span></th><td>{item.producer}</td><td>{item.frequency}</td><td>{item.revision}</td><td>{item.use}</td><td>{item.pitfall}</td></tr>)}</tbody></table></div></section>
}
function ExpenditureShares({ shares }: { shares: ExpenditureShares }) {
  const max = Math.max(...shares.rows.map((row) => Math.abs(row.value)), 1)
  return <article className="gdp-share-card"><header><div><span>Y = C + I + G + NX</span><h3>最新名义GDP支出结构</h3><p>消费看体量，投资看波动；净出口为负是进口大于出口的会计结果，不等于进口本身造成经济损失。</p></div><strong>{formatDate(shares.period)}</strong></header><div className="gdp-share-grid">{shares.rows.map((row) => <article key={row.id}><span>{row.label}</span><div className={row.value < 0 ? 'negative' : ''}><i style={{ width: `${Math.abs(row.value) / max * 100}%`, background: row.color }} /></div><strong>{formatValue(row.value, 1)}%</strong><small>{row.source.code}</small></article>)}</div><footer><strong>加总 {formatValue(shares.identityTotal, 1)}%</strong><span>{shares.note}</span></footer></article>
}
function RevisionCard() {
  const values = dataset.revisionCase.rows.flatMap((row) => [row.advance, row.third, row.latest]); const min = Math.min(...values, 0); const max = Math.max(...values, 0); const span = max - min || 1
  const y = (value: number) => (max - value) / span * 160
  return <article className="gdp-revision-card"><header><div><span>VINTAGE CASE · 2022H1</span><h3>{dataset.revisionCase.title}</h3></div><strong>{dataset.revisionCase.unit}</strong></header><div className="gdp-revision-chart">{dataset.revisionCase.rows.map((row) => <section key={row.period}><h4>{row.period}</h4><div className="gdp-revision-bars"><b className="gdp-zero-line" style={{ top: `${8 + y(0)}px` }}>0</b>{([['advance', row.advance], ['third', row.third], ['latest', row.latest]] as const).map(([label, value]) => <div key={label}><i style={{ top: `${Math.min(y(value), y(0))}px`, height: `${Math.max(2, Math.abs(y(value) - y(0)))}px` }} /><strong>{value > 0 ? '+' : ''}{value.toFixed(1)}</strong><span>{label}</span></div>)}</div></section>)}</div><footer><p>{dataset.revisionCase.source}</p><p>{dataset.revisionCase.caveat}</p></footer></article>
}
function InformationFlow() {
  return <article className="gdp-flow-card"><header><span>INTRA-QUARTER INFORMATION FLOW</span><h3>GDP是已知月度数据的会计汇总</h3><p>advance发布时，大部分商品消费、住宅、设备、贸易、库存和服务消费输入已经公布。</p></header><ol>{dataset.informationFlow.map((item) => <li key={`${item.timing}-${item.release}`}><span>{item.timing}</span><strong>{item.release}</strong><ChevronRight size={14} /><em>{item.target}</em></li>)}</ol></article>
}
function AvailabilityPanel() {
  return <div className="employment-availability" aria-label="GDP高频数据接入状态">{dataset.availability.map((item) => <article key={item.id}><span>{item.status === 'available' ? 'IFIND · AVAILABLE' : 'NOT INTEGRATED'}</span><h3>{item.label}</h3><p>{item.explanation}</p></article>)}</div>
}
function SectionHeading({ code, section }: { code: string; section: Section }) { return <header className="inflation-section-heading"><span>{code}</span><div><h2>{section.title}</h2><p>{section.description}</p></div></header> }
function scrollToSection(id: string) { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }

export function UsGdpDetail({ onBack }: { onBack: () => void }) {
  const latestObservation = dataset.headline.reduce((latest, item) => item.observation > latest ? item.observation : latest, '')
  const missingCount = Object.values(dataset.dataQuality.missingPeriods).filter((items) => items.length).length
  return <>
    <div className="page-heading us-macro-heading"><div><button className="history-back" type="button" onClick={onBack}><ArrowLeft size={15} />返回宏观框架</button><p className="eyebrow">US ECONOMY · IFIND GDP & NATIONAL ACCOUNTS</p><h1>美国GDP与经济核算</h1><p>先用潜在增速建立标尺，再从支出结构、核心私人内需、GDP/GDI双核算、名义—实际价格桥和高频活动拼图逐层判断。</p></div><div className="as-of"><span>本页最近观测</span><strong>{formatDate(latestObservation)}</strong></div></div>
    <section className="employment-headline-grid gdp-headline-grid" aria-label="美国GDP状态摘要">{dataset.headline.map((item, index) => <article key={item.id}><span>0{index + 1} · {item.label}</span><h2>{item.title}</h2><div><strong>{formatValue(item.value)}</strong><b>{item.unit}</b></div><footer><small>{formatDate(item.observation)}</small><em>{item.source}</em></footer></article>)}</section>
    <RouteMap /><PassportTable />
    <nav className="inflation-section-nav employment-section-nav" aria-label="GDP栏目分区"><button type="button" onClick={() => scrollToSection('gdp-benchmark')}><span>01</span>潜在增速</button><button type="button" onClick={() => scrollToSection('gdp-core')}><span>02</span>核心GDP</button><button type="button" onClick={() => scrollToSection('gdp-income')}><span>03</span>双核算与价格</button><button type="button" onClick={() => scrollToSection('gdp-cycle')}><span>04</span>Nowcast与衰退</button><button type="button" onClick={() => scrollToSection('gdp-vintage')}><span>05</span>修订与信息流</button></nav>
    <section className="inflation-section" id="gdp-benchmark" aria-label="潜在增速与支出结构"><SectionHeading code="01 · BENCHMARK & STRUCTURE" section={dataset.sections.benchmark} /><div className="employment-chart-grid">{dataset.sections.benchmark.charts.map((chart) => <ChartCard chart={chart} key={chart.id} />)}</div>{dataset.sections.benchmark.expenditureShares && <ExpenditureShares shares={dataset.sections.benchmark.expenditureShares} />}</section>
    <section className="inflation-section" id="gdp-core" aria-label="核心GDP与增长贡献"><SectionHeading code="02 · CORE DEMAND" section={dataset.sections.coreDemand} /><div className="employment-chart-grid">{dataset.sections.coreDemand.charts.map((chart) => <ChartCard chart={chart} key={chart.id} />)}</div></section>
    <section className="inflation-section" id="gdp-income" aria-label="收入法与名义实际桥"><SectionHeading code="03 · INCOME & PRICES" section={dataset.sections.incomePrices} /><div className="employment-chart-grid">{dataset.sections.incomePrices.charts.map((chart) => <ChartCard chart={chart} key={chart.id} />)}</div></section>
    <section className="inflation-section" id="gdp-cycle" aria-label="Nowcast与衰退判定"><SectionHeading code="04 · NOWCAST & RECESSION" section={dataset.sections.cycleTracking} /><div className="employment-chart-grid">{dataset.sections.cycleTracking.charts.map((chart) => <ChartCard chart={chart} key={chart.id} />)}</div><AvailabilityPanel /></section>
    <section className="inflation-section" id="gdp-vintage" aria-label="GDP修订与季度内信息流"><header className="inflation-section-heading"><span>05 · VINTAGE & RELEASE FLOW</span><div><h2>修订与季度内信息流</h2><p>把同一观察期的多个vintage与生成GDP的月度输入分开保存，才能真实复盘当时市场看到的信息。</p></div></header><div className="gdp-vintage-grid"><RevisionCard /><InformationFlow /></div></section>
    <section className="inflation-method-card employment-method-card" aria-label="GDP数据口径"><div><span>06 · DATA CONTRACT</span><h2>iFinD数据口径与可更新性</h2><p>每条序列保留独立观测日期、频率、原始单位、指标码和确定性变换；周、月、季频不按数组位置拼接。</p></div><div className="cross-check-list"><article><CheckCircle2 size={15} /><div><strong>身份与量级核验</strong><span>26条iFinD序列逐条核对displayid、精确名称、单位、频率和合理区间</span></div></article><article><CheckCircle2 size={15} /><div><strong>三组会计闭合</strong><span>贡献加总、名义/实际/平减指数恒等式、GDP/GDI均值均通过程序化核验</span></div></article><article><CheckCircle2 size={15} /><div><strong>缺口与不可得项透明</strong><span>{missingCount}条月/季频序列有日历缺口；GDPNow、NY Fed Nowcast及NBER两项未用替代值冒充</span></div></article></div><footer><Info size={14} /><span>{dataset.dataQuality.note} 快照生成 {dataset.generatedAt.slice(0, 10)}；定期更新运行 <code>python scripts/refresh_ifind_us_gdp.py</code>。</span></footer></section>
    <footer className="us-macro-source"><div><strong>数据来源：iFinD经济数据库（EDB）。</strong><span>{dataset.researchBasis[0]} · {dataset.frameworkSource.file}</span></div><button aria-label="返回宏观框架（页尾）" type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button></footer>
  </>
}
