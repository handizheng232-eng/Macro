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
  transformation?: string
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
  displayDateShiftMonths?: number
  observationCoverageEnd?: string
  displayPeriod?: string
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
  formula?: string
  caveat?: string
  availability?: string
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
  framework: {
    title: string
    description: string
    route: Array<{ id: string; label: string; question: string; signals: string[] }>
    attribution: Array<{ id: string; label: string; equation: string; signals: string; reading: string }>
    oilShockFramework: {
      title: string
      evidenceType: string
      pptPages: string
      steps: Array<{ id: string; label: string; question: string; boundary: string }>
    }
    passports: Array<{
      id: string
      name: string
      publisher: string
      frequency: string
      coverage: string
      revision: string
      role: string
      caveat: string
    }>
    indicatorDictionary: Array<{
      id: string
      name: string
      definition: string
      frequency: string
      unit: string
      transformation: string
      interpretation: string
      caveat: string
    }>
  }
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
    goodsServices: ChartDefinition
    shelterLag: ChartDefinition & { availability: string }
    underlying: ChartDefinition & { caveat: string }
    cpiPceGap: ChartDefinition
    januaryEffect: {
      title: string
      description: string
      months: number[]
      unit: string
      series: Array<{ id: string; label: string; values: number[]; color: string }>
      source: { provider: string; code: string }
      caveat: string
    }
    cpiPceWeights: {
      title: string
      description: string
      categories: string[]
      cpi: number[]
      pce: number[]
      unit: string
      asOf: string
      caveat: string
    }
    specialComponents: Array<{ name: string; mechanism: string; use: string }>
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
    divergence: ChartDefinition
    expectations: ChartDefinition
  }
  implied: {
    fiveYearFiveYear: ChartDefinition
    breakeven: ChartDefinition
    latestCurve: Array<{ tenor: string; value: number; observation: string }>
  }
  leading: {
    energyNowcast: ChartDefinition & { formula: string }
    usedCarLead: ChartDefinition & { formula: string }
    goodsPipeline: ChartDefinition & { formula: string }
    toolkit: Array<{ name: string; target: string; lead: string; status: string; note: string }>
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
        {(chart.formula || chart.caveat || chart.availability) && (
          <p className="chart-method-note">{[chart.formula, chart.caveat, chart.availability].filter(Boolean).join('；')}</p>
        )}
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

function InflationFrameworkOverview() {
  const framework = dataset.framework
  return (
    <section className="inflation-framework" id="inflation-framework" aria-label="通胀研究路线图">
      <header>
        <span>RESEARCH ROUTE · PPT CHAPTER 2</span>
        <h2>{framework.title}</h2>
        <p>{framework.description}</p>
      </header>
      <div className="inflation-route-grid">
        {framework.route.map((step, index) => (
          <article key={step.id}>
            <span>{String(index + 1).padStart(2, '0')}</span>
            <h3>{step.label}</h3>
            <p>{step.question}</p>
            <small>{step.signals.join(' · ')}</small>
          </article>
        ))}
      </div>
      <div className="inflation-attribution" aria-label="通胀归因框架">
        <header><strong>需求缺口—供给冲击—预期—政策</strong><span>PPT第63—65页：数据先回答机制变量，再讨论政策含义</span></header>
        <div>
          {framework.attribution.map((item) => (
            <div key={item.id}><span>{item.equation}</span><h3>{item.label}</h3><strong>{item.signals}</strong><p>{item.reading}</p></div>
          ))}
        </div>
      </div>
      <div className="inflation-passport-wrap">
        <table aria-label="CPI与PCE数据身份证" className="inflation-passport-table">
          <thead><tr><th>指标</th><th>发布与频率</th><th>覆盖口径</th><th>修正规则</th><th>研究角色</th><th>主要限制</th></tr></thead>
          <tbody>
            {framework.passports.map((item) => (
              <tr key={item.id}>
                <th>{item.name}</th>
                <td><strong>{item.publisher}</strong><small>{item.frequency}</small></td>
                <td>{item.coverage}</td>
                <td>{item.revision}</td>
                <td>{item.role}</td>
                <td>{item.caveat}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function JanuaryEffectChart() {
  const chart = dataset.actual.januaryEffect
  const width = 920
  const height = 340
  const left = 54
  const right = 20
  const top = 20
  const bottom = 45
  const values = chart.series.flatMap((item) => item.values)
  const minValue = Math.min(0, ...values)
  const maxValue = Math.max(...values) * 1.15
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const groupWidth = plotWidth / chart.months.length
  const barWidth = groupWidth * 0.31
  const y = (value: number) => top + ((maxValue - value) / Math.max(maxValue - minValue, 0.01)) * plotHeight
  const ticks = Array.from({ length: 5 }, (_, index) => maxValue - index / 4 * (maxValue - minValue))
  return (
    <article className="inflation-chart-card january-effect-card">
      <header><div><span>MEASUREMENT · RESIDUAL SEASONALITY</span><h3>{chart.title}</h3><p>{chart.description}</p></div></header>
      <div className="simple-chart-legend">{chart.series.map((item) => <span key={item.id}><i style={{ background: item.color }} />{item.label}</span>)}</div>
      <div className="multi-chart-wrap">
        <svg className="multi-series-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${chart.title}柱状图`}>
          {ticks.map((tick, index) => {
            const tickY = top + index / 4 * plotHeight
            return <g key={tick}><line x1={left} x2={width - right} y1={tickY} y2={tickY} className="chart-grid-line" /><text x={left - 8} y={tickY + 4} textAnchor="end" className="chart-axis-text">{formatValue(tick, 2)}</text></g>
          })}
          {chart.months.map((month, monthIndex) => {
            const center = left + groupWidth * (monthIndex + 0.5)
            return <g key={month}>
              {chart.series.map((item, seriesIndex) => {
                const value = item.values[monthIndex]
                const x = center + (seriesIndex - 0.5) * barWidth
                return <rect key={item.id} x={x - barWidth / 2} y={Math.min(y(0), y(value))} width={barWidth} height={Math.max(1, Math.abs(y(0) - y(value)))} fill={item.color} />
              })}
              <text x={center} y={height - 13} textAnchor="middle" className="chart-axis-text">{month}</text>
            </g>
          })}
        </svg>
      </div>
      <footer><div className="chart-source-list"><span>{chart.unit} · {chart.source.provider} · {chart.source.code}</span><strong>{chart.caveat}</strong></div></footer>
    </article>
  )
}

function WeightComparisonCard() {
  const weights = dataset.actual.cpiPceWeights
  return (
    <article className="inflation-weights-card">
      <header><span>MEASUREMENT · WEIGHTS</span><h3>{weights.title}</h3><p>{weights.description}</p></header>
      <div className="weight-legend"><span><i className="cpi" />CPI</span><span><i className="pce" />PCE</span></div>
      <div className="weight-rows">
        {weights.categories.map((category, index) => (
          <article key={category}>
            <strong>{category}</strong>
            <div><i className="cpi" style={{ width: `${weights.cpi[index] * 2}%` }} /><span>{weights.cpi[index]}%</span></div>
            <div><i className="pce" style={{ width: `${weights.pce[index] * 2}%` }} /><span>{weights.pce[index]}%</span></div>
          </article>
        ))}
      </div>
      <footer><strong>{weights.asOf}</strong><span>{weights.caveat}</span></footer>
    </article>
  )
}

function SpecialComponentsCard() {
  return (
    <article className="special-components-card">
      <header><span>ANATOMY · ALGORITHM FIRST</span><h3>特殊分项：先读算法，再读经济</h3><p>这些分项经常制造单月核心CPI意外；先检查采价和算法，再决定是否上升为宏观趋势。</p></header>
      <div>
        {dataset.actual.specialComponents.map((item) => (
          <article key={item.name}><strong>{item.name}</strong><p>{item.mechanism}</p><small>{item.use}</small></article>
        ))}
      </div>
    </article>
  )
}

function LeadingToolkit() {
  return (
    <article className="leading-toolkit-card">
      <header><span>LEADING · AVAILABILITY</span><h3>发布前工具箱与接入状态</h3><p>“可提前观察”不等于“确定预测”。页面区分直接序列、派生序列、部分映射与暂不可得项。</p></header>
      <div className="leading-toolkit-wrap">
        <table aria-label="通胀发布前工具箱">
          <thead><tr><th>工具</th><th>提前估算</th><th>经验领先</th><th>状态</th><th>说明</th></tr></thead>
          <tbody>{dataset.leading.toolkit.map((item) => <tr key={item.name}><th>{item.name}</th><td>{item.target}</td><td>{item.lead}</td><td><span className={`toolkit-status ${item.status}`}>{item.status}</span></td><td>{item.note}</td></tr>)}</tbody>
        </table>
      </div>
    </article>
  )
}

function OilShockFramework() {
  const framework = dataset.framework.oilShockFramework
  return (
    <article className="oil-shock-card">
      <header><span>SCENARIO · OIL & STAGFLATION</span><h3>{framework.title}</h3><p>{framework.evidenceType} · PPT第{framework.pptPages}页</p></header>
      <div>
        {framework.steps.map((step, index) => (
          <section key={step.id}><span>{String(index + 1).padStart(2, '0')}</span><h4>{step.label}</h4><strong>{step.question}</strong><p>{step.boundary}</p></section>
        ))}
      </div>
      <footer>判断顺序：冲击类型 → 一阶直接效应 → 二阶扩散 → 增长与就业 → 制度缓冲。任何单一步骤都不能单独推出“滞胀”。</footer>
    </article>
  )
}

function IndicatorDictionary() {
  return (
    <article className="inflation-dictionary-card">
      <header><span>DATA · DEFINITIONS</span><h3>通胀指标说明</h3><p>每个指标同时写明频率、单位、转换、研究用途和误读边界，避免同名不同口径。</p></header>
      <div>
        <table aria-label="通胀指标说明">
          <thead><tr><th>指标</th><th>频率</th><th>单位</th><th>转换</th><th>研究用途</th><th>注意事项</th></tr></thead>
          <tbody>{dataset.framework.indicatorDictionary.map((item) => <tr key={item.id}><th>{item.name}</th><td>{item.frequency}</td><td>{item.unit}</td><td>{item.transformation}</td><td>{item.interpretation}</td><td>{item.caveat}</td></tr>)}</tbody>
        </table>
      </div>
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
    <div className="deep-research-page deep-research-page--inflation" role="document" aria-label="美国通胀深度数据页">
      <div className="page-heading us-macro-heading">
        <div>
          <button className="history-back" type="button" onClick={onBack}>
            <ArrowLeft size={15} />返回宏观框架
          </button>
          <p className="eyebrow">US ECONOMY · IFIND INFLATION RESEARCH FRAMEWORK</p>
          <h1>美国通胀</h1>
          <p>按“总量—结构—底层中枢—预期锚—发布前先行”组织，iFinD负责定期刷新，所有派生序列公开公式与限制。</p>
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

      <InflationFrameworkOverview />

      <nav className="inflation-section-nav" aria-label="通胀栏目分区">
        <button type="button" onClick={() => scrollToSection('inflation-framework')}><span>01</span>研究路线</button>
        <button type="button" onClick={() => scrollToSection('actual-inflation')}><span>02</span>实际与结构</button>
        <button type="button" onClick={() => scrollToSection('expectation-inflation')}><span>03</span>预期与锚</button>
        <button type="button" onClick={() => scrollToSection('leading-inflation')}><span>04</span>发布前先行</button>
        <button type="button" onClick={() => scrollToSection('scenario-inflation')}><span>05</span>情景与复盘</button>
        <button type="button" onClick={() => scrollToSection('inflation-method')}><span>06</span>数据说明</button>
      </nav>

      <section className="inflation-section" id="actual-inflation" aria-label="实际通胀">
        <SectionHeading code="02 · ACTUAL & ANATOMY" title="实际通胀与结构拆分" description="先看CPI与PCE总量，再沿6211结构拆到核心商品、住房与超级核心服务；最后用底层分布指标和特殊分项算法核对信号是否广泛。" />
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.actual.cpiTrend} />
          <MultiSeriesChart chart={dataset.actual.pceTrend} />
        </div>
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.actual.goodsServices} />
          <MultiSeriesChart chart={dataset.actual.shelterLag} />
        </div>
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.actual.cpiPceGap} />
          <WeightComparisonCard />
        </div>
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.actual.underlying} />
          <JanuaryEffectChart />
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
        <SpecialComponentsCard />
        <CpiHeatmapTable />
      </section>

      <section className="inflation-section" id="expectation-inflation" aria-label="通胀预期与锚">
        <SectionHeading code="03 · EXPECTATIONS & ANCHOR" title="调查预期与市场锚" description="短期调查容易受汽油价、问法与党派情绪影响；长端市场补偿则混入风险和流动性溢价。判断锚定要看长端对短期冲击的敏感度，而不是要求读数恰好等于2%。" />
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.survey.divergence} />
          <MultiSeriesChart chart={dataset.survey.expectations} />
        </div>
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.implied.fiveYearFiveYear} />
          <MultiSeriesChart chart={dataset.implied.breakeven} />
        </div>
        <LatestCurve />
      </section>

      <section className="inflation-section" id="leading-inflation" aria-label="发布前通胀先行工具">
        <SectionHeading code="04 · LEADING TOOLBOX" title="CPI发布前先算个大概" description="能源和二手车可由更早公布的价格直接或经验映射；供应链压力只提供方向信号。所有领先关系都保留转换公式、原观测日期和可用性限制。" />
        <div className="inflation-chart-grid">
          <MultiSeriesChart chart={dataset.leading.energyNowcast} />
          <MultiSeriesChart chart={dataset.leading.usedCarLead} />
        </div>
        <div className="inflation-chart-grid single">
          <MultiSeriesChart chart={dataset.leading.goodsPipeline} />
        </div>
        <LeadingToolkit />
      </section>

      <section className="inflation-section" id="scenario-inflation" aria-label="通胀情景与历史复盘">
        <SectionHeading code="05 · SCENARIO & REPLAY" title="情景与复盘" description="PPT第85—93页不是把油价上涨机械等同于滞胀，而是依次核对直接价格影响、向核心通胀的二阶扩散、增长与就业损失，以及预期、能源结构、工会和央行信誉等制度缓冲。" />
        <OilShockFramework />
      </section>

      <section className="inflation-method-card" id="inflation-method" aria-label="通胀数据口径">
        <div>
          <span>06 · DATA CONTRACT</span>
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

      <IndicatorDictionary />

      <footer className="us-macro-source">
        <div>
          <strong>数据来源：iFinD 经济数据库（EDB）。</strong>
          <span>{dataset.sourceProviders.join(' · ')}</span>
        </div>
        <button aria-label="返回宏观框架（页尾）" type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button>
      </footer>
    </div>
  )
}
