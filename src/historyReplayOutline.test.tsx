import { cleanup, fireEvent, render, screen, within, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayRenewedEasingQtEnd.json'
import { ReplayOutline } from './replayOutline'
afterEach(() => { cleanup(); vi.restoreAllMocks() })
it('keeps deep-source reading active on its visible parent column without exposing a fourth-level link', async () => {
  const items = [{ id: 'primary', title: 'Primary' }, { id: 'theme', title: 'Theme', depth: 1 }, { id: 'column', title: 'Column', depth: 2 }, { id: 'source', title: '2025-12-11 source', depth: 3 }, { id: 'next', title: 'Next', depth: 2 }]
  const { container } = render(<article className="replay-reading-controls"><ReplayOutline items={items} navigate={() => {}} /><section id="primary"><section id="theme"><section id="column"><p id="source">Full original source body</p></section><section id="next">Next column</section></section></section></article>)
  for (const item of items) vi.spyOn(document.getElementById(item.id)!, 'getBoundingClientRect').mockReturnValue({ top: item.id === 'next' ? 700 : item.id === 'source' ? 90 : -200 } as DOMRect)
  fireEvent.scroll(window)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Column' })).toHaveAttribute('aria-current', 'location'))
  expect(container.querySelector('[data-reading-target="source"]')).toBeNull()
  expect(document.getElementById('source')).toHaveTextContent('Full original source body')
})
it('tracks real scroll geometry and excludes collapsed descendants from active state', async () => {
  render(<article className="replay-reading-controls"><ReplayOutline navigate={() => {}} items={[{ id: 'a', title: 'A' }, { id: 'b', title: 'B' }, { id: 'c', title: 'C' }]} /><section id="a">A body</section><section id="b">B body</section><details><summary>C header</summary><section id="c">Hidden C</section></details></article>)
  let bTop = 500
  vi.spyOn(document.getElementById('a')!, 'getBoundingClientRect').mockImplementation(() => ({ top: -100 }) as DOMRect)
  vi.spyOn(document.getElementById('b')!, 'getBoundingClientRect').mockImplementation(() => ({ top: bTop }) as DOMRect)
  vi.spyOn(document.getElementById('c')!, 'getBoundingClientRect').mockImplementation(() => ({ top: -1 }) as DOMRect)
  fireEvent.scroll(window)
  await waitFor(() => expect(screen.getByRole('button', { name: 'A' })).toHaveAttribute('aria-current', 'location'))
  bTop = 100
  fireEvent.scroll(window)
  await waitFor(() => expect(screen.getByRole('button', { name: 'B' })).toHaveAttribute('aria-current', 'location'))
  expect(screen.getByRole('button', { name: 'C' })).not.toHaveAttribute('aria-current')
})
it('folds primary modules independently and bulk does not open source records', () => {
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const blocks = container.querySelectorAll('details[data-reading-block]')
  expect(blocks.length).toBeGreaterThanOrEqual(5)
  expect(container.querySelector('details[data-reading-block][open]')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '展开全篇大板块' }))
  expect(container.querySelectorAll('details[data-reading-block][open]')).toHaveLength(blocks.length)
  expect(container.querySelector('.replay-disclosure[open]')).toBeNull()
  fireEvent.click(container.querySelector('.replay-topic-toggle')!)
  fireEvent.click(screen.getByRole('button', { name: '收起全篇大板块' }))
  fireEvent.click(screen.getByRole('button', { name: '展开全篇大板块' }))
  expect(container.querySelector('.replay-topic-toggle')).toHaveAttribute('aria-expanded', 'true')
}, 30000)
it('side directory reveals every ancestor, preserves route and returns without a new history entry', () => {
  HTMLElement.prototype.scrollIntoView = vi.fn()
  const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const nav = screen.getByRole('navigation', { name: '本篇目录' })
  for (const channel of ['星球', 'Wind', '微信']) expect(within(nav).getByRole('button', { name: new RegExp(`${channel}观点明细$`) })).toBeInTheDocument()
  const entry = data.marketAnalysis.sections.flatMap(s => Object.values(s.deepDive).flat()).find(n => n.claimIds?.length)!
  const hash = location.hash
  const columnId = document.getElementById(`analysis-entry-${entry.id}`)!.closest('[data-reading-column]')!.id
  fireEvent.click(nav.querySelector(`[data-reading-target="${columnId}"]`)!)
  fireEvent.click(within(screen.getByRole('navigation', { name: '公众号本轮正文目录' })).getByRole('button', { name: entry.title }))
  expect(document.getElementById(`analysis-entry-${entry.id}`)).toBeVisible()
  expect(document.getElementById(`analysis-entry-${entry.id}`)).toHaveFocus()
  expect(container.querySelector('#reading-analysis')).toHaveAttribute('open')
  fireEvent.click(within(nav).getByRole('button', { name: /市场预期与现实路径对照$/ }))
  expect(container.querySelector('#reading-comparison > summary')).not.toHaveAttribute('tabindex', '-1')
  fireEvent.click(screen.getByRole('button', { name: '返回刚才位置' }))
  expect(location.hash).toBe(hash)
  fireEvent.click(screen.getByRole('button', { name: '返回刚才位置' }))
  expect(scroll).toHaveBeenCalled()
  expect(screen.getByRole('button', { name: '返回刚才位置' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2025-12-30' } })
  expect(within(screen.getByRole('navigation', { name: '本篇目录' })).queryByText(entry.title)).toBeNull()
  expect(container.querySelector('[data-analysis-entry]')).toBeNull()
}, 30000)
