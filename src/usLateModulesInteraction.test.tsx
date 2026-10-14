import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { UsLateModuleDetail } from './usLateModules'

afterEach(() => { cleanup(); vi.restoreAllMocks() })

it('短区间内已终止的单点目标不参与悬停，也不导致整页崩溃', () => {
  render(<UsLateModuleDetail category="fed" onBack={() => {}} />)
  const group = screen.getByRole('group', { name: '联邦基金政策目标与实际利率时间范围' })
  const chart = group.closest('article')!
  vi.spyOn(SVGElement.prototype, 'getBoundingClientRect').mockReturnValue({ left: 0, top: 0, width: 920, height: 350, right: 920, bottom: 350, x: 0, y: 0, toJSON: () => ({}) })
  for (const range of ['1年', '3年', '5年', '10年', '20年', '30年', '全部']) {
    fireEvent.click(within(group).getByRole('button', { name: range }))
    fireEvent(within(chart).getByRole('img'), new MouseEvent('pointermove', { bubbles: true, clientX: 200 }))
    expect(screen.getByRole('heading', { name: '美国美联储与金融条件' })).toBeInTheDocument()
    expect(chart.querySelector('.chart-readout strong')).not.toBeNull()
    expect(chart.innerHTML).not.toMatch(/NaN|Infinity/)
  }
})

it('短区间仅启用已终止序列时显示无数据状态并可恢复', () => {
  render(<UsLateModuleDetail category="fed" onBack={() => {}} />)
  const group = screen.getByRole('group', { name: '联邦基金政策目标与实际利率时间范围' })
  const chart = group.closest('article')!
  fireEvent.click(within(group).getByRole('button', { name: '1年' }))
  const switches = within(chart).getByRole('group', { name: '联邦基金政策目标与实际利率序列开关' })
  for (const button of within(switches).getAllByRole('button')) {
    if (!button.textContent?.includes('单点目标')) fireEvent.click(button)
  }
  expect(within(chart).getByText('当前区间内所选序列无数据')).toBeInTheDocument()
  expect(chart.innerHTML).not.toMatch(/NaN|Infinity/)
  fireEvent.click(within(group).getByRole('button', { name: '全部' }))
  expect(within(chart).queryByText('当前区间内所选序列无数据')).not.toBeInTheDocument()
})
