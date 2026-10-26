import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import data from './data/historyReplayTaper.json'
import { HistoryReplay } from './historyReplay'

afterEach(() => { cleanup(); vi.restoreAllMocks() })
it('renders the admitted incremental research in the actual body and unmounts it at a historical cutoff', () => {
  HTMLElement.prototype.scrollIntoView = vi.fn()
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const nodes = [...container.querySelectorAll('[data-analysis-entry]')].filter(n => n.getAttribute('data-analysis-entry')?.includes('-nsr01-'))
  expect(nodes).toHaveLength(18)
  const n = nodes.find(n => n.getAttribute('data-analysis-entry') === 'taper-curve-nsr01-n12')!
  expect(n.textContent).toContain('可能')
  const sources = [...container.querySelectorAll('[data-summary-source]')]
  expect(sources.some(n => n.getAttribute('data-summary-source') === 'wx-tg9RjTBIEsOC')).toBe(true)
  fireEvent.change(container.querySelector('#replay-cutoff')!, { target: { value: '2022-02-01' } })
  expect(container.querySelectorAll('[data-analysis-entry]')).toHaveLength(0)
  expect(container.querySelectorAll('[data-summary-source]')).toHaveLength(0)
  expect(container.textContent).not.toContain('通胀压力如何转成收紧判断')
  expect(container.textContent).not.toContain('美国通胀创新高，债务上限再提高')
})
it('shows the new ten-per-month contract without conflating acquisition, use, limited admission and quota', () => {
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  expect(container.textContent).toContain('公众号每月目标10篇')
  expect(container.textContent).toContain('取得34篇')
  expect(container.textContent).toContain('采用32篇')
  expect(container.textContent).toContain('重点池未达标')
  expect(container.textContent).not.toContain('公众号取得20篇')
  expect(data.localReview.fullStageReady).toBe(false)
  expect(data.candidateMetadata.parentAccepted).toBe(false)
})
