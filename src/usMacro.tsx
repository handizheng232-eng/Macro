import { ArrowLeft, ChevronRight } from 'lucide-react'
import usMacroData from './data/usMacroData.json'
import { US_MACRO_PAGES, type UsMacroCategory } from './usMacroConfig'
import { UsInflationDetail } from './usInflation'

type SeasonalLine = {
  year: number
  values: Array<number | null>
}

type Metric = {
  id: string
  title: string
  displayUnit: string
  decimals: number
  frequency: '月' | '季'
  latestObservation: string
  latestValue: number
  seasonal: SeasonalLine[]
  reference?: number
  transformLabel?: string
  verification?: {
    benchmark: string
    period: string
    difference: number
    unit: string
    status: 'pass' | 'review'
  }
  source: {
    provider: string
    code: string
    name: string
    institution: string | null
    rawUnit: string
    updateDate: string | null
  }
}

type CategoryData = {
  title: string
  description: string
  metrics: Metric[]
}

type MacroDataset = {
  generatedAt: string
  source: string
  sourceProviders?: string[]
  seasonalStartYear: number
  categories: Record<UsMacroCategory, CategoryData>
}

const dataset = usMacroData as MacroDataset

const YEAR_COLORS = ['#9b7653', '#855c9c', '#6f7a84', '#2f8a7a', '#1859b8']
const MONTH_LABELS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
const QUARTER_LABELS = ['Q1', 'Q2', 'Q3', 'Q4']

function linePath(
  values: Array<number | null>,
  min: number,
  max: number,
  width: number,
  height: number,
  left: number,
  top: number,
): string {
  const plotWidth = width - left - 24
  const plotHeight = height - top - 32
  const denominator = Math.max(values.length - 1, 1)
  let path = ''
  let drawing = false
  values.forEach((value, index) => {
    if (value === null) {
      drawing = false
      return
    }
    const x = left + (index / denominator) * plotWidth
    const y = top + ((max - value) / (max - min || 1)) * plotHeight
    path += `${drawing ? ' L' : ' M'} ${x.toFixed(2)} ${y.toFixed(2)}`
    drawing = true
  })
  return path.trim()
}

function formatValue(value: number, decimals: number): string {
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

function formatDate(date: string): string {
  return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
}

function SeasonalChart({ metric }: { metric: Metric }) {
  const width = 680
  const height = 320
  const left = 52
  const top = 18
  const values = metric.seasonal.flatMap((line) => line.values).filter((value): value is number => value !== null)
  if (typeof metric.reference === 'number') values.push(metric.reference)
  const rawMin = Math.min(...values)
  const rawMax = Math.max(...values)
  const padding = Math.max((rawMax - rawMin) * 0.12, Math.abs(rawMax || 1) * 0.02, 0.25)
  const min = rawMin - padding
  const max = rawMax + padding
  const plotWidth = width - left - 24
  const plotHeight = height - top - 32
  const labels = metric.frequency === '季' ? QUARTER_LABELS : MONTH_LABELS
  const yTicks = Array.from({ length: 5 }, (_, index) => max - (index / 4) * (max - min))
  const latestYear = Math.max(...metric.seasonal.map((line) => line.year))

  return (
    <svg
      className="seasonal-svg"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${metric.title}季节图`}
    >
      {yTicks.map((tick, index) => {
        const y = top + (index / 4) * plotHeight
        return (
          <g key={tick}>
            <line x1={left} x2={width - 24} y1={y} y2={y} className="chart-grid-line" />
            <text x={left - 8} y={y + 4} textAnchor="end" className="chart-axis-text">
              {formatValue(tick, metric.decimals)}
            </text>
          </g>
        )
      })}
      {labels.map((label, index) => {
        const x = left + (index / Math.max(labels.length - 1, 1)) * plotWidth
        return <text key={label} x={x} y={height - 8} textAnchor="middle" className="chart-axis-text">{label}</text>
      })}
      {typeof metric.reference === 'number' && metric.reference >= min && metric.reference <= max && (
        <line
          x1={left}
          x2={width - 24}
          y1={top + ((max - metric.reference) / (max - min || 1)) * plotHeight}
          y2={top + ((max - metric.reference) / (max - min || 1)) * plotHeight}
          className="chart-reference-line"
        />
      )}
      {metric.seasonal.map((line, index) => {
        const color = YEAR_COLORS[Math.max(0, YEAR_COLORS.length - metric.seasonal.length + index)]
        return (
          <g key={line.year}>
            <path
              d={linePath(line.values, min, max, width, height, left, top)}
              fill="none"
              stroke={color}
              strokeWidth={line.year === latestYear ? 3 : 1.7}
              strokeDasharray={line.year === latestYear ? undefined : ['8 5', '3 4', undefined, '10 4 2 4'][index]}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={line.year === latestYear ? 1 : 0.8}
            />
            {line.year === latestYear && line.values.map((value, pointIndex) => {
              if (value === null) return null
              const x = left + (pointIndex / Math.max(line.values.length - 1, 1)) * plotWidth
              const y = top + ((max - value) / (max - min || 1)) * plotHeight
              return (
                <circle key={`${line.year}-${pointIndex}`} cx={x} cy={y} r="3.5" fill={color}>
                  <title>{`${line.year} ${labels[pointIndex]}：${formatValue(value, metric.decimals)} ${metric.displayUnit}`}</title>
                </circle>
              )
            })}
          </g>
        )
      })}
    </svg>
  )
}

function MetricCard({ metric }: { metric: Metric }) {
  const latestYear = Math.max(...metric.seasonal.map((line) => line.year))
  return (
    <article className="seasonal-card">
      <header>
        <div>
          <span>{metric.frequency === '季' ? 'QUARTERLY SEASONAL' : 'MONTHLY SEASONAL'}</span>
          <h2>{metric.title}</h2>
        </div>
        <div className="metric-latest">
          <strong>{formatValue(metric.latestValue, metric.decimals)}</strong>
          <span>{metric.displayUnit}</span>
          <small>{formatDate(metric.latestObservation)}</small>
        </div>
      </header>
      <div className="chart-legend" aria-label="图例">
        {metric.seasonal.map((line, index) => (
          <span key={line.year} className={line.year === latestYear ? 'current' : ''}>
            <i style={{ background: YEAR_COLORS[Math.max(0, YEAR_COLORS.length - metric.seasonal.length + index)] }} />
            {line.year}
          </span>
        ))}
      </div>
      <SeasonalChart metric={metric} />
      <footer>
        <div className="metric-source">
          <span>{metric.source.provider}</span>
          <strong>{metric.source.institution || '来源机构未提供'}</strong>
          <small>{metric.source.code}</small>
          {metric.verification && (
            <em className={metric.verification.status}>
              与 {metric.verification.benchmark} 同期核验（{metric.verification.period}）：
              差 {metric.verification.difference >= 0 ? '+' : ''}{formatValue(metric.verification.difference, 2)} {metric.verification.unit}
            </em>
          )}
        </div>
        <p>{metric.transformLabel || `原始口径：${metric.source.rawUnit}`}</p>
      </footer>
    </article>
  )
}

export function UsMacroDetail({ category, onBack }: { category: UsMacroCategory; onBack: () => void }) {
  if (category === 'inflation') return <UsInflationDetail onBack={onBack} />

  const page = US_MACRO_PAGES.find((item) => item.category === category)!
  const categoryData = dataset.categories[category]
  const latestDate = categoryData.metrics.reduce(
    (latest, metric) => metric.latestObservation > latest ? metric.latestObservation : latest,
    '',
  )

  return (
    <>
      <div className="page-heading us-macro-heading">
        <div>
          <button className="history-back" type="button" onClick={onBack}>
            <ArrowLeft size={15} />返回宏观框架
          </button>
          <p className="eyebrow">US ECONOMY · {page.label.toUpperCase()} · SEASONAL</p>
          <h1>{categoryData.title}</h1>
          <p>{categoryData.description}</p>
        </div>
        <div className="as-of"><span>本页最近观测</span><strong>{formatDate(latestDate)}</strong></div>
      </div>

      <section className="seasonal-method" aria-label="季节图说明">
        <div>
          <span>READING GUIDE</span>
          <h2>同月或同季度跨年比较</h2>
          <p>每条线代表一个自然年；当前年度为蓝色粗线，空白表示尚未公布。各卡片保留独立观测日期，不假设数据同步发布。</p>
        </div>
        <div>
          <strong>{dataset.seasonalStartYear}—{new Date(dataset.generatedAt).getUTCFullYear()}</strong>
          <span>季节图覆盖年份</span>
        </div>
      </section>

      <section className="seasonal-grid" aria-label={`${categoryData.title}季节图`}>
        {categoryData.metrics.map((metric) => <MetricCard metric={metric} key={metric.id} />)}
      </section>

      <footer className="us-macro-source">
        <div>
          <strong>数据来源：OpenBB 与 Wind EDB。</strong>
          <span>{dataset.sourceProviders?.join(' · ')}</span>
          <span>快照生成：{dataset.generatedAt.slice(0, 10)}</span>
        </div>
        <button aria-label="返回宏观框架（页尾）" type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button>
      </footer>
    </>
  )
}
