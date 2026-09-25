import { ArrowLeft, ChevronRight } from 'lucide-react'
import usMacroData from './data/usMacroData.json'
import { US_MACRO_PAGES, type UsMacroCategory, type UsMacroDatasetCategory } from './usMacroConfig'
import { UsEmploymentDetail } from './usEmployment'
import { UsGdpDetail } from './usGdp'
import { UsInflationDetail } from './usInflation'
import { UsConsumptionDetail } from './usConsumption'

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
  categories: Record<UsMacroDatasetCategory, CategoryData>
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

function FrameworkModule({ category }: { category: UsMacroCategory }) {
  const page = US_MACRO_PAGES.find((item) => item.category === category)!
  const sourceMetrics = page.dataCategory ? dataset.categories[page.dataCategory].metrics : []
  const metrics = sourceMetrics.filter((metric) => page.metricIds?.includes(metric.id))
  const providers = [...new Set(metrics.map((metric) => metric.source.provider))]

  return (
    <>
      <section className="module-thesis" aria-label={`${page.label}研究主线`}>
        <div>
          <span>CHAPTER {page.chapter} · RESEARCH QUESTION</span>
          <h2>{page.thesis}</h2>
        </div>
        <p>{page.description}</p>
      </section>

      <section className="module-chain" aria-labelledby="module-chain-title">
        <header>
          <span>CAUSAL CHAIN</span>
          <h2 id="module-chain-title">传导链条</h2>
        </header>
        <div>
          {page.chain.map((step, index) => (
            <div key={step}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              <strong>{step}</strong>
              {index < page.chain.length - 1 && <ChevronRight size={15} aria-hidden="true" />}
            </div>
          ))}
        </div>
      </section>

      <section className="indicator-dictionary" aria-labelledby="indicator-dictionary-title">
        <header>
          <div>
            <span>INDICATOR DICTIONARY</span>
            <h2 id="indicator-dictionary-title">核心指标字典</h2>
          </div>
          <small>框架依据：《美国宏观数据培训【0829定稿】》</small>
        </header>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>指标</th><th>研究角色</th><th>来源</th><th>频率</th><th>首要陷阱</th></tr>
            </thead>
            <tbody>
              {page.indicators.map((indicator) => (
                <tr key={indicator.name}>
                  <th scope="row">{indicator.name}</th>
                  <td>{indicator.role}</td>
                  <td>{indicator.source}</td>
                  <td>{indicator.frequency}</td>
                  <td>{indicator.trap}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {metrics.length > 0 ? (
        <>
          <section className="seasonal-method module-data-method" aria-label="已接入数据说明">
            <div>
              <span>VERIFIED DATA COVERAGE</span>
              <h2>已接入序列</h2>
              <p>仅展示现有构建管线中已核验的真实序列；每张卡片保留独立观测日期、单位、转换和来源，不用框架指标冒充已接入数据。</p>
            </div>
            <div>
              <strong>{metrics.length} / {page.indicators.length}</strong>
              <span>当前图表 / 核心指标组</span>
            </div>
          </section>
          <section className="seasonal-grid" aria-label={`美国${page.label}已接入数据`}>
            {metrics.map((metric) => <MetricCard metric={metric} key={metric.id} />)}
          </section>
        </>
      ) : (
        <section className="module-data-gap" aria-label={`${page.label}数据缺口`}>
          <div>
            <span>DATA GAP · NO SYNTHETIC SERIES</span>
            <h2>尚未接入可核验的{page.label}序列</h2>
            <p>本页先固化研究链条、指标定义、来源与陷阱。取得源数据并完成身份、单位、量级和时间对齐核验后，再生成图表。</p>
          </div>
        </section>
      )}

      <footer className="us-macro-source">
        <div>
          <strong>{metrics.length > 0 ? `数据来源：${providers.join('、')}。` : '数据状态：框架已建立，序列待接入。'}</strong>
          <span>框架来源：美国宏观数据培训【0829定稿】 · 231页</span>
          {metrics.length > 0 && <span>快照生成：{dataset.generatedAt.slice(0, 10)}</span>}
        </div>
      </footer>
    </>
  )
}

export function UsMacroDetail({ category, onBack }: { category: UsMacroCategory; onBack: () => void }) {
  if (category === 'employment') return <UsEmploymentDetail onBack={onBack} />
  if (category === 'inflation') return <UsInflationDetail onBack={onBack} />
  if (category === 'growth') return <UsGdpDetail onBack={onBack} />
  if (category === 'consumption') return <UsConsumptionDetail onBack={onBack} />

  const page = US_MACRO_PAGES.find((item) => item.category === category)!
  const sourceMetrics = page.dataCategory ? dataset.categories[page.dataCategory].metrics : []
  const metrics = sourceMetrics.filter((metric) => page.metricIds?.includes(metric.id))
  const latestDate = metrics.reduce(
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
          <p className="eyebrow">US ECONOMY · CHAPTER {page.chapter}</p>
          <h1>美国{page.label}</h1>
          <p>{page.detail}</p>
        </div>
        <div className="as-of">
          <span>{latestDate ? '本页最近观测' : '数据状态'}</span>
          <strong>{latestDate ? formatDate(latestDate) : '待接入'}</strong>
        </div>
      </div>

      <FrameworkModule category={category} />

      <footer className="module-back-footer">
        <button aria-label="返回宏观框架（页尾）" type="button" onClick={onBack}>返回宏观框架 <ChevronRight size={15} /></button>
      </footer>
    </>
  )
}
