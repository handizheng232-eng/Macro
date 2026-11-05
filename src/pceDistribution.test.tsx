import { fireEvent, render, screen, within } from '@testing-library/react'
import { PceDistributionChart, type PceDistributionData } from './pceDistribution'

// UI-only fixture; production observations are built from the archived workbooks.
const periods = Array.from({ length: 13 }, (_, index) => {
  const date = new Date(Date.UTC(2025, 8 + index, 1))
  return `${date.getUTCFullYear()}${String(date.getUTCMonth() + 1).padStart(2, '0')}`
})
const fixture: PceDistributionData = {
  title: 'PCE分项价格涨幅分布——按消费支出权重加权', description: '月度环比折年率的分桶，不是同比。',
  unit: '消费支出占比（%）', periods,
  buckets: ['未上涨（≤0%）', '0—2%', '2—3%', '3—5%', '5—10%', '>10%'].map((label, index) => ({
    id: String(index), label, color: ['#aaa', '#1859b8', '#2f7fa3', '#8a9096', '#ba7a2e', '#c94c4c'][index],
    values: periods.map((_, month) => month === 0 ? [40, 10, 10, 10, 10, 20][index] : [20, 10, 10, 20, 20, 20][index]),
  })),
  source: { provider: 'Federal Reserve Bank of Dallas', sourceUrl: 'https://www.dallasfed.org/research/pce', chartDataUrl: 'https://www.dallasfed.org/chart.xlsx', detailDataUrl: 'https://www.dallasfed.org/detail.xlsx', fetchedAt: '2026-11-05T00:00:00+00:00', latestObservation: '202609' },
  methodology: { rate: '月度环比折年', weight: '消费支出权重', boundaries: '右端含边界', residual: '未上涨按100减五桶计算', coverage: '仅官方可下载月份，不造长历史' },
  quality: { latestComponentCount: 177, maximumSumResidual: 0, latestBucketMaxDifference: 0, latestWeightSum: 100, monthlySums: periods.map(() => 100) },
  notes: ['不是分项数量占比'],
}

it('固定0—100%支出权重轴，七档区间实际裁剪月份且保持六桶闭合', () => {
  const { container } = render(<PceDistributionChart data={fixture} />)
  const controls = screen.getByRole('group', { name: 'PCE分项价格涨幅分布时间范围' })
  expect(within(controls).getAllByRole('button').map(b => b.textContent)).toEqual(['1年', '3年', '5年', '10年', '20年', '30年', '全部'])
  expect(container.querySelectorAll('rect[data-bucket]')).toHaveLength(periods.length * 6)
  for (const label of ['1年', '3年', '5年', '10年', '20年', '30年', '全部']) {
    fireEvent.click(within(controls).getByRole('button', { name: label }))
    const count = label === '1年' ? 12 : periods.length
    expect(container.querySelectorAll('[data-pce-month]')).toHaveLength(count)
    expect(screen.getByLabelText('PCE分布读数月份').querySelectorAll('option')).toHaveLength(count)
    for (const month of container.querySelectorAll('[data-pce-month]')) {
      const total = [...month.querySelectorAll('rect[data-bucket]')].reduce((sum, r) => sum + Number(r.getAttribute('data-value')), 0)
      expect(total).toBeCloseTo(100, 8)
    }
  }
  expect(container.textContent).toContain('月度环比折年')
  expect(container.textContent).toContain('不是分项数量占比')
  expect(container.textContent).toContain('右端含边界')
  expect(container.textContent).toContain('合计按未舍入权重计算')
  expect(screen.getByRole('link', { name: '官方分桶数据' })).toHaveAttribute('href', fixture.source.chartDataUrl)
})

it('鼠标、月份选择与数据表读数一致，区间切换后不遗留范围外月份', () => {
  const { container } = render(<PceDistributionChart data={fixture} />)
  fireEvent.change(screen.getByLabelText('PCE分布读数月份'), { target: { value: periods[0] } })
  expect(container.querySelector('.pce-distribution-readout')).toHaveTextContent('2025-09')
  expect(container.querySelector('[data-readout-bucket="0"]')).toHaveTextContent('40.00%')
  const svg = screen.getByRole('img', { name: /PCE分项价格涨幅分布.*堆叠柱状图/ })
  vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({ x: 0, y: 0, left: 0, top: 0, width: 920, height: 350, right: 920, bottom: 350, toJSON: () => ({}) })
  const event = new MouseEvent('pointermove', { bubbles: true, clientX: 880, clientY: 100 })
  fireEvent(svg, event)
  expect(container.querySelector('.pce-distribution-readout')).toHaveTextContent('2026-09')
  expect(container.querySelector('[data-readout-bucket="0"]')).toHaveTextContent('20.00%')
  fireEvent.pointerLeave(svg)
  fireEvent.click(screen.getByRole('button', { name: '1年' }))
  expect(container.querySelector('.pce-distribution-readout')).not.toHaveTextContent('2025-09')
  const table = screen.getByRole('table', { name: 'PCE涨幅分布数据表', hidden: true })
  expect(table.querySelectorAll('tbody tr')).toHaveLength(12)
})

it('缺值不补零、不虚报100%，空历史显示可恢复的无数据状态', () => {
  const data = structuredClone(fixture)
  data.buckets[0].values[data.periods.length - 1] = null
  const { container, rerender } = render(<PceDistributionChart data={data} />)
  expect(container.querySelector('[data-readout-bucket="0"]')).toHaveTextContent('—')
  expect(container.querySelector('[data-readout-total]')).toHaveTextContent('未核验')
  rerender(<PceDistributionChart data={{ ...fixture, periods: [], buckets: fixture.buckets.map(b => ({ ...b, values: [] })) }} />)
  expect(screen.getByText('当前区间无可用分布数据')).toBeInTheDocument()
})
