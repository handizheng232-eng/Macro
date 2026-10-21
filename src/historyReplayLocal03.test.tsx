import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayRenewedEasingQtEnd.json'
afterEach(cleanup)
const nodes = data.marketAnalysis.sections.flatMap(s => Object.values(s.deepDive).flat()).filter(n => n.id.startsWith('local03-'))
it('shows all four limited candidates with honest statistics, full conditions and line locators', () => {
  const { container } = render(<HistoryReplay onBack={() => {}} data={data} />)
  expect(nodes).toHaveLength(4)
  expect(data.experimentStatus.wechatPendingAnalysis).toBe(0)
  expect(data.experimentStatus.wechatAcceptedTotal).toBe(23)
  expect(data.experimentStatus.libraryReviewedCandidateCount).toBe(4)
  expect(data.experimentStatus.wechatLocalUsedCount).toBe(4)
  expect(data.experimentStatus.wechatLocalNotUsedCount).toBe(0)
  for (const n of nodes) {
    const el = container.querySelector(`[data-analysis-entry="${n.id}"]`)!
    expect(el.querySelector('[data-analysis-text]')?.textContent).toBe(n.text)
    expect(el.textContent).toContain('已分析参考')
    expect(el.textContent).not.toMatch(/第正文行.*页/)
    expect(el.querySelector('a')?.getAttribute('href')).toBe(data.sources.find(s => s.id === n.sourceIds[0])?.url)
  }
  expect(nodes.map(n => n.text).join('')).toContain('不着陆或再通胀')
  expect(nodes.map(n => n.text).join('')).toContain('高估值仍可能触发调整')
  expect(nodes.map(n => n.text).join('')).toContain('AI资本开支尚未出现二阶拐点')
  expect(nodes.map(n => n.text).join('')).toContain('两者的相对斜率当时仍待观察')
  expect(screen.getByLabelText('公众号本轮正文目录').querySelectorAll('button')).toHaveLength(7)
}, 30000)
it('unmounts all four titles, paragraphs and sources in strict history, then restores', () => {
  const { container } = render(<HistoryReplay onBack={() => {}} data={data} />)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2025-12-30' } })
  for (const n of nodes) {
    expect(container.querySelector(`[data-analysis-entry="${n.id}"]`)).toBeNull()
    expect(container.textContent).not.toContain(n.title)
    expect(container.textContent).not.toContain(n.text)
    expect(container.textContent).not.toContain(data.sources.find(s => s.id === n.sourceIds[0])!.title)
  }
  expect(screen.queryByLabelText('公众号本轮正文目录')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByLabelText('公众号本轮正文目录').querySelectorAll('button')).toHaveLength(7)
}, 30000)
