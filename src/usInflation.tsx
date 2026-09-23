import { useMemo, useState } from 'react'
import { ArrowLeft, CheckCircle2, ChevronRight, Info } from 'lucide-react'
import inflationData from './data/usInflationData.json'

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
  frequency: string
  latestValue: number
  latestObservation: string
  defaultActive?: boolean
  dash?: string
  source: SourceMeta
}

type ChartDefinition = {
  id: string
  eyebrow: string
  title: string
  description: string
  unit: string
  reference?: number
  defaultRange: RangeKey
  series: ChartSeries[]
  totalSeries?: ChartSeries
}

type DetailRow = {
  id: string
  label: string
  depth: number
  nature: string
  observation: string
  yoy: number
  yoyChange: number
  mom: number
  source: SourceMeta
}

type CycleRow = {
  id: string
  label: string
  nature: string
  classification: string
  peak: number
  peakDate: string
  latest: number
  latestDate: string
  baseline: number
  annualVolatility: number
  halfLifeYears: number
  wageCorrelation: number
  retrace: number
  code: string
}

type HeatmapRow = {
  id: string
  label: string
  group: string
  depth: number
  weight: number
  yoy: Array<number | null>
  mom: Array<number | null>
  source: { provider: string; code: string }
}

type InflationDataset = {
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
  actual: {
    cpiTrend: ChartDefinition
    pceTrend: ChartDefinition
    coreSplit: ChartDefinition
    cpiContributions: ChartDefinition
    supercoreMom: ChartDefinition
    wageAnchor: ChartDefinition
    cycleStructure: {
      title: string
      description: string
      rows: CycleRow[]
      source: { provider: string; route: string }
    }
    cpiHeatmap: {
      title: string
      description: string
      periods: string[]
      rows: HeatmapRow[]
      source: { provider: string; route: string }
    }
    cpiDetail: {
      title: string
      description: string
      rows: DetailRow[]
      source: { provider: string; route: string }
    }
  }
  survey: {
    expectations: ChartDefinition
  }
  implied: {
    breakeven: ChartDefinition
    latestCurve: Array<{ tenor: string; value: number; observation: string }>
  }
  dataQuality: {
    cpiMissingPeriods: string[]
    note: string
  }
}

const dataset = inflationData as InflationDataset
const RANGE_OPTIONS: Array<{ key: RangeKey; label: string; years: number | null }> = [
  { key: '1Y', label: '1年', years: 1 },
  { key: '3Y', label: '3年', years: 3 },
  { key: '5Y', label: '5年', years: 5 },
  { key: 'ALL', label: '全部', years: null },
]

function formatValue(value: number, digits = 2): string {
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

function formatChartValue(value: number, unit: string): string {
  return `${formatValue(value)}${unit === '%' ? '%' : ` ${unit}`}`
}

function formatDate(date: string): string {
  if (date.length < 6) return date
  return date.length >= 8
    ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
    : `${date.slice(0, 4)}-${date.slice(4, 6)}`
}

function dateToTimestamp(date: string): number {
  const year = Number(date.slice(0, 4))
  const month = Number(date.slice(4, 6)) - 1
  const day = Number(date.slice(6, 8) || '1')
  return Date.UTC(year, month, day)
}

function timestampLabel(timestamp: number): string {
  const date = new Date(timestamp)
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`
}

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function MultiSeriesChart({ chart }: { chart: ChartDefinition }) {
  const width = 920
  const height = 350
  const left = 56
  const right = 22
  const top = 18
  const bottom = 42
  const [range, setRange] = useState<RangeKey>(chart.defaultRange)
  const [active, setActive] = useState<Record<string, boolean>>(
    () => Object.fromEntries(chart.series.map((series) => [series.id, series.defaultActive !== false])),
  )
  const [hoverTimestamp, setHoverTimestamp] = useState<number | null>(null)

  const latestTimestamp = Math.max(...chart.series.flatMap((series) => series.dates.map(dateToTimestamp)))
  const rangeYears = RANGE_OPTIONS.find((option) => option.key === range)?.years ?? null
  const cutoff = rangeYears === null
    ? Number.NEGATIVE_INFINITY
    : latestTimestamp - rangeYears * 365.25 * 24 * 60 * 60 * 1000

  const visible = useMemo(() => chart.series.map((series) => {
    const points = series.dates.map((date, index) => ({
      date,
      timestamp: dateToTimestamp(date),
      value: series.values[index],
    })).filter((point) => point.timestamp >= cutoff)
    return { ...series, points }
  }).filter((series) => active[series.id] && series.points.length > 0), [active, chart.series, cutoff])

  const timestamps = visible.flatMap((series) => series.points.map((point) => point.timestamp))
  const values = visible.flatMap((series) => series.points.map((point) => point.value))
  if (typeof chart.reference === 'number') values.push(chart.reference)
  const minTimestamp = Math.min(...timestamps)
  const maxTimestamp = Math.max(...timestamps)
  const rawMin = Math.min(...values)
  const rawMax = Math.max(...values)
  const padding = Math.max((rawMax - rawMin) * 0.12, 0.2)
  const minValue = rawMin - padding
  const maxValue = rawMax + padding
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const x = (timestamp: number) => left + ((timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1)) * plotWidth
  const y = (value: number) => top + ((maxValue - value) / Math.max(maxValue - minValue, 1)) * plotHeight
  const yTicks = Array.from({ length: 5 }, (_, index) => maxValue - (index / 4) * (maxValue - minValue))
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + (index / 5) * (maxTimestamp - minTimestamp))

  const linePath = (series: typeof visible[number]) => {
    const maxGapDays = series.frequency === '季' ? 130 : 45
    return series.points.map((point, index) => {
      const previous = index > 0 ? series.points[index - 1] : null
      const gapDays = previous ? (point.timestamp - previous.timestamp) / (24 * 60 * 60 * 1000) : 0
      const command = index === 0 || gapDays > maxGapDays ? 'M' : 'L'
      return `${command} ${x(point.timestamp).toFixed(2)} ${y(point.value).toFixed(2)}`
    }).join(' ')
  }

  const hoverRows = hoverTimestamp === null ? [] : visible.map((series) => {
    const point = series.points.reduce((nearest, candidate) => (
      Math.abs(candidate.timestamp - hoverTimestamp) < Math.abs(nearest.timestamp - hoverTimestamp) ? candidate : nearest
    ))
    return { series, point }
  })

  const toggleSeries = (seriesId: string) => {
    setActive((current) => {
      const activeCount = Object.values(current).filter(Boolean).length
      if (current[seriesId] && activeCount === 1) return current
      return { ...current, [seriesId]: !current[seriesId] }
    })
  }

  return (
    <article className="inflation-chart-card">
      <header>
        <div>
          <span>{chart.eyebrow}</span>
          <h3>{chart.title}</h3>
          <p>{chart.description}</p>
        </div>
        <div className="range-switch" role="group" aria-label={`${chart.title}时间范围`}>
          {RANGE_OPTIONS.map((option) => (
            <button
              className={range === option.key ? 'active' : ''}
              key={option.key}
              type="button"
              onClick={() => setRange(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </header>

      <div className="series-switches" role="group" aria-label={`${chart.title}序列开关`}>
        {chart.series.map((series) => (
          <button
            aria-pressed={active[series.id]}
            className={active[series.id] ? 'active' : ''}
            key={series.id}
            type="button"
            onClick={() => toggleSeries(series.id)}
          >
            <i style={{ background: series.color }} />
            <span>{series.label}</span>
            <strong>{formatChartValue(series.latestValue, chart.unit)}</strong>
            <small>{formatDate(series.latestObservation)}</small>
          </button>
        ))}
      </div>

      <div className="multi-chart-wrap">
        <svg
          className="multi-series-svg"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${chart.title}折线图`}
          onPointerLeave={() => setHoverTimestamp(null)}
          onPointerMove={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect()
            const svgX = ((event.clientX - bounds.left) / bounds.width) * width
            const ratio = Math.min(1, Math.max(0, (svgX - left) / plotWidth))
            setHoverTimestamp(minTimestamp + ratio * (maxTimestamp - minTimestamp))
          }}
        >
          {yTicks.map((tick, index) => {
            const tickY = top + (index / 4) * plotHeight
            return (
              <g key={tick}>
                <line x1={left} x2={width - right} y1={tickY} y2={tickY} className="chart-grid-line" />
                <text x={left - 9} y={tickY + 4} textAnchor="end" className="chart-axis-text">
                  {formatValue(tick, 1)}
                </text>
              </g>
            )
          })}
          {xTicks.map((tick) => (
            <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">
              {timestampLabel(tick)}
            </text>
          ))}
          {typeof chart.reference === 'number' && (
            <g>
              <line x1={left} x2={width - right} y1={y(chart.reference)} y2={y(chart.reference)} className="chart-reference-line" />
              <text x={width - right - 4} y={y(chart.reference) - 5} textAnchor="end" className="chart-reference-label">
                {chart.reference}%参照
              </text>
            </g>
          )}
          {visible.map((series) => (
            <path
              key={series.id}
              data-series-id={series.id}
              d={linePath(series)}
              fill="none"
              stroke={series.color}
              strokeWidth="2.3"
              strokeDasharray={series.dash}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}
          {hoverTimestamp !== null && (
            <g className="chart-hover-layer">
              <line x1={x(hoverTimestamp)} x2={x(hoverTimestamp)} y1={top} y2={height - bottom} />
              {hoverRows.map(({ series, point }) => (
                <circle key={series.id} cx={x(point.timestamp)} cy={y(point.value)} r="4" fill={series.color} />
              ))}
            </g>
          )}
        </svg>
      </div>

      <div className="chart-readout" aria-live="polite">
        {hoverRows.length > 0 ? hoverRows.map(({ series, point }) => (
          <span key={series.id}>
            <i style={{ background: series.color }} />
            {series.label}
            <strong>{formatChartValue(point.value, chart.unit)}</strong>
            <small>{formatDate(point.date)}</small>
          </span>
        )) : <span className="chart-readout-hint">移动鼠标读取各序列同一时点附近的数值</span>}
      </div>

      <footer>
        <div className="chart-source-list">
          {chart.series.map((series) => (
            <a href={series.source.url} key={series.id} target="_blank" rel="noreferrer">
              <strong>{series.label}</strong>
              <span>{series.source.provider} · {series.source.code}</span>
            </a>
          ))}
        </div>
      </footer>
    </article>
  )
}

function ContributionChart({ chart }: { chart: ChartDefinition }) {
  const total = chart.totalSeries
  if (!total) return <MultiSeriesChart chart={chart} />
  const width = 920
  const height = 350
  const left = 56
  const right = 22
  const top = 20
  const bottom = 42
  const latest = Math.max(...chart.series.flatMap((item) => item.dates.map(dateToTimestamp)))
  const cutoff = latest - 3 * 365.25 * 24 * 60 * 60 * 1000
  const maps = chart.series.map((item) => new Map(item.dates.map((date, index) => [date, item.values[index]])))
  const totalMap = new Map(total.dates.map((date, index) => [date, total.values[index]]))
  const dates = Array.from(new Set(chart.series.flatMap((item) => item.dates)))
    .filter((date) => dateToTimestamp(date) >= cutoff && maps.every((map) => map.has(date)))
    .sort()
  const rows = dates.map((date) => ({
    date,
    timestamp: dateToTimestamp(date),
    components: maps.map((map) => map.get(date) ?? 0),
    total: totalMap.get(date) ?? null,
  }))
  const extrema = rows.flatMap((row) => {
    const positive = row.components.filter((value) => value > 0).reduce((sum, value) => sum + value, 0)
    const negative = row.components.filter((value) => value < 0).reduce((sum, value) => sum + value, 0)
    return [positive, negative, row.total ?? 0]
  })
  const rawMin = Math.min(...extrema, -0.1)
  const rawMax = Math.max(...extrema, 0.1)
  const padding = Math.max((rawMax - rawMin) * 0.1, 0.08)
  const minValue = rawMin - padding
  const maxValue = rawMax + padding
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const minTimestamp = rows[0]?.timestamp ?? 0
  const maxTimestamp = rows.at(-1)?.timestamp ?? 1
  const x = (timestamp: number) => left + ((timestamp - minTimestamp) / Math.max(maxTimestamp - minTimestamp, 1)) * plotWidth
  const y = (value: number) => top + ((maxValue - value) / Math.max(maxValue - minValue, 1)) * plotHeight
  const barWidth = Math.max(2, Math.min(15, plotWidth / Math.max(rows.length, 1) * 0.68))
  const yTicks = Array.from({ length: 5 }, (_, index) => maxValue - (index / 4) * (maxValue - minValue))
  const xTicks = Array.from({ length: 6 }, (_, index) => minTimestamp + (index / 5) * (maxTimestamp - minTimestamp))
  const totalPath = rows.map((row, index) => {
    if (row.total === null) return ''
    const previous = index > 0 ? rows[index - 1] : null
    const gapDays = previous ? (row.timestamp - previous.timestamp) / (24 * 60 * 60 * 1000) : 0
    return `${index === 0 || previous?.total === null || gapDays > 45 ? 'M' : 'L'} ${x(row.timestamp).toFixed(2)} ${y(row.total).toFixed(2)}`
  }).join(' ')
  return (
    <article className="inflation-chart-card contribution-chart-card">
      <header>
        <div><span>{chart.eyebrow}</span><h3>{chart.title}</h3><p>{chart.description}</p></div>
        <div className="contribution-latest"><strong>{formatValue(total.latestValue)}%</strong><span>{formatDate(total.latestObservation)}</span></div>
      </header>
      <div className="contribution-legend">
        {chart.series.map((item) => <span key={item.id}><i style={{ background: item.color }} />{item.label}</span>)}
        <span><i className="total-line" />CPI环比</span>
      </div>
      <div className="multi-chart-wrap">
        <svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}堆叠柱与折线图`}>
          {yTicks.map((tick, index) => {
            const tickY = top + index / 4 * plotHeight
            return <g key={tick}><line x1={left} x2={width - right} y1={tickY} y2={tickY} className="chart-grid-line" /><text x={left - 9} y={tickY + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick, 1)}</text></g>
          })}
          {xTicks.map((tick) => <text key={tick} x={x(tick)} y={height - 11} textAnchor="middle" className="chart-axis-text">{timestampLabel(tick)}</text>)}
          <line x1={left} x2={width - right} y1={y(0)} y2={y(0)} className="chart-reference-line" />
          {rows.flatMap((row) => {
            let positive = 0
            let negative = 0
            return row.components.map((value, index) => {
              const start = value >= 0 ? positive : negative
              const end = start + value
              if (value >= 0) positive = end
              else negative = end
              return <rect key={`${row.date}-${chart.series[index].id}`} x={x(row.timestamp) - barWidth / 2} y={Math.min(y(start), y(end))} width={barWidth} height={Math.max(1, Math.abs(y(start) - y(end)))} fill={chart.series[index].color} />
            })
          })}
          <path d={totalPath} fill="none" stroke={total.color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <footer><div className="chart-source-list"><span>分项影响值与CPI环比均来自 iFinD EDB；2025-10缺口保持断开。</span></div></footer>
    </article>
  )
}

const NATURE_TONE: Record<string, string> = {
  总量: 'total',
  波动项: 'volatile',
  周期分项: 'cyclical',
  半结构分项: 'semi-structural',
  结构分项: 'structural',
}

function NatureBadge({ nature }: { nature: string }) {
  return <span className={`nature-badge ${NATURE_TONE[nature] ?? 'total'}`}>{nature}</span>
}

function heatCellColor(value: number | null, mode: 'yoy' | 'mom'): string {
  if (value === null) return 'transparent'
  const ceiling = mode === 'yoy' ? 8 : 1.5
  const alpha = Math.min(0.52, 0.06 + Math.abs(value) / ceiling * 0.46)
  return value >= 0 ? `rgba(197, 68, 68, ${alpha})` : `rgba(47, 127, 163, ${alpha})`
}

function CpiHeatmapTable() {
  const table = dataset.actual.cpiHeatmap
  const [mode, setMode] = useState<'yoy' | 'mom'>('yoy')
  return (
    <article className="cpi-heatmap-card">
      <header>
        <div>
          <span>ACTUAL · 23 SUBCOMPONENTS</span>
          <h3>{table.title}</h3>
          <p>{table.description}</p>
        </div>
        <div className="heatmap-mode" role="group" aria-label="CPI分项温度表口径">
          <button className={mode === 'yoy' ? 'active' : ''} type="button" onClick={() => setMode('yoy')}>同比</button>
          <button className={mode === 'mom' ? 'active' : ''} type="button" onClick={() => setMode('mom')}>季调环比</button>
        </div>
      </header>
      <div className="heatmap-legend" aria-hidden="true">
        <span>负增长</span><i className="cool" /><i className="neutral" /><i className="hot" /><span>正增长</span>
      </div>
      <div className="cpi-heatmap-wrap">
        <table className="cpi-heatmap" aria-label={table.title}>
          <thead>
            <tr>
              <th>分项</th>
              <th>组别</th>
              <th>权重 %</th>
              {table.periods.map((period) => <th key={period}>{formatDate(period)}</th>)}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIndex) => {
              const values = mode === 'yoy' ? row.yoy : row.mom
              const startsGroup = rowIndex === 0 || table.rows[rowIndex - 1].group !== row.group
              return (
                <tr className={`${row.depth === 0 ? 'major' : ''} ${startsGroup ? 'group-start' : ''}`} key={row.id}>
                  <th style={{ paddingLeft: `${16 + row.depth * 16}px` }}>{row.label}</th>
                  <td><span className={`heatmap-group group-${row.group}`}>{row.group}</span></td>
                  <td className="heatmap-weight">{formatValue(row.weight)}</td>
                  {values.map((value, index) => (
                    <td className="heat-value" key={`${row.id}-${table.periods[index]}`} style={{ backgroundColor: heatCellColor(value, mode) }}>
                      {value === null ? '—' : formatValue(value, 1)}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <footer>
        <strong>{mode === 'yoy' ? '当月同比' : '季调环比'}</strong>
        <span>月份按从新到旧排列；2025-10为iFinD上游缺口，不做插值，最近12个可用月因此跳过该月。</span>
        <b>{table.source.provider}</b>
      </footer>
    </article>
  )
}

function CycleStructureTable() {
  const table = dataset.actual.cycleStructure
  return (
    <article className="cycle-structure-card">
      <header>
        <div>
          <span>ACTUAL · CYCLE vs STRUCTURE</span>
          <h3>{table.title}</h3>
          <p>{table.description}</p>
        </div>
        <div className="cycle-legend">
          <span><i className="cyclical" />周期分项</span>
          <span><i className="semi-structural" />半结构分项</span>
          <span><i className="structural" />结构分项</span>
        </div>
      </header>
      <div className="cycle-table-wrap">
        <table className="cycle-table" aria-label={table.title}>
          <thead>
            <tr>
              <th>分项</th>
              <th>识别</th>
              <th>年度波动率 σ</th>
              <th>半衰期（年）</th>
              <th>工资相关性</th>
              <th>冲击峰值 %</th>
              <th>最新 %</th>
              <th>2015—19均值</th>
              <th>归位度</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row) => (
              <tr key={row.id}>
                <th>{row.label}</th>
                <td><NatureBadge nature={row.nature} /></td>
                <td className="num">{formatValue(row.annualVolatility, 2)}</td>
                <td className="num">{formatValue(row.halfLifeYears, 2)}</td>
                <td className="num">{formatValue(row.wageCorrelation, 2)}</td>
                <td className="num">{formatValue(row.peak)}<small>{formatDate(row.peakDate).slice(0, 7)}</small></td>
                <td className="num">{formatValue(row.latest)}</td>
                <td className="num">{formatValue(row.baseline, 2)}</td>
                <td className="retrace-cell">
                  <i><b className={NATURE_TONE[row.nature] ?? 'total'} style={{ width: `${row.retrace}%` }} /></i>
                  <strong>{formatValue(row.retrace, 0)}%</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <footer>
        <strong>数据来源：</strong>
        <b>{table.source.provider}</b>
        <span>归位度 =（冲击峰值−最新）/（冲击峰值−2015—2019均值）；半衰期由年度均值AR(1)系数推算。</span>
      </footer>
    </article>
  )
}

function SectionHeading({ code, title, description }: { code: string; title: string; description: string }) {
  return (
    <header className="inflation-section-heading">
      <span>{code}</span>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </header>
  )
}

function LatestCurve() {
  const curve = dataset.implied.latestCurve
  const min = Math.min(...curve.map((point) => point.value))
  const max = Math.max(...curve.map((point) => point.value))
  return (
    <aside className="latest-curve-card">
      <span>TERM STRUCTURE · LATEST</span>
      <h3>最新隐含通胀曲线</h3>
      <p>期限越长，风险溢价与流动性因素的累计影响通常越大，不能把斜率机械解释为纯预期差。</p>
      <div>
        {curve.map((point) => {
          const width = 32 + ((point.value - min) / Math.max(max - min, 0.01)) * 68
          return (
            <article key={point.tenor}>
              <header><strong>{point.tenor}</strong><span>{formatValue(point.value)}%</span></header>
              <i><b style={{ width: `${width}%` }} /></i>
              <small>{formatDate(point.observation)}</small>
            </article>
          )
        })}
      </div>
    </aside>
  )
}

export function UsInflationDetail({ onBack }: { onBack: () => void }) {
  const latestObservation = dataset.headline.reduce(
    (latest, item) => item.observation > latest ? item.observation : latest,
    '',
  )

  return (
    <>
      <div className="page-heading us-macro-heading">
        <div>
          <button className="history-back" type="button" onClick={onBack}>
            <ArrowLeft size={15} />返回宏观框架
          </button>
          <p className="eyebrow">US ECONOMY · IFIND INFLATION MONITOR</p>
          <h1>美国通胀</h1>
          <p>以 iFinD 经济数据库为数据源，分开观察实际通胀分项、调查预期与市场隐含定价。</p>
        </div>
        <div className="as-of"><span>本页最近观测</span><strong>{formatDate(latestObservation)}</strong></div>
      </div>

      <section className="inflation-headline-grid" aria-label="美国通胀状态摘要">
        {dataset.headline.map((item, index) => (
          <article key={item.id}>
            <span>0{index + 1} · {item.label}</span>
            <h2>{item.title}</h2>
            <div><strong>{formatValue(item.value)}</strong><b>{item.unit}</b></div>
            <footer><small>{formatDate(item.observation)}</small><em>{item.source}</em></footer>
          </article>
        ))}
      </section>

      <nav className="inflation-section-nav" aria-label="通胀栏目分区">
        <button type="button" onClick={() => scrollToSection('actual-inflation')}><span>01</span>实际通胀</button>
        <button type="button" onClick={() => scrollToSection('survey-inflation')}><span>02</span>调查通胀</button>
        <button type="button" onClick={() => scrollToSection('implied-inflation')}><span>03</span>市场隐含</button>
        <button type="button" onClick={() => scrollToSection('inflation-method')}><span>04</span>数据口径</button>
      </nav>

      <section className="inflation-section" id="actual-inflation" aria-label="实际通胀">
        <SectionHeading code="01 · ACTUAL INFLATION" title="实际通胀" description="从总量、环比贡献、核心三分项与工资锚逐层拆解，并用23项温度表追踪内部扩散，而不是把总CPI当作单一对象。" />
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.actual.cpiTrend} />
          <MultiSeriesChart chart={dataset.actual.pceTrend} />
        </div>
        <div className="inflation-chart-grid">
          <ContributionChart chart={dataset.actual.cpiContributions} />
          <MultiSeriesChart chart={dataset.actual.supercoreMom} />
        </div>
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.actual.coreSplit} />
          <MultiSeriesChart chart={dataset.actual.wageAnchor} />
        </div>
        <CycleStructureTable />
        <CpiHeatmapTable />
      </section>

      <section className="inflation-section" id="survey-inflation" aria-label="调查通胀">
        <SectionHeading code="02 · SURVEY INFLATION" title="调查与模型预期" description="密歇根大学居民调查对短期价格冲击更敏感；克利夫兰联储模型综合收益率、通胀与调查信息。" />
        <div className="inflation-chart-grid single">
          <MultiSeriesChart chart={dataset.survey.expectations} />
        </div>
      </section>

      <section className="inflation-section" id="implied-inflation" aria-label="市场隐含通胀">
        <SectionHeading code="03 · MARKET IMPLIED" title="市场隐含通胀" description="盈亏平衡通胀率是名义债与TIPS的价差，不是无偏的纯通胀预测；风险与流动性溢价同样会移动曲线。" />
        <div className="implied-layout">
          <MultiSeriesChart chart={dataset.implied.breakeven} />
          <LatestCurve />
        </div>
      </section>

      <section className="inflation-method-card" id="inflation-method" aria-label="通胀数据口径">
        <div>
          <span>04 · DATA CONTRACT</span>
          <h2>iFinD 数据口径</h2>
          <p>每条序列保留自己的观测日期。CPI、PCE、居民/模型调查与盈亏平衡通胀率不共享同一截至日。</p>
        </div>
        <div className="cross-check-list">
          <article>
            <CheckCircle2 size={15} />
            <div>
              <strong>CPI序列缺口检查</strong>
              <span>缺失月份：{dataset.dataQuality.cpiMissingPeriods.length ? dataset.dataQuality.cpiMissingPeriods.map(formatDate).join('、') : '无'}</span>
            </div>
          </article>
          <article>
            <CheckCircle2 size={15} />
            <div>
              <strong>同比与环比分离</strong>
              <span>明细表同比与环比并列，不把环比折年与同比混用</span>
            </div>
          </article>
          <article>
            <CheckCircle2 size={15} />
            <div>
              <strong>单源取数</strong>
              <span>{dataset.dataQuality.note}</span>
            </div>
          </article>
        </div>
        <footer>
          <Info size={14} />
          <span>数据提供方：{dataset.sourceProviders.join(' · ')}；快照生成 {dataset.generatedAt.slice(0, 10)}。</span>
        </footer>
      </section>

      <footer className="us-macro-source">
        <div>
          <strong>数据来源：iFinD 经济数据库（EDB）。</strong>
          <span>{dataset.sourceProviders.join(' · ')}</span>
        </div>
        <button aria-label="返回宏观框架（页尾）" type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button>
      </footer>
    </>
  )
}
