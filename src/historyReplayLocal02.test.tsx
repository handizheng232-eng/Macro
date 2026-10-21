import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayRenewedEasingQtEnd.json'
afterEach(cleanup)
it('renders three admitted paragraphs in policy body, current exception and pending analysis; unmounts history', () => {
  const { container } = render(<HistoryReplay onBack={() => {}} data={data} />)
  const policy = data.marketAnalysis.sections[0]
  const nodes = Object.values(policy.deepDive || {}).flat().filter(n => n.id.startsWith('local02-WP'))
  expect(nodes).toHaveLength(3)
  for (const n of nodes) {
    const el = container.querySelector(`[data-analysis-entry="${n.id}"]`)
    expect(el).not.toBeNull()
    expect(el?.querySelector('[data-analysis-text]')?.textContent).toBe(n.text)
  }
  expect(screen.getByLabelText('公众号本轮正文目录').querySelectorAll('button')).toHaveLength(7)
  expect(container.textContent).not.toContain('本地新配额未完成：12月缺1篇')
  expect(container.textContent).not.toContain('本轮新增原发0篇')
  expect(container.textContent).toContain('待分析0篇')
  expect(container.textContent).toContain('旧中邮相关观点待单独复核')
  expect(container.textContent).toContain('未接入CME概率数据')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2025-12-30' } })
  for (const n of nodes) expect(container.querySelector(`[data-analysis-entry="${n.id}"]`)).toBeNull()
  for (const s of data.sources.filter(s => s.id.startsWith('WP01'))) expect(container.textContent).not.toContain(s.title)
  expect(screen.queryByLabelText('公众号本轮正文目录')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByLabelText('公众号本轮正文目录').querySelectorAll('button')).toHaveLength(7)
}, 30000)
