import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayRenewedEasingQtEnd.json'
import first from './data/historyReplay.json'
import second from './data/historyReplayHawkishTransition.json'
afterEach(cleanup)
const labels = ['阶段总结', '观点 / 事前预期', '现实', '机制', '分歧 / 预期差', '市场含义', '实例 / 原文与数据', '验证条件']
it('numbers body and directory from one hierarchy with eight ordered children per theme', () => {
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const nav = container.querySelector('.replay-outline')!
  expect(nav.querySelectorAll('li[data-depth="3"], [data-reading-target^="analysis-entry-"]')).toHaveLength(0)
  expect(nav.querySelector('ol ol ol ol')).toBeNull()
  const numbers: string[] = []
  for (const link of nav.querySelectorAll('[data-reading-target]')) {
    const target = container.querySelector(`#${link.getAttribute('data-reading-target')}`)!
    if (target.id === 'replay-page-top') continue
    const heading = target.querySelector('h2, h3, h4, h5')!
    expect(heading.textContent).toBe(link.textContent)
  }
  for (const topic of container.querySelectorAll('.replay-analysis-topic')) {
    const topicLink = nav.querySelector(`[data-reading-target="${topic.id}"]`)!
    expect(topicLink.parentElement!.querySelectorAll(':scope > ol > li')).toHaveLength(8)
    const fields = topic.querySelectorAll('[data-reading-column]')
    expect(fields).toHaveLength(8)
    expect(Array.from(fields, field => field.getAttribute('data-column-label'))).toEqual(labels)
    for (const field of fields) {
      const heading = field.querySelector('h4')!
      expect(heading.querySelector('.replay-heading-text')).toHaveTextContent(field.getAttribute('data-column-label')!)
      const link = nav.querySelector(`[data-reading-target="${field.id}"]`)!
      expect(link.textContent).toBe(heading.textContent)
      expect(link.closest('li')).toHaveAttribute('data-depth', '2')
      numbers.push(heading.querySelector('[data-reading-number]')!.textContent!)
    }
  }
  expect(new Set(numbers).size).toBe(40)
}, 30000)
it('folds columns independently, preserves children through parent toggles and reveals all ancestors on directory jump', () => {
  HTMLElement.prototype.scrollIntoView = vi.fn()
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const first = container.querySelector<HTMLDetailsElement>('[data-reading-column]')!
  expect(first.tagName).toBe('DETAILS')
  expect(container.querySelector('[data-reading-column][open]')).toBeNull()
  fireEvent.click(container.querySelector('[data-reading-target="replay-topic-0-summary"]')!)
  expect(first).toHaveAttribute('open')
  expect(first.querySelector('summary')).toHaveFocus()
  expect(first).toBeVisible()
  expect(container.querySelectorAll('[data-reading-column][open]')).toHaveLength(1)
  const toggle = container.querySelector('.replay-topic-toggle')!
  fireEvent.click(toggle)
  fireEvent.click(toggle)
  expect(first).toHaveAttribute('open')
  fireEvent.click(container.querySelector('[data-reading-target="replay-topic-0-validation"]')!)
  expect(first).toHaveAttribute('open')
  expect(container.querySelectorAll('[data-reading-column][open]')).toHaveLength(2)
}, 30000)
it('removes auxiliary framework charts only from the opted-in third replay, keeping market paths and other replays', () => {
  const view = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  expect(view.container.textContent).not.toContain('宏观框架辅助图表')
  expect(view.container.querySelector('#reading-paths svg')).not.toBeNull()
  expect(view.container.querySelector('#reading-comparison table')).not.toBeNull()
  for (const other of [first, second]) {
    view.rerender(<HistoryReplay key={other.title} data={other} onBack={() => {}} />)
    expect(view.container.textContent).toContain('宏观框架辅助图表')
    expect(view.container.querySelector('[data-reading-column]')).toBeNull()
  }
}, 30000)
