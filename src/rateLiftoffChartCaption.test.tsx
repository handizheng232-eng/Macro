import { render, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import data from './data/historyReplayRateLiftoffQtGuidance.json'
import taper from './data/historyReplayTaper.json'
import { HistoryReplay } from './historyReplay'
afterEach(cleanup)
it('uses this exact stage window on five charts and May 4–5 on the event chart', () => {
  const { container } = render(<HistoryReplay data={data} readingControls onBack={() => {}} />)
  const charts = [...container.querySelectorAll('.replay-path-chart')].filter(e => e.querySelector('img[data-approved-market-chart]'))
  expect(charts).toHaveLength(6)
  for (const chart of charts) {
    const event = chart.querySelector('img')!.getAttribute('src') === 'replay-rate-liftoff/06-event-window.svg'
    expect(chart.textContent).toContain(event ? '观察期：2022年5月4日至2022年5月5日' : '观察期：2022年3月16日至2022年5月31日')
    expect(chart.textContent).not.toContain('2021年12月1日')
    expect(chart.textContent).toContain('当前回取，不是当时快照')
  }
})
it('preserves all six existing Taper captions without inheriting the next stage dates', () => {
  const { container } = render(<HistoryReplay data={taper} readingControls onBack={() => {}} />)
  const charts = [...container.querySelectorAll('.replay-path-chart')].filter(e => e.querySelector('img[data-approved-market-chart]'))
  expect(charts).toHaveLength(6)
  for (const chart of charts) {
    expect(chart.textContent).toContain('观察期：2021年12月1日至2022年3月15日')
    expect(chart.textContent).not.toContain('2022年5月31日')
  }
})
