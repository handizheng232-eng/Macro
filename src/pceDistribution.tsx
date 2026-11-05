import { useState } from 'react'
import { MACRO_TIME_RANGE_OPTIONS, type MacroTimeRange } from './macroTimeRange'
import { heatmapPeriodIndices } from './heatmapTimeRange'

export type PceDistributionData = {
  title: string
  description: string
  unit: string
  periods: string[]
  buckets: Array<{ id: string; label: string; color: string; values: Array<number | null> }>
  source: { provider: string; sourceUrl: string; chartDataUrl: string; detailDataUrl: string; fetchedAt: string; latestObservation: string }
  methodology: { rate: string; weight: string; boundaries: string; residual: string; coverage: string }
  quality: { latestComponentCount: number; maximumSumResidual: number; latestBucketMaxDifference: number; latestWeightSum: number; monthlySums: number[] }
  notes: string[]
}

const monthLabel = (period: string | undefined) => period ? `${period.slice(0, 4)}-${period.slice(4, 6)}` : '—'
const percent = (value: number | null | undefined) => value === null || value === undefined ? '—' : `${value.toFixed(2)}%`
const totalWeight = (values: Array<number | null>) => values.length && values.every(v => v !== null && Number.isFinite(v) && v >= 0 && v <= 100)
  ? values.reduce<number>((sum, v) => sum + (v ?? 0), 0) : null

export function PceDistributionChart({ data }: { data: PceDistributionData }) {
  const [range, setRange] = useState<MacroTimeRange>('ALL')
  const [chosenMonth, setChosenMonth] = useState<string | null>(null)
  const [hoverMonth, setHoverMonth] = useState<string | null>(null)
  const indices = heatmapPeriodIndices(data.periods, range)
  const periods = indices.map(index => data.periods[index])
  const selected = [hoverMonth, chosenMonth, periods.at(-1)].find(p => p && periods.includes(p)) ?? ''
  const selectedIndex = data.periods.indexOf(selected)
  const activeValues = data.buckets.map(bucket => bucket.values[selectedIndex] ?? null)
  const total = totalWeight(activeValues)
  const width = Math.max(920, periods.length * 62 + 80)
  const height = 350
  const left = 58, right = 22, top = 24, bottom = 44
  const plotWidth = width - left - right, plotHeight = height - top - bottom
  const step = plotWidth / Math.max(periods.length, 1)
  const y = (value: number) => top + plotHeight * (1 - value / 100)
  const fetchedAt = new Date(data.source.fetchedAt)
  const fetchLabel = Number.isFinite(fetchedAt.getTime()) ? fetchedAt.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '未披露'

  return <article className="inflation-chart-card pce-distribution-card" aria-label={data.title}>
    <header>
      <div><span>ACTUAL · PCE PRICE-CHANGE DISTRIBUTION</span><h3>{data.title}</h3><p>{data.description}</p></div>
      <div className="range-switch" role="group" aria-label="PCE分项价格涨幅分布时间范围">
        {MACRO_TIME_RANGE_OPTIONS.map(option => <button key={option.key} type="button" className={range === option.key ? 'active' : ''} aria-pressed={range === option.key} onClick={() => { setRange(option.key); setChosenMonth(null); setHoverMonth(null) }}>{option.label}</button>)}
      </div>
    </header>
    <div className="contribution-legend">{data.buckets.map(bucket => <span key={bucket.id}><i style={{ background: bucket.color }} />{bucket.label}</span>)}</div>
    <div className="pce-distribution-toolbar">
      <span>纵轴：{data.unit} · 分桶依据：月度环比折年涨幅</span>
      <label>读数月份 <select aria-label="PCE分布读数月份" value={selected} disabled={!periods.length} onChange={event => { setChosenMonth(event.target.value); setHoverMonth(null) }}>{periods.map(period => <option key={period} value={period}>{monthLabel(period)}</option>)}</select></label>
    </div>
    {periods.length ? <div className="multi-chart-wrap pce-chart-scroll">
      <svg className="multi-series-svg" style={{ minWidth: `${Math.max(760, periods.length * 52 + 80)}px` }} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${data.title}堆叠柱状图`}
        onPointerLeave={() => setHoverMonth(null)} onPointerMove={event => {
          const bounds = event.currentTarget.getBoundingClientRect()
          if (bounds.width <= 0) return
          const svgX = (event.clientX - bounds.left) / bounds.width * width
          const index = Math.max(0, Math.min(periods.length - 1, Math.floor((svgX - left) / step)))
          setHoverMonth(periods[index])
        }}>
        {[0, 20, 40, 60, 80, 100].map(tick => <g key={tick}><line x1={left} x2={width - right} y1={y(tick)} y2={y(tick)} className="chart-grid-line" /><text x={left - 9} y={y(tick) + 4} textAnchor="end" className="chart-axis-text">{tick}%</text></g>)}
        {periods.map((period, position) => {
          const sourceIndex = indices[position]
          const values = data.buckets.map(bucket => bucket.values[sourceIndex] ?? null)
          const sum = totalWeight(values)
          const complete = sum !== null && Math.abs(sum - 100) < 1e-6
          const x = left + step * (position + 0.5)
          let accumulated = 0
          return <g key={period} data-pce-month={period}>
            {complete ? data.buckets.map((bucket, index) => {
              const value = values[index] as number
              const before = accumulated
              accumulated += value
              return <rect key={bucket.id} data-bucket={bucket.id} data-value={value} x={x - step * 0.35} y={y(accumulated)} width={step * 0.7} height={y(before) - y(accumulated)} fill={bucket.color}><title>{monthLabel(period)} · {bucket.label} · {percent(value)}</title></rect>
            }) : <text x={x} y={y(50)} textAnchor="middle" className="chart-axis-text">无数据</text>}
            {period === selected && <rect className="pce-selected-month" x={x - step * 0.4} y={top} width={step * 0.8} height={plotHeight} />}
            <text x={x} y={height - 13} textAnchor="middle" className="chart-axis-text">{monthLabel(period)}</text>
          </g>
        })}
      </svg>
    </div> : <p className="chart-method-note">当前区间无可用分布数据</p>}
    <div className="chart-readout pce-distribution-readout" aria-live="polite">
      <span><strong>{monthLabel(selected)}</strong></span>
      {data.buckets.map((bucket, index) => <span key={bucket.id} data-readout-bucket={bucket.id}><i style={{ background: bucket.color }} />{bucket.label}<strong>{percent(activeValues[index])}</strong></span>)}
      <span data-readout-total>{total === null ? '合计未核验' : `合计 ${percent(total)}${Math.abs(total - 100) < 1e-6 ? '' : '（未闭合）'}`}</span>
    </div>
    <div className="pce-distribution-coverage">显示 {monthLabel(periods[0])}—{monthLabel(periods.at(-1))}，{periods.length}个月；当前实得范围 {monthLabel(data.periods[0])}—{monthLabel(data.periods.at(-1))}。更长档位不补造历史；窄屏可横向滑动图表。</div>
    <details className="pce-distribution-details"><summary>查看逐月分布数据</summary><div className="pce-table-scroll"><table aria-label="PCE涨幅分布数据表"><thead><tr><th scope="col">月份</th>{data.buckets.map(bucket => <th scope="col" key={bucket.id}>{bucket.label}</th>)}<th scope="col">合计</th></tr></thead><tbody>{[...periods].reverse().map(period => {
      const index = data.periods.indexOf(period)
      const values = data.buckets.map(bucket => bucket.values[index] ?? null)
      return <tr key={period}><th scope="row">{monthLabel(period)}</th>{values.map((value, i) => <td key={data.buckets[i].id}>{percent(value)}</td>)}<td>{percent(totalWeight(values))}</td></tr>
    })}</tbody></table></div></details>
    <footer>
      <div className="chart-source-list"><a href={data.source.sourceUrl} target="_blank" rel="noreferrer"><strong>{data.source.provider}</strong></a><a href={data.source.chartDataUrl} target="_blank" rel="noreferrer">官方分桶数据</a><a href={data.source.detailDataUrl} target="_blank" rel="noreferrer">当月分项与权重</a></div>
      <p className="chart-method-note">最新观察月：{monthLabel(data.source.latestObservation)}；取得时间：{fetchLabel}（北京时间）。发布时点：通常在BEA月度个人收入与支出发布后更新，以发布机构实际更新为准。</p>
      <details className="pce-distribution-method"><summary>统计口径与核验依据</summary>
        <p className="chart-method-note">{data.methodology.rate}；{data.methodology.weight}；{data.methodology.boundaries}；{data.methodology.residual}。{data.methodology.coverage}</p>
        <p className="chart-method-note">展示值保留两位小数，合计按未舍入权重计算。</p>
        <p className="chart-method-note">{data.notes.join('；')}</p>
      </details>
      <p className="chart-verification">最新期 {data.quality.latestComponentCount} 个分项逐项复核；权重合计 {percent(data.quality.latestWeightSum)}；分桶复算最大差 {data.quality.latestBucketMaxDifference.toExponential(2)} 个百分点。</p>
    </footer>
  </article>
}
