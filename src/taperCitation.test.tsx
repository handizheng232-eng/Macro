import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayTaper.json'

afterEach(() => { cleanup(); vi.restoreAllMocks() })
it('returns to the actual citation without opening an unrelated preceding chart disclosure', () => {
  HTMLElement.prototype.scrollIntoView = vi.fn()
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(callback => { callback(0); return 1 })
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    return { top: this.id === 'reading-paths' ? 67 : this.tagName === 'BUTTON' ? 486 : 1000, left: 0, right: 200, bottom: 510, width: 200, height: 24, x: 0, y: 0, toJSON() {} }
  })
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  fireEvent.click(container.querySelector('#reading-comparison > summary')!)
  fireEvent.click(container.querySelector('[aria-label="五主题逐月路径对照"] details > summary')!)
  const citation = container.querySelectorAll('[aria-label="五主题逐月路径对照"] button')[2]
  fireEvent.click(citation)
  fireEvent.click([...container.querySelectorAll('.replay-outline-actions button')].find(n => n.textContent === '返回刚才位置')!)
  expect(container.querySelector('#reading-paths')).not.toHaveAttribute('open')
  expect(citation).toHaveFocus()
})
it('resolves every real monthly citation to its unique body node, not a channel disclosure', () => {
  const scroll = vi.fn()
  HTMLElement.prototype.scrollIntoView = scroll
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const ids = [...container.querySelectorAll('[id]')].map(n => n.id)
  expect(new Set(ids).size).toBe(ids.length)
  const expected = data.marketAnalysis.sections.flatMap(section => ['2021-12', '2022-01', '2022-02', '2022-03'].flatMap(month => (['expectationTimeline', 'realityTimeline', 'implicationTimeline'] as const).flatMap(role => section.deepDive[role].filter(n => n.id.includes(month)).map(n => n.id))))
  const citations = container.querySelectorAll('[aria-label="五主题逐月路径对照"] button')
  expect(citations).toHaveLength(expected.length)
  const hash = window.location.hash
  citations.forEach((citation, index) => {
    fireEvent.click(citation)
    const target = document.getElementById(`analysis-entry-${expected[index]}`)!
    expect(target).toHaveAttribute('data-analysis-entry', expected[index])
    expect(target).toHaveFocus()
    expect(target.closest('[hidden]')).toBeNull()
    for (let parent = target.parentElement; parent; parent = parent.parentElement) {
      if (parent instanceof HTMLDetailsElement) expect(parent.open).toBe(true)
    }
    expect(scroll.mock.instances.at(-1)).toBe(target)
    expect(window.location.hash).toBe(hash)
  })
  expect([...container.querySelectorAll('.replay-outline-actions button')].find(n => n.textContent === '返回刚才位置')).not.toBeDisabled()
})
