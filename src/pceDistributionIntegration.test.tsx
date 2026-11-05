import { render, screen, within } from '@testing-library/react'
import rawData from './data/usInflationData.json'
import { UsInflationDetail } from './usInflation'
import type { PceDistributionData } from './pceDistribution'

it('在真实通胀页接入真实分布，来源及独立取数时间可追溯', () => {
  const distribution = (rawData as unknown as { actual: { pceDistribution?: PceDistributionData } }).actual.pceDistribution
  expect(distribution).toBeDefined()
  render(<UsInflationDetail onBack={() => undefined} />)
  const chart = screen.getByRole('article', { name: 'PCE分项价格涨幅分布——按消费支出权重加权' })
  expect(within(chart).getByRole('heading', { name: distribution!.title })).toBeInTheDocument()
  expect(within(chart).getByRole('img', { name: /堆叠柱状图/ })).toBeInTheDocument()
  expect(chart).toHaveTextContent('北京时间')
  expect(chart).toHaveTextContent(distribution!.source.provider)
  expect(chart.querySelectorAll('[data-pce-month]')).toHaveLength(distribution!.periods.length)
  expect(within(chart).getByRole('link', { name: '官方分桶数据' })).toHaveAttribute('href', distribution!.source.chartDataUrl)
})
