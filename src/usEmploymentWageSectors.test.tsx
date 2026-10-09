import { render, screen, within } from '@testing-library/react'
import App from './App'

beforeEach(() => {
  window.location.hash = '#framework/us-employment'
})

test('工资板块展示分行业平均时薪环比热力表', () => {
  render(<App />)

  const table = screen.getByRole('table', { name: '分行业时薪环比变化表' })
  expect(within(table).getAllByRole('row')).toHaveLength(10)
  expect(within(table).getByRole('columnheader', { name: '近12月平均环比' })).toBeInTheDocument()
  expect(within(table).getByRole('columnheader', { name: '2018—19月均环比' })).toBeInTheDocument()
  expect(within(table).getByRole('rowheader', { name: '建筑业' })).toBeInTheDocument()
  expect(within(table).getByRole('rowheader', { name: '制造业' })).toBeInTheDocument()
  expect(within(table).getByRole('rowheader', { name: '教育与医疗服务' })).toBeInTheDocument()
  expect(within(table).getAllByText(/^CES\d{10}$/)).toHaveLength(9)
  expect(screen.getAllByText(/BLS Public Data API/).length).toBeGreaterThan(0)
})
