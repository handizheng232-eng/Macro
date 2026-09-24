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

type ChartExplanation = {
  what: string
  howToRead: string
  caveat: string
  pptSlide: string
}

type ChartSeries = {
  id: string
  label: string
  dates: string[]
  values: number[]
  color: string
  unit: string
  frequency: '月' | '周' | '季' | '年'
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
  explanation: ChartExplanation
}

type ScatterPoint = { period: string; x: number; y: number; group?: string }

type ScatterChartDefinition = {
  id: string
  kind: 'scatter'
  eyebrow: string
  title: string
  description: string
  unit: string
  defaultRange: RangeKey
  points: ScatterPoint[]
  xLabel: string
  yLabel: string
  xSource: SourceMeta
  ySource: SourceMeta
  balanceLine?: string
  equalityLine?: boolean
  regression?: { slope: number; intercept: number; excludeGroup?: string }
  explanation: ChartExplanation
}

type ChartDefinition = LineChartDefinition | ScatterChartDefinition

type SectorMonitor = {
  title: string
  description: string
  periods: string[]
  rows: Array<{
    id: string
    label: string
    values: Array<number | null>
    recent12mAverage: number
    baseline2018To2019: number
    source: SourceMeta
  }>
  source: { provider: string; url: string }
}

type AvailabilityItem = {
  id: string
  label: string
  status: 'available' | 'not-integrated'
  explanation: string
}

type Section = {
  title: string
  description: string
  charts: ChartDefinition[]
  sectorMonitor?: SectorMonitor
  availability?: AvailabilityItem[]
}

type EmploymentDataset = {
  schemaVersion: number
  generatedAt: string
  source: string
  sourceProviders: string[]
  frameworkSource: { file: string; slides: string; routeSlide: number }
  routeMap: Array<{
    id: string
    title: string
    subtitle: string
    nodes: Array<{ title: string; detail: string }>
  }>
  dataPassports: Array<{
    id: string
    title: string
    producer: string
    sample: string
    frequency: string
    revision: string
    use: string
    pitfall: string
    pptSlide: string
  }>
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
    officialSurveys: Section
    flows: Section
    wages: Section
    frameworks: Section
    crossChecks: Section
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
          <strong>{chartValue(series.latestValue, series.unit)}</strong>
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

function ExplanationPanel({ explanation }: { explanation: ChartExplanation }) {
  return (
    <div className="employment-explanation">
      <div><span>数据是什么</span><p>{explanation.what}</p></div>
      <div><span>怎么读</span><p>{explanation.howToRead}</p></div>
      <div><span>口径警示</span><p>{explanation.caveat}</p></div>
      <small>{explanation.pptSlide}</small>
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
      const maxGapDays = series.frequency === '周' ? 12 : series.frequency === '季' ? 130 : series.frequency === '年' ? 400 : 45
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
        {hoverRows.length ? hoverRows.map(({ series, point }) => <span key={series.id}><i style={{ background: series.color }} />{series.label}<strong>{chartValue(point.value, series.unit)}</strong><small>{formatDate(point.date)}</small></span>) : <span className="chart-readout-hint">移动鼠标读取各序列同一时点附近的数值</span>}
      </div>
      <footer><SourceList series={chart.series} /></footer>
      <ExplanationPanel explanation={chart.explanation} />
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
      <ExplanationPanel explanation={chart.explanation} />
    </article>
  )
}

function EmploymentScatterChart({ chart }: { chart: ScatterChartDefinition }) {
  const width = 920
  const height = 350
  const left = 62
  const right = 24
  const top = 20
  const bottom = 48
  const points = chart.points
  const rawMinX = Math.min(...points.map((point) => point.x))
  const rawMaxX = Math.max(...points.map((point) => point.x))
  const rawMinY = Math.min(...points.map((point) => point.y))
  const rawMaxY = Math.max(...points.map((point) => point.y))
  const padX = Math.max((rawMaxX - rawMinX) * 0.08, 0.35)
  const padY = Math.max((rawMaxY - rawMinY) * 0.08, 0.35)
  const minX = rawMinX - padX
  const maxX = rawMaxX + padX
  const minY = rawMinY - padY
  const maxY = rawMaxY + padY
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const x = (value: number) => left + (value - minX) / Math.max(maxX - minX, 0.01) * plotWidth
  const y = (value: number) => top + (maxY - value) / Math.max(maxY - minY, 0.01) * plotHeight
  const xTicks = Array.from({ length: 6 }, (_, index) => minX + index / 5 * (maxX - minX))
  const yTicks = Array.from({ length: 5 }, (_, index) => maxY - index / 4 * (maxY - minY))
  const latestPeriod = points.at(-1)?.period ?? ''
  const groupColors: Record<string, string> = {
    history: '#aeb5bd', extreme: '#8a9096', mismatch: '#a56a12',
    'soft-landing': '#c94c4c', current: '#1859b8',
  }
  const groupLabels: Record<string, string> = {
    history: '历史样本', extreme: '2020—21极端值', mismatch: '2020—21疫情错配',
    'soft-landing': '2022—24软着陆', current: '2025年至今',
  }
  const groups = Array.from(new Set(points.map((point) => point.group ?? 'history')))
  const formatPeriod = (period: string) => period.includes('Q') ? period : formatDate(`${period}01`).slice(0, 7)
  const diagonalMin = Math.max(minX, minY)
  const diagonalMax = Math.min(maxX, maxY)
  const regression = chart.regression
  const regressionStart = regression ? { x: minX, y: regression.intercept + regression.slope * minX } : null
  const regressionEnd = regression ? { x: maxX, y: regression.intercept + regression.slope * maxX } : null

  return (
    <article className="employment-chart-card">
      <header>
        <div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div>
        <div className="scatter-latest"><strong>{formatPeriod(latestPeriod)}</strong><span>最新共同观测</span></div>
      </header>
      <div className="beveridge-legend">
        {groups.map((group) => <span key={group}><i style={{ background: groupColors[group] ?? '#718295' }} />{groupLabels[group] ?? group}</span>)}
        {chart.balanceLine && <span><i className="balance" />{chart.balanceLine}</span>}
        {chart.equalityLine && <span><i className="balance" />45度线</span>}
        {regression && <span><i className="regression" />剔除极端值拟合</span>}
      </div>
      <div className="multi-chart-wrap">
        <svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}散点图`}>
          {yTicks.map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" /><text x={left - 9} y={y(tick) + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick, 1)}</text></g>)}
          {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 16} textAnchor="middle" className="chart-axis-text">{formatValue(tick, 1)}</text>)}
          {minX <= 0 && maxX >= 0 && <line x1={x(0)} x2={x(0)} y1={top} y2={height - bottom} className="chart-reference-line" />}
          {minY <= 0 && maxY >= 0 && <line x1={left} x2={width - right} y1={y(0)} y2={y(0)} className="chart-reference-line" />}
          <text x={width / 2} y={height - 2} textAnchor="middle" className="employment-axis-label">{chart.xLabel}</text>
          <text x={14} y={height / 2} textAnchor="middle" className="employment-axis-label" transform={`rotate(-90 14 ${height / 2})`}>{chart.yLabel}</text>
          {(chart.balanceLine || chart.equalityLine) && diagonalMin < diagonalMax && <line x1={x(diagonalMin)} x2={x(diagonalMax)} y1={y(diagonalMin)} y2={y(diagonalMax)} className="scatter-balance-line" />}
          {regressionStart && regressionEnd && <line x1={x(regressionStart.x)} x2={x(regressionEnd.x)} y1={y(regressionStart.y)} y2={y(regressionEnd.y)} className="scatter-regression-line" />}
          {points.map((point) => {
            const latest = point.period === latestPeriod
            const color = groupColors[point.group ?? 'history'] ?? '#718295'
            return <circle key={point.period} cx={x(point.x)} cy={y(point.y)} r={latest ? 5.3 : 3} fill={latest ? '#111418' : color} opacity={latest ? 1 : .7}><title>{`${formatPeriod(point.period)}：${chart.xLabel} ${formatValue(point.x, 2)}；${chart.yLabel} ${formatValue(point.y, 2)}`}</title></circle>
          })}
        </svg>
      </div>
      <footer><div className="chart-source-list"><a href={chart.xSource.url} target="_blank" rel="noreferrer"><strong>横轴</strong><span>iFinD EDB · {chart.xSource.code}</span></a><a href={chart.ySource.url} target="_blank" rel="noreferrer"><strong>纵轴</strong><span>iFinD EDB · {chart.ySource.code}</span></a></div></footer>
      <ExplanationPanel explanation={chart.explanation} />
    </article>
  )
}

function ChartCard({ chart }: { chart: ChartDefinition }) {
  if (chart.kind === 'scatter') return <EmploymentScatterChart chart={chart} />
  if (chart.kind === 'bar') return <EmploymentBarChart chart={chart} />
  return <EmploymentLineChart chart={chart} />
}

function heatColor(value: number | null, maxAbs: number): string {
  if (value === null) return 'transparent'
  const alpha = Math.min(0.54, 0.08 + Math.abs(value) / Math.max(maxAbs, 1) * 0.46)
  return value >= 0 ? `rgba(197,68,68,${alpha})` : `rgba(47,127,163,${alpha})`
}

function SectorMonitorTable({ section }: { section: Section }) {
  const table = section.sectorMonitor!
  const maxAbs = Math.max(...table.rows.flatMap((row) => row.values.filter((value): value is number => value !== null).map(Math.abs)))
  return (
    <article className="employment-heatmap-card">
      <header><div><span>CES · INDUSTRY BREADTH</span><h3>{table.title}</h3><p>{table.description}</p></div><div className="employment-heat-legend"><span>收缩</span><i className="cool" /><i className="neutral" /><i className="hot" /><span>扩张</span></div></header>
      <div className="employment-heatmap-wrap">
        <table className="employment-heatmap sector-monitor-table" aria-label="行业就业广度与结构表">
          <thead><tr><th>行业</th>{table.periods.map((period) => <th key={period}>{formatDate(`${period}01`).slice(0, 7)}</th>)}<th>近12月均值</th><th>2018—19基准</th><th>iFinD指标码</th></tr></thead>
          <tbody>{table.rows.map((row) => <tr key={row.id}><th>{row.label}</th>{row.values.map((value, index) => <td key={`${row.id}-${table.periods[index]}`} style={{ backgroundColor: heatColor(value, maxAbs) }}>{value === null ? '—' : formatValue(value, 0)}</td>)}<td className="sector-benchmark">{formatValue(row.recent12mAverage, 1)}</td><td className="sector-benchmark">{formatValue(row.baseline2018To2019, 1)}</td><td>{row.source.code}</td></tr>)}</tbody>
        </table>
      </div>
      <footer><strong>单位：千人/月</strong><span>同一色阶按全表最大绝对值缩放；基准期与近12个月均为简单月均，不对缺失月份插值。</span><b>{table.source.provider}</b></footer>
    </article>
  )
}

function EmploymentRouteMap() {
  return (
    <section className="employment-route-map" aria-label="就业数据体系路线图">
      <header><div><span>CHAPTER 1 · ROUTE MAP</span><h2>就业市场路线图</h2><p>把PPT第27页的观察路径翻译为五组可更新的数据模块；每个节点均对应页面中的实测序列、口径说明或明确的未接入项。</p></div><aside><strong>{dataset.frameworkSource.slides}</strong><span>{dataset.frameworkSource.file}</span></aside></header>
      <div className="employment-route-core"><span>核心判断</span><strong>就业数量 → 供需松紧 → 工资压力 → 周期框架</strong></div>
      <div className="employment-route-grid">
        {dataset.routeMap.map((branch) => <article key={branch.id}><header><span>{branch.subtitle}</span><h3>{branch.title}路径</h3></header><ol>{branch.nodes.map((node) => <li key={node.title}><strong>{node.title}</strong><span>{node.detail}</span></li>)}</ol></article>)}
      </div>
    </section>
  )
}

function DataPassportTable() {
  return (
    <section className="employment-passports" aria-label="就业数据说明">
      <header><span>DATA PASSPORTS</span><h2>五类数据先分口径，再读方向</h2><p>调查对象、发布时间和修订机制不同，不能把同月数值机械并表。以下说明直接吸收PPT第一章的数据描述。</p></header>
      <div className="employment-passport-wrap">
        <table aria-label="就业数据身份证">
          <thead><tr><th>数据</th><th>调查/生产者</th><th>样本与频率</th><th>修订</th><th>主要用途</th><th>常见误读</th></tr></thead>
          <tbody>{dataset.dataPassports.map((item) => <tr key={item.id}><th><strong>{item.title}</strong><span>{item.pptSlide}</span></th><td>{item.producer}</td><td><strong>{item.sample}</strong><span>{item.frequency}</span></td><td>{item.revision}</td><td>{item.use}</td><td>{item.pitfall}</td></tr>)}</tbody>
        </table>
      </div>
    </section>
  )
}

function AvailabilityPanel({ items }: { items: AvailabilityItem[] }) {
  return (
    <div className="employment-availability" aria-label="第三方调查接入状态">
      {items.map((item) => <article key={item.id}><span>{item.status === 'available' ? 'IFIND' : 'NOT INTEGRATED'}</span><h3>{item.label}</h3><p>{item.explanation}</p></article>)}
    </div>
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
          <p>沿PPT第一章路线图重构：先分清CES与CPS的存量口径，再用申领失业金和JOLTS观察流量，用三类工资指标判断压力，最后落到Okun、失业缺口、贝弗里奇曲线与Sahm规则。</p>
        </div>
        <div className="as-of"><span>本页最近观测</span><strong>{formatDate(latestObservation)}</strong></div>
      </div>

      <section className="employment-headline-grid" aria-label="美国就业状态摘要">
        {dataset.headline.map((item, index) => <article key={item.id}><span>0{index + 1} · {item.label}</span><h2>{item.title}</h2><div><strong>{formatValue(item.value, item.unit === '千人' || item.unit === '万人' ? 0 : 1)}</strong><b>{item.unit}</b></div><footer><small>{formatDate(item.observation)}</small><em>{item.source}</em></footer></article>)}
      </section>

      <EmploymentRouteMap />
      <DataPassportTable />

      <nav className="inflation-section-nav employment-section-nav" aria-label="就业栏目分区">
        <button type="button" onClick={() => scrollToSection('employment-official')}><span>01</span>官方双调查</button>
        <button type="button" onClick={() => scrollToSection('employment-flows')}><span>02</span>流量与周频</button>
        <button type="button" onClick={() => scrollToSection('employment-wages')}><span>03</span>工资口径</button>
        <button type="button" onClick={() => scrollToSection('employment-frameworks')}><span>04</span>实证框架</button>
        <button type="button" onClick={() => scrollToSection('employment-cross-checks')}><span>05</span>第三方验证</button>
      </nav>

      <section className="inflation-section" id="employment-official" aria-label="官方双调查：CES 与 CPS">
        <SectionHeading code="01 · OFFICIAL SURVEYS" section={dataset.sections.officialSurveys} />
        <div className="employment-chart-grid">{dataset.sections.officialSurveys.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
        {dataset.sections.officialSurveys.sectorMonitor && <SectorMonitorTable section={dataset.sections.officialSurveys} />}
      </section>

      <section className="inflation-section" id="employment-flows" aria-label="流量与周频验证">
        <SectionHeading code="02 · FLOWS & WEEKLY CHECK" section={dataset.sections.flows} />
        <div className="employment-chart-grid">{dataset.sections.flows.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
      </section>

      <section className="inflation-section" id="employment-wages" aria-label="工资的三种口径">
        <SectionHeading code="03 · WAGE MEASURES" section={dataset.sections.wages} />
        <div className="employment-chart-grid single">{dataset.sections.wages.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
      </section>

      <section className="inflation-section" id="employment-frameworks" aria-label="四组实证框架">
        <SectionHeading code="04 · EMPIRICAL FRAMEWORKS" section={dataset.sections.frameworks} />
        <div className="employment-chart-grid">{dataset.sections.frameworks.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
      </section>

      <section className="inflation-section" id="employment-cross-checks" aria-label="第三方就业数据验证">
        <SectionHeading code="05 · THIRD-PARTY CROSS-CHECKS" section={dataset.sections.crossChecks} />
        <div className="employment-chart-grid">{dataset.sections.crossChecks.charts.map((item) => <ChartCard chart={item} key={item.id} />)}</div>
        {dataset.sections.crossChecks.availability && <AvailabilityPanel items={dataset.sections.crossChecks.availability} />}
      </section>

      <section className="inflation-method-card employment-method-card" aria-label="就业数据口径">
        <div><span>06 · DATA CONTRACT</span><h2>iFinD 数据口径与可更新性</h2><p>月度就业、周度申领失业金、季度ECI及滞后发布的JOLTS保留各自观测日期，不把不同发布日伪装成同一截至日。</p></div>
        <div className="cross-check-list">
          <article><CheckCircle2 size={15} /><div><strong>源身份与量级核验</strong><span>构建脚本逐条核对iFinD指标码、名称、频率、单位、历史区间与合理量级</span></div></article>
          <article><CheckCircle2 size={15} /><div><strong>缺口与异频处理</strong><span>{disclosedGaps}条月频序列存在至少一个日历月缺口；折线按实际间隔断开，周/月/季不按数组位置拼接</span></div></article>
          <article><CheckCircle2 size={15} /><div><strong>PPT只定义框架</strong><span>页面不沿用截图数值；{dataset.researchBasis[1]}</span></div></article>
        </div>
        <footer><Info size={14} /><span>{dataset.dataQuality.note} 快照生成 {dataset.generatedAt.slice(0, 10)}；定期更新运行 <code>python scripts/refresh_ifind_us_employment.py</code>。</span></footer>
      </section>

      <footer className="us-macro-source">
        <div><strong>数据来源：iFinD 经济数据库（EDB）。</strong><span>{dataset.sourceProviders.join(' · ')} · 框架参考 {dataset.frameworkSource.file} 第{dataset.frameworkSource.slides}页</span></div>
        <button aria-label="返回宏观框架（页尾）" type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button>
      </footer>
    </>
  )
}
