import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayRenewedEasingQtEnd.json'

afterEach(() => { cleanup(); vi.restoreAllMocks() })
it('keeps theme headings and judgments visible while folding only opted-in long reading bodies', () => {
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const topics = Array.from(container.querySelectorAll('.replay-analysis-topic'))
  fireEvent.click(screen.getByRole('button', { name: '展开全篇大板块' }))
  expect(topics).toHaveLength(5)
  for (const topic of topics) {
    const toggle = topic.querySelector('button[aria-expanded]')!
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    const body = document.getElementById(toggle.getAttribute('aria-controls')!)!
    expect(body).not.toBeVisible()
    expect(topic.querySelector('h3')).toBeVisible()
    expect(topic.querySelector('.replay-analysis-judgement')).toBeVisible()
    fireEvent.click(toggle)
    expect(body).toBeVisible()
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(toggle)
    expect(body).not.toBeVisible()
  }
}, 30000)

it('expands only research bodies in bulk and reveals a closed entry before scrolling without changing the route', () => {
  const scroll = vi.fn()
  HTMLElement.prototype.scrollIntoView = scroll
  const pageScroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const hash = window.location.hash
  fireEvent.click(screen.getByRole('button', { name: '展开全篇大板块' }))
  fireEvent.click(screen.getByRole('button', { name: '全部展开研究正文' }))
  expect(container.querySelectorAll('.replay-topic-toggle[aria-expanded="true"]')).toHaveLength(5)
  expect(container.querySelector('details:not([data-reading-block])[open]')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '全部收起研究正文' }))
  expect(container.querySelectorAll('.replay-topic-toggle[aria-expanded="false"]')).toHaveLength(5)
  const entry = data.marketAnalysis.sections.flatMap(s => Object.values(s.deepDive).flat()).find(n => n.claimIds?.length)!
  fireEvent.click(screen.getByLabelText('公众号本轮正文目录').querySelector('button')!)
  const target = document.getElementById(`analysis-entry-${entry.id}`)!
  expect(target).toBeVisible()
  expect(target).toHaveFocus()
  expect(scroll).toHaveBeenCalled()
  expect(window.location.hash).toBe(hash)
  fireEvent.click(screen.getAllByRole('button', { name: /回到本板块顶部/ })[0])
  expect(container.querySelector('.replay-analysis-topic')).toHaveFocus()
  fireEvent.click(screen.getByRole('button', { name: '回到页面顶部' }))
  expect(container.querySelector('.replay-heading')).toHaveFocus()
  expect(pageScroll).toHaveBeenCalledWith({ top: 0, behavior: 'smooth' })
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2025-12-30' } })
  expect(container.querySelector('[data-analysis-entry]')).toBeNull()
  expect(screen.queryByRole('button', { name: '全部展开研究正文' })).toBeNull()
}, 30000)

it('leaves the existing default uncollapsed without opting in', () => {
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(container.querySelector('.replay-topic-toggle')).toBeNull()
  expect(container.querySelector('[data-analysis-entry]')).toBeVisible()
  expect(screen.queryByRole('button', { name: '回到页面顶部' })).toBeNull()
}, 30000)
