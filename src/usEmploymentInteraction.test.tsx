import { fireEvent, render, screen, within } from '@testing-library/react'
import App from './App'
import employmentData from './data/usEmploymentData.json'

beforeEach(() => {
  window.location.hash = '#framework/us-employment'
})

test('新增非农柱状图显示观测与快照更新时间，并可悬停读取历史月份', () => {
  render(<App />)

  const chartData = employmentData.sections.officialSurveys.charts.find((item) => item.id === 'payroll-momentum')!
  const latestObservation = chartData.series.map((series) => series.latestObservation).sort().at(-1)!
  const formattedLatest = `${latestObservation.slice(0, 4)}-${latestObservation.slice(4, 6)}-${latestObservation.slice(6, 8)}`
  const chart = screen.getByRole('heading', { name: '新增非农：月度增量与3个月均值' }).closest('article')!
  expect(chart).toHaveTextContent(`数据截至：${formattedLatest}`)
  expect(chart).toHaveTextContent(/快照更新：\d{4}-\d{2}-\d{2} \d{2}:\d{2}（北京时间）/)

  const readout = within(chart).getByRole('status', { name: '新增非农图表读数' })
  expect(readout).toHaveTextContent(formattedLatest)
  expect(readout).toHaveTextContent('月度增量')
  expect(readout).toHaveTextContent('3个月均值')

  const svg = within(chart).getByRole('img', { name: '新增非农：月度增量与3个月均值堆叠柱图' })
  Object.defineProperty(svg, 'getBoundingClientRect', {
    configurable: true,
    value: () => ({ left: 0, width: 920, top: 0, height: 350, right: 920, bottom: 350, x: 0, y: 0, toJSON: () => ({}) }),
  })
  fireEvent.pointerMove(svg, { clientX: 58 })
  expect(readout).not.toHaveTextContent(formattedLatest)
})
