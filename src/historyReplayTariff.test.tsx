import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import App from './App'

it('关税暂停阶段可直达，明确阶段性版本，历史截面卸载研究与图', () => {
  window.history.replaceState(null, '', '#history/easing-to-tightening/tariff-pause')
  render(<App />)
  expect(screen.getByRole('heading', { name: '关税迷雾下的暂停', level: 1 })).toBeInTheDocument()
  expect(screen.getByText(/阶段性版本：四个主题/)).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: '美元与相对条件 · 待补充' })).toBeInTheDocument()
  expect(screen.getByRole('img', { name: '2025年美债收益率、期限利差与通胀补偿' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: '预期 → 现实：事件时间轴' })).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2025-04-01' } })
  expect(screen.queryByRole('region', { name: '综合市场分析' })).not.toBeInTheDocument()
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('恢复资料截止日'))
  expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument()
})
