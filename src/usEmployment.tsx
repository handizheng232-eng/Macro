import { useMemo, useState } from 'react'
import { ArrowLeft, CheckCircle2, ChevronRight, Info } from 'lucide-react'
import employmentData from './data/usEmploymentData.json'

type RangeKey = '1Y' | '3Y' | '5Y' | 'ALL'

type SourceMeta = {
  provider: string
  institution: string
  code: string
  name: string
  rawUnit: string
  url: string
  latestObservation: string
}

type ChartSeries = {
  id: string
  label: string
  dates: string[]
  values: number[]
  color: string
  frequency: '月' | '周'
  latestValue: number
  latestObservation: string
  transformLabel?: string
  source: SourceMeta
}

type LineChartDefinition = {
  id: string
  kind: 'line' | 'bar'
  eyebrow: string
  title: string
  description: string
  unit: string
  defaultRange: RangeKey
  reference?: number
  separateScale?: boolean
  series: ChartSeries[]
  totalSeries?: ChartSeries
}

type ScatterChartDefinition = {
  id: string
  kind: 'scatter'
  eyebrow: string
  title: string
  description: string
  unit: string
  defaultRange: RangeKey
  points: Array<{ period: string; x: number; y: number }>
  xSource: SourceMeta
  ySource: SourceMeta
}

type ChartDefinition = LineChartDefinition | ScatterChartDefinition

type Section = {
  title: string
  description: string
  charts: ChartDefinition[]
  sectorHeatmap?: {
    title: string
    description: string
    periods: string[]
    rows: Array<{
      id: string
      label: string
      values: Array<number | null>
      source: SourceMeta
    }>
    source: { provider: string; url: string }
  }
}

type EmploymentDataset = {
  schemaVersion: number
  generatedAt: string
  source: string
  sourceProviders: string[]
  headline: Array<{
    id: string
    label: string
    title: string
    value: number
    unit: string
    observation: string
    source: string
  }>
  sections: {
    supply: Section
    slack: Section
    demand: Section
    wages: Section
  }
  dataQuality: {
    monthlyMissingPeriods: Record<string, string[]>
    note: string
  }
  researchBasis: string[]
}

const dataset = employmentData as EmploymentDataset
const RANGE_OPTIONS: Array<{ key: RangeKey; label: string; years: number | null }> = [
  { key: '1Y', label: '1年', years: 1 },
  { key: '3Y', label: '3年', years: 3 },
  { key: '5Y', label: '5年', years: 5 },
  { key: 'ALL', label: '全部', years: null },
]

function formatValue(value: number, digits = 1): string {
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

function formatDate(date: string): string {
  if (date.length < 6) return date
  return date.length >= 8
    ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
    : `${date.slice(0, 4)}-${date.slice(4, 6)}`
}

function dateToTimestamp(date: string): number {
  return Date.UTC(Number(date.slice(0, 4)), Number(date.slice(4, 6)) - 1, Number(date.slice(6, 8) || '1'))
}

function timestampLabel(timestamp: number): string {
  const date = new Date(timestamp)
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`
}

function chartValue(value: number, unit: string): string {
  const digits = Math.abs(value) >= 100 ? 0 : 1
  return `${formatValue(value, digits)}${unit === '%' ? '%' : ` ${unit}`}`
}

function cutoffFor(range: RangeKey, latestTimestamp: number): number {
  const years = RANGE_OPTIONS.find((option) => option.key === range)?.years ?? null
  return years === null
    ? Number.NEGATIVE_INFINITY
    : latestTimestamp - years * 365.25 * 24 * 60 * 60 * 1000
}

function RangeSwitch({ title, value, onChange }: { title: string; value: RangeKey; onChange: (value: RangeKey) => void }) {
  return (
    <div className="range-switch" role="group" aria-label={`${title}时间范围`}>
      {RANGE_OPTIONS.map((option) => (
        <button className={value === option.key ? 'active' : ''} key={option.key} type="button" onClick={() => onChange(option.key)}>
          {option.label}
        </button>
      ))}
    </div>
  )
}

function SeriesSwitches({ chart, active, onToggle }: {
  chart: LineChartDefinition
  active: Record<string, boolean>
  onToggle: (id: string) => void
}) {
  return (
    <div className="series-switches" role="group" aria-label={`${chart.title}序列开关`}>
      {chart.series.map((series) => (
        <button
          aria-pressed={active[series.id]}
          className={active[series.id] ? 'active' : ''}
          key={series.id}
          type="button"
          onClick={() => onToggle(series.id)}
        >
          <i style={{ background: series.color }} />
          <span>{series.label}</span>
          <strong>{chartValue(series.latestValue, chart.unit)}</strong>
          <small>{formatDate(series.latestObservation)}</small>
        </button>
      ))}
    </div>
  )
}

function SourceList({ series }: { series: ChartSeries[] }) {
  return (
    <div className="chart-source-list">
      {series.map((item) => (
        <a href={item.source.url} key={item.id} target="_blank" rel="noreferrer">
          <strong>{item.label}</strong>
          <span>{item.source.provider} · {item.source.code}</span>
        </a>
      ))}
    </div>
  )
}

function EmploymentLineChart({ chart }: { chart: LineChartDefinition }) {
  const width = 920
  const height = 350
  const left = 58
  const right = 24
  const top = 18
  const bottom = 42
  const [range, setRange] = useState<RangeKey>(chart.defaultRange)
  const [active, setActive] = useState<Record<string, boolean>>(
    () => Object.fromEntries(chart.series.map((series) => [series.id, true])),
  )
  const [hoverTimestamp, setHoverTimestamp] = useState<number | null>(null)
  const latestTimestamp = Math.max(...chart.series.flatMap((series) => series.dates.map(dateToTimestamp)))
  const cutoff = cutoffFor(range, latestTimestamp)
  const visible = useMemo(() => chart.series.map((series) => ({
    ...series,
    points: series.dates.map((date, index) => ({ date, timestamp: dateToTimestamp(date), value: series.values[index] }))
      .filter((point) => point.timestamp >= cutoff),
  })).filter((series) => active[series.id]), [active, chart.series, cutoff])
  const timestamps = visible.flatMap((series) => series.points.map((point) => point.timestamp))
  const minTimestamp = Math.min(...timestamps)
  const maxTimestamp = Math.max(...timestamps)
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const x = (timestamp: number) => left + (timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1) * plotWidth
  const allValues = visible.flatMap((series) => series.points.map((point) => point.value))
  if (typeof chart.reference === 'number') allValues.push(chart.reference)
  const sharedMin = Math.min(...allValues)
  const sharedMax = Math.max(...allValues)
  const sharedPadding = Math.max((sharedMax - sharedMin) * 0.12, 0.15)
  const minValue = sharedMin - sharedPadding
  const maxValue = sharedMax + sharedPadding
  const yShared = (value: number) => top + (maxValue - value) / Math.max(maxValue - minValue, 1) * plotHeight
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + index / 5 * (maxTimestamp - minTimestamp))
  const yTicks = Array.from({ length: 5 }, (_, index) => maxValue - index / 4 * (maxValue - minValue))

  const panelScale = (series: typeof visible[number], index: number) => {
    const count = Math.max(visible.length, 1)
    const gap = 18
    const panelHeight = (plotHeight - gap * (count - 1)) / count
    const panelTop = top + index * (panelHeight + gap)
    const values = series.points.map((point) => point.value)
    const rawMin = Math.min(...values)
    const rawMax = Math.max(...values)
    const padding = Math.max((rawMax - rawMin) * 0.15, 0.1)
    return {
      min: rawMin - padding,
      max: rawMax + padding,
      top: panelTop,
      height: panelHeight,
      y: (value: number) => panelTop + (rawMax + padding - value) / Math.max(rawMax - rawMin + padding * 2, 1) * panelHeight,
    }
  }

  const linePath = (series: typeof visible[number], index: number) => {
    const scale = chart.separateScale ? panelScale(series, index) : null
    return series.points.map((point, pointIndex) => {
      const previous = pointIndex ? series.points[pointIndex - 1] : null
      const maxGapDays = series.frequency === '周' ? 12 : 45
      const gapDays = previous ? (point.timestamp - previous.timestamp) / 86_400_000 : 0
      const command = pointIndex === 0 || gapDays > maxGapDays ? 'M' : 'L'
      return `${command} ${x(point.timestamp).toFixed(2)} ${(scale ? scale.y(point.value) : yShared(point.value)).toFixed(2)}`
    }).join(' ')
  }
  const hoverRows = hoverTimestamp === null ? [] : visible.map((series) => ({
    series,
    point: series.points.reduce((nearest, point) => (
      Math.abs(point.timestamp - hoverTimestamp) < Math.abs(nearest.timestamp - hoverTimestamp) ? point : nearest
    )),
  }))
  const toggle = (id: string) => setActive((current) => {
    if (current[id] && Object.values(current).filter(Boolean).length === 1) return current
    return { ...current, [id]: !current[id] }
  })

  return (
    <article className="employment-chart-card">
      <header>
        <div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div>
        <RangeSwitch title={chart.title} value={range} onChange={setRange} />
      </header>
      <SeriesSwitches chart={chart} active={active} onToggle={toggle} />
      <div className="multi-chart-wrap">
        <svg
          className="multi-series-svg"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${chart.title}折线图`}
          onPointerLeave={() => setHoverTimestamp(null)}
          onPointerMove={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect()
            const svgX = (event.clientX - bounds.left) / bounds.width * width
            const ratio = Math.min(1, Math.max(0, (svgX - left) / plotWidth))
            setHoverTimestamp(minTimestamp + ratio * (maxTimestamp - minTimestamp))
          }}
        >
          {chart.separateScale ? visible.map((series, index) => {
            const scale = panelScale(series, index)
            return (
              <g key={`panel-${series.id}`}>
                <rect x={left} y={scale.top} width={plotWidth} height={scale.height} className="employment-panel-bg" />
                <text x={left + 7} y={scale.top + 13} className="employment-panel-label">{series.label}</text>
                <text x={left - 8} y={scale.top + 4} textAnchor="end" className="chart-axis-text">{formatValue(scale.max, 0)}</text>
                <text x={left - 8} y={scale.top + scale.height} textAnchor="end" className="chart-axis-text">{formatValue(scale.min, 0)}</text>
              </g>
            )
          }) : yTicks.map((tick, index) => {
            const tickY = top + index / 4 * plotHeight
            return <g key={tick}><line x1={left} x2={width - right} y1={tickY} y2={tickY} className="chart-grid-line" /><text x={left - 9} y={tickY + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick, 1)}</text></g>
          })}
          {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">{timestampLabel(tick)}</text>)}
          {!chart.separateScale && typeof chart.reference === 'number' && chart.reference >= minValue && chart.reference <= maxValue && (
            <line x1={left} x2={width - right} y1={yShared(chart.reference)} y2={yShared(chart.reference)} className="chart-reference-line" />
          )}
          {visible.map((series, index) => <path key={series.id} data-series-id={series.id} d={linePath(series, index)} fill="none" stroke={series.color} strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />)}
          {hoverTimestamp !== null && <line className="employment-hover-line" x1={x(hoverTimestamp)} x2={x(hoverTimestamp)} y1={top} y2={height - bottom} />}
        </svg>
      </div>
      <div className="chart-readout" aria-live="polite">
        {hoverRows.length ? hoverRows.map(({ series, point }) => <span key={series.id}><i style={{ background: series.color }} />{series.label}<strong>{chartValue(point.value, chart.unit)}</strong><small>{formatDate(point.date)}</small></span>) : <span className="chart-readout-hint">移动鼠标读取各序列同一时点附近的数值</span>}
      </div>
      <footer><SourceList series={chart.series} /></footer>
    </article>
  )
}

function EmploymentBarChart({ chart }: { chart: LineChartDefinition }) {
  const width = 920
  const height = 350
  const left = 58
  const right = 24
  const top = 20
  const bottom = 42
  const [range, setRange] = useState<RangeKey>(chart.defaultRange)
  const latestTimestamp = Math.max(...chart.series.flatMap((series) => series.dates.map(dateToTimestamp)))
  const cutoff = cutoffFor(range, latestTimestamp)
  const maps = chart.series.map((series) => new Map(series.dates.map((date, index) => [date, series.values[index]])))
  const totalMap = new Map((chart.totalSeries?.dates ?? []).map((date, index) => [date, chart.totalSeries?.values[index] ?? 0]))
  const dates = chart.series[0].dates.filter((date) => dateToTimestamp(date) >= cutoff)
  const rows = dates.map((date) => ({
    date,
    timestamp: dateToTimestamp(date),
    values: maps.map((map) => map.get(date) ?? 0),
    total: totalMap.get(date),
  }))
  const extrema = rows.flatMap((row) => {
    const positive = row.values.filter((value) => value > 0).reduce((sum, value) => sum + value, 0)
    const negative = row.values.filter((value) => value < 0).reduce((sum, value) => sum + value, 0)
    return [positive, negative, row.total ?? 0]
  })
  const rawMin = Math.min(...extrema, 0)
  const rawMax = Math.max(...extrema, 0)
  const padding = Math.max((rawMax - rawMin) * 0.1, 20)
  const minValue = rawMin - padding
  const maxValue = rawMax + padding
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const minTimestamp = rows[0]?.timestamp ?? 0
  const maxTimestamp = rows.at(-1)?.timestamp ?? 1
  const x = (timestamp: number) => left + (timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1) * plotWidth
  const y = (value: number) => top + (maxValue - value) / Math.max(maxValue - minValue, 1) * plotHeight
  const barWidth = Math.max(2, Math.min(18, plotWidth / Math.max(rows.length, 1) * 0.72))
  const ticks = Array.from({ length: 5 }, (_, index) => maxValue - index / 4 * (maxValue - minValue))
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + index / 5 * (maxTimestamp - minTimestamp))
  const totalPath = rows.map((row, index) => `${index ? 'L' : 'M'} ${x(row.timestamp).toFixed(2)} ${y(row.total ?? 0).toFixed(2)}`).join(' ')

  return (
    <article className="employment-chart-card employment-bar-card">
      <header>
        <div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div>
        <RangeSwitch title={chart.title} value={range} onChange={setRange} />
      </header>
      <div className="employment-bar-legend">
        {chart.series.map((series) => <span key={series.id}><i style={{ background: series.color }} />{series.label}</span>)}
        {chart.totalSeries && <span><i className="employment-total-line" />{chart.totalSeries.label}</span>}
      </div>
      <div className="multi-chart-wrap">
        <svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}堆叠柱图`}>
          {ticks.map((tick, index) => {
            const tickY = top + index / 4 * plotHeight
            return <g key={tick}><line x1={left} x2={width - right} y1={tickY} y2={tickY} className="chart-grid-line" /><text x={left - 9} y={tickY + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick, 0)}</text></g>
          })}
          {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">{timestampLabel(tick)}</text>)}
          <line x1={left} x2={width - right} y1={y(0)} y2={y(0)} className="chart-reference-line" />
          {rows.flatMap((row) => {
            let positive = 0
            let negative = 0
            return row.values.map((value, index) => {
              const start = value >= 0 ? positive : negative
              const end = start + value
              if (value >= 0) positive = end
              else negative = end
              return <rect key={`${row.date}-${chart.series[index].id}`} x={x(row.timestamp) - barWidth / 2} y={Math.min(y(start), y(end))} width={barWidth} height={Math.max(1, Math.abs(y(start) - y(end)))} fill={chart.series[index].color} />
            })
          })}
          {chart.totalSeries && <path d={totalPath} fill="none" stroke={chart.totalSeries.color} strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" />}
        </svg>
      </div>
      <footer><SourceList series={[...chart.series, ...(chart.totalSeries ? [chart.totalSeries] : [])]} /></footer>
    </article>
  )
}

function BeveridgeChart({ chart }: { chart: ScatterChartDefinition }) {
  const width = 920
  const height = 350
  const left = 58
  const right = 24
  const top = 20
  const bottom = 43
  const points = chart.points
  const minX = Math.min(...points.map((point) => point.x)) - 0.4
  const maxX = Math.max(...points.map((point) => point.x)) + 0.4
  const minY = Math.min(...points.map((point) => point.y)) - 0.4
  const maxY = Math.max(...points.map((point) => point.y)) + 0.4
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const x = (value: number) => left + (value - minX) / (maxX - minX) * plotWidth
  const y = (value: number) => top + (maxY - value) / (maxY - minY) * plotHeight
  const xTicks = Array.from({ length: 6 }, (_, index) => minX + index / 5 * (maxX - minX))
  const yTicks = Array.from({ length: 5 }, (_, index) => maxY - index / 4 * (maxY - minY))
  const latestPeriod = points.at(-1)?.period ?? ''
  const recentCutoff = String(Number(latestPeriod.slice(0, 4)) - 2)

  return (
    <article className="employment-chart-card">
      <header><div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div><div className="scatter-latest"><strong>{formatDate(`${latestPeriod}01`).slice(0, 7)}</strong><span>最新共同月份</span></div></header>
      <div className="beveridge-legend"><span><i className="history" />历史样本</span><span><i className="recent" />近三年</span><span><i className="latest" />最新</span></div>
      <div className="multi-chart-wrap">
        <svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}散点图`}>
          {yTicks.map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" /><text x={left - 9} y={y(tick) + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick, 1)}</text></g>)}
          {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 15} textAnchor="middle" className="chart-axis-text">{formatValue(tick, 1)}</text>)}
          <text x={width / 2} y={height - 2} textAnchor="middle" className="employment-axis-label">U3失业率（%）</text>
          <text x={13} y={height / 2} textAnchor="middle" className="employment-axis-label" transform={`rotate(-90 13 ${height / 2})`}>职位空缺率（%）</text>
          <path d={points.map((point, index) => `${index ? 'L' : 'M'} ${x(point.x).toFixed(2)} ${y(point.y).toFixed(2)}`).join(' ')} fill="none" stroke="#b7bec6" strokeWidth="1" opacity=".65" />
          {points.map((point) => {
            const latest = point.period === latestPeriod
            const recent = point.period.slice(0, 4) >= recentCutoff
            return <circle key={point.period} cx={x(point.x)} cy={y(point.y)} r={latest ? 5.3 : recent ? 3.3 : 2.2} fill={latest ? '#c94c4c' : recent ? '#1859b8' : '#aeb5bd'} opacity={latest ? 1 : recent ? .78 : .42}><title>{`${formatDate(`${point.period}01`).slice(0, 7)}：U3 ${point.x}%，空缺率 ${point.y}%`}</title></circle>
          })}
        </svg>
      </div>
      <footer><div className="chart-source-list"><a href={chart.xSource.url} target="_blank" rel="noreferrer"><strong>横轴U3</strong><span>iFinD EDB · {chart.xSource.code}</span></a><a href={chart.ySource.url} target="_blank" rel="noreferrer"><strong>纵轴空缺率</strong><span>iFinD EDB · {chart.ySource.code}</span></a></div></footer>
    </article>
  )
}

function ChartCard({ chart }: { chart: ChartDefinition }) {
  if (chart.kind === 'scatter') return <BeveridgeChart chart={chart} />
  if (chart.kind === 'bar') return <EmploymentBarChart chart={chart} />
  return <EmploymentLineChart chart={chart} />
}

function heatColor(value: number | null, maxAbs: number): string {
  if (value === null) return 'transparent'
  const alpha = Math.min(0.54, 0.08 + Math.abs(value) / Math.max(maxAbs, 1) * 0.46)
  return value >= 0 ? `rgba(197,68,68,${alpha})` : `rgba(47,127,163,${alpha})`
}

function SectorHeatmap({ section }: { section: Section }) {
  const table = section.sectorHeatmap!
  const maxAbs = Math.max(...table.rows.flatMap((row) => row.values.filter((value): value is number => value !== null).map(Math.abs)))
  return (
    <article className="employment-heatmap-card">
      <header><div><span>DEMAND · INDUSTRY BREADTH</span><h3>{table.title}</h3><p>{table.description}</p></div><div className="employment-heat-legend"><span>收缩</span><i className="cool" /><i className="neutral" /><i className="hot" /><span>扩张</span></div></header>
      <div className="employment-heatmap-wrap">
        <table className="employment-heatmap" aria-label={table.title}>
          <thead><tr><th>行业</th>{table.periods.map((period) => <th key={period}>{formatDate(`${period}01`).slice(0, 7)}</th>)}<th>iFinD指标码</th></tr></thead>
          <tbody>{table.rows.map((row) => <tr key={row.id}><th>{row.label}</th>{row.values.map((value, index) => <td key={`${row.id}-${table.periods[index]}`} style={{ backgroundColor: heatColor(value, maxAbs) }}>{value === null ? '—' : formatValue(value, 0)}</td>)}<td>{row.source.code}</td></tr>)}</tbody>
        </table>
      </div>
      <footer><strong>单位：千人</strong><span>同一色阶按全表最大绝对值缩放，不对缺失月份插值。</span><b>{table.source.provider}</b></footer>
    </article>
  )
}

function SectionHeading({ code, section }: { code: string; section: Section }) {
  return <header className="inflation-section-heading"><span>{code}</span><div><h2>{section.title}</h2><p>{section.description}</p></div></header>
}

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export function UsEmploymentDetail({ onBack }: { onBack: () => void }) {
  const latestObservation = dataset.headline.reduce((latest, item) => item.observation > latest ? item.observation : latest, '')
  const disclosedGaps = Object.values(dataset.dataQuality.monthlyMissingPeriods).filter((items) => items.length).length

  return (
    <>
      <div className="page-heading us-macro-heading">
        <div>
          <button className="history-back" type="button" onClick={onBack}><ArrowLeft size={15} />返回宏观框架</button>
          <p className="eyebrow">US ECONOMY · IFIND EMPLOYMENT MONITOR</p>
          <h1>美国就业</h1>
          <p>从劳动力供给、失业松弛、企业需求到工资工时建立闭环；所有时序数据均由 iFinD 经济数据库重取。</p>
        </div>
        <div className="as-of"><span>本页最近观测</span><strong>{formatDate(latestObservation)}</strong></div>
      </div>

      <section className="employment-headline-grid" aria-label="美国就业状态摘要">
        {dataset.headline.map((item, index) => <article key={item.id}><span>0{index + 1} · {item.label}</span><h2>{item.title}</h2><div><strong>{formatValue(item.value, item.unit === '千人' ? 0 : 1)}</strong><b>{item.unit}</b></div><footer><small>{formatDate(item.observation)}</small><em>{item.source}</em></footer></article>)}
      </section>

      <nav className="inflation-section-nav" aria-label="就业栏目分区">
        <button type="button" onClick={() => scrollToSection('employment-supply')}><span>01</span>劳动力供给</button>
        <button type="button" onClick={() => scrollToSection('employment-slack')}><span>02</span>失业与松弛</button>
        <button type="button" onClick={() => scrollToSection('employment-demand')}><span>03</span>劳动力需求</button>
        <button type="button" onClick={() => scrollToSection('employment-wages')}><span>04</span>工资与工时</button>
      </nav>

      <section className="inflation-section" id="employment-supply" aria-label="劳动力供给">
        <SectionHeading code="01 · LABOR SUPPLY" section={dataset.sections.supply} />
        <div className="employment-chart-grid single">{dataset.sections.supply.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
      </section>

      <section className="inflation-section" id="employment-slack" aria-label="失业与松弛">
        <SectionHeading code="02 · LABOR SLACK" section={dataset.sections.slack} />
        <div className="employment-chart-grid">{dataset.sections.slack.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
      </section>

      <section className="inflation-section" id="employment-demand" aria-label="劳动力需求">
        <SectionHeading code="03 · LABOR DEMAND" section={dataset.sections.demand} />
        <div className="employment-chart-grid">{dataset.sections.demand.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
        <SectorHeatmap section={dataset.sections.demand} />
      </section>

      <section className="inflation-section" id="employment-wages" aria-label="工资与工时">
        <SectionHeading code="04 · WAGES & HOURS" section={dataset.sections.wages} />
        <div className="employment-chart-grid">{dataset.sections.wages.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
      </section>

      <section className="inflation-method-card employment-method-card" aria-label="就业数据口径">
        <div><span>05 · DATA CONTRACT</span><h2>iFinD 数据口径</h2><p>月度就业、周度申领失业金与滞后发布的JOLTS保留各自观测日期，不把不同发布日伪装成同一截至日。</p></div>
        <div className="cross-check-list">
          <article><CheckCircle2 size={15} /><div><strong>单源身份核验</strong><span>构建脚本逐条核对iFinD指标码、名称、频率、单位与量级</span></div></article>
          <article><CheckCircle2 size={15} /><div><strong>月度缺口披露</strong><span>{disclosedGaps}条序列存在至少一个日历月缺口，折线按实际间隔断开</span></div></article>
          <article><CheckCircle2 size={15} /><div><strong>研报仅作框架参考</strong><span>页面数值不沿用研报截图；{dataset.researchBasis[1]}</span></div></article>
        </div>
        <footer><Info size={14} /><span>{dataset.dataQuality.note} 快照生成 {dataset.generatedAt.slice(0, 10)}。</span></footer>
      </section>

      <footer className="us-macro-source">
        <div><strong>数据来源：iFinD 经济数据库（EDB）。</strong><span>{dataset.sourceProviders.join(' · ')}</span></div>
        <button aria-label="返回宏观框架（页尾）" type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button>
      </footer>
    </>
  )
}
