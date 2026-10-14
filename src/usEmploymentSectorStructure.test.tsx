import { afterEach, expect, it } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import { SectorMonitorTable } from './usEmployment'

// Synthetic numbers are isolated UI fixtures, never research data.
const source = { provider: 'test fixture', institution: 'test', code: 'TEST', name: 'test', rawUnit: '千人', url: 'https://example.org', latestObservation: '20260930' }
const row = (id: string, label: string, parentId: string | null, depth: number, rowType: 'total' | 'subtotal' | 'detail', value: number) => ({ id, label, parentId, depth, rowType, values: [value], recent12mAverage: value, baseline2018To2019: null, source })
const table = {
  title: '行业就业广度与结构', description: '私营与政府分别列示', periods: ['202609'], decimals: 1,
  rows: [row('total', '非农总计', null, 0, 'total', 120), row('private', '私营部门合计', 'total', 1, 'subtotal', 100), row('retail', '零售业', 'private', 2, 'detail', 100), row('government', '政府部门合计', 'total', 1, 'subtotal', 20), row('federal', '联邦政府', 'government', 2, 'detail', 20)],
  source: { provider: 'test fixture', url: 'https://example.org' },
  reconciliation: { note: '按父子层级核验，不重复加总。', checks: [{ id: 'total', label: '私营+政府−非农', values: [0], tolerance: 0.1 }] },
}
afterEach(cleanup)

it('行业表显示父子层级、汇总行及独立的逐月闭合核验', () => {
  render(<SectorMonitorTable table={table} />)
  const main = screen.getByRole('table', { name: '行业就业广度与结构表' })
  const privateRow = within(main).getByRole('rowheader', { name: '私营部门合计' }).closest('tr')!
  expect(privateRow).toHaveAttribute('data-parent-id', 'total')
  expect(privateRow).toHaveClass('sector-row--subtotal')
  const leaf = within(main).getByRole('rowheader', { name: '零售业' })
  expect(leaf).toHaveAttribute('data-depth', '2')
  expect(within(main).getAllByText('—')).toHaveLength(5)
  const checks = screen.getByRole('table', { name: '行业就业逐月闭合核验表' })
  expect(within(checks).getByText('私营+政府−非农')).toBeInTheDocument()
  expect(within(checks).getByText('0.0')).toBeInTheDocument()
  expect(screen.getByText(/按父子层级核验，不重复加总/)).toBeInTheDocument()
})

it('超出容差的核验不得显示通过；原工资表无闭合字段仍正常', () => {
  const view = render(<SectorMonitorTable table={{ ...table, reconciliation: { ...table.reconciliation, checks: [{ id: 'bad', label: '差额测试', values: [1], tolerance: 0.1 }] } }} />)
  expect(screen.getByText('存在超容差差额')).toBeInTheDocument()
  view.rerender(<SectorMonitorTable table={{ ...table, reconciliation: undefined }} />)
  expect(screen.queryByRole('table', { name: '行业就业逐月闭合核验表' })).not.toBeInTheDocument()
  expect(screen.getByRole('table', { name: '行业就业广度与结构表' })).toBeInTheDocument()
})
