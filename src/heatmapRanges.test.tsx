import { afterEach, expect, it } from 'vitest'
import type { ComponentProps } from 'react'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { CpiHeatmapTable } from './usInflation'
import { SectorMonitorTable } from './usEmployment'
import inflation from './data/usInflationData.json'
import employment from './data/usEmploymentData.json'

afterEach(cleanup)
const options = ['1年', '3年', '5年', '10年', '20年', '30年', '全部']

it('缺月时不计算不完整区间均值，也不把未核验月份误报为通过', () => {
  const fixture = structuredClone(employment.sections.officialSurveys.sectorMonitor) as unknown as ComponentProps<typeof SectorMonitorTable>['table']
  fixture.history!.rows[0].values[0] = null
  fixture.history!.reconciliation!.checks[0].values[0] = null
  const { container } = render(<SectorMonitorTable table={fixture} />)
  const row = container.querySelector('table')!.tBodies[0].rows[0]
  expect(row.cells[1].textContent).toBe('—')
  expect(row.cells[13].textContent).toBe('—')
  expect(screen.getByRole('status')).toHaveTextContent('未完成全区间核验')
})

it('CPI以连续日历月显示缺口，支持更长区间且同比环比使用同一月份轴', () => {
  const { container } = render(<CpiHeatmapTable />)
  const controls = screen.getByRole('group', { name: 'CPI分项温度表时间范围' })
  expect(within(controls).getAllByRole('button').map(b => b.textContent)).toEqual(options)
  const table = container.querySelector('table')!
  expect(table.tHead!.rows[0].cells.length).toBe(15)
  const firstWindow = inflation.actual.cpiHeatmap.history.periods.slice(0, 12)
  for (const period of firstWindow) expect(table.tHead!.textContent).toContain(`${period.slice(0, 4)}-${period.slice(4)}`)
  for (const [label, count] of [['3年', 36], ['5年', 60], ['10年', 120], ['20年', 240], ['30年', 360], ['全部', inflation.actual.cpiHeatmap.history.periods.length], ['1年', 12]] as const) {
    fireEvent.click(within(controls).getByRole('button', { name: label }))
    expect(table.tHead!.rows[0].cells.length).toBe(count + 3)
  }
  fireEvent.click(within(controls).getByRole('button', { name: '3年' }))
  const headings = table.tHead!.textContent
  fireEvent.click(screen.getByRole('button', { name: '季调环比' }))
  expect(table.tHead!.textContent).toBe(headings)
  const latest = inflation.actual.cpiHeatmap.history.rows[0].mom[0]
  expect(table.tBodies[0].rows[0].cells[3].textContent).toBe(latest === null ? '—' : latest.toFixed(1))
  expect(container.textContent).toContain('权重快照')
})

it.each(['sectorMonitor', 'wageSectorMonitor'] as const)('%s 区间同步切换月份/均值/核验且保留固定比较基准', (name) => {
  const tableData = name === 'sectorMonitor' ? employment.sections.officialSurveys.sectorMonitor : employment.sections.wages.wageSectorMonitor
  const { container } = render(<SectorMonitorTable table={tableData as unknown as ComponentProps<typeof SectorMonitorTable>['table']} />)
  const controls = screen.getByRole('group', { name: `${tableData.title}时间范围` })
  expect(within(controls).getAllByRole('button').map(b => b.textContent)).toEqual(options)
  const table = container.querySelector('table')!
  expect(table.tHead!.rows[0].cells.length).toBe(17)
  const available = tableData.history.periods.length
  for (const [label, count] of [['3年', Math.min(36, available)], ['5年', Math.min(60, available)], ['10年', Math.min(120, available)], ['20年', Math.min(240, available)], ['30年', Math.min(360, available)], ['全部', available], ['1年', 12]] as const) {
    fireEvent.click(within(controls).getByRole('button', { name: label }))
    expect(table.tHead!.rows[0].cells.length).toBe(count + 5)
    if (name === 'sectorMonitor') expect(container.querySelectorAll('.employment-sector-reconciliation thead th')).toHaveLength(count + 2)
  }
  fireEvent.click(within(controls).getByRole('button', { name: '3年' }))
  expect(table.tHead!.textContent).toContain('所选区间月均')
  const first = tableData.history.periods.at(-1)!
  expect(container.textContent).toContain(`${first.slice(0, 4)}-${first.slice(4)}`)
  const mean = tableData.history.rows[0].values.slice(0, 36).reduce((a, b) => a + (b ?? 0), 0) / 36
  expect(Number(table.tBodies[0].rows[0].cells[37].textContent?.replaceAll(',', ''))).toBeCloseTo(mean, name === 'sectorMonitor' ? 1 : 2)
})
