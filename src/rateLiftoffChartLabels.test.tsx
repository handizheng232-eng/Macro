import { render, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import data from './data/historyReplayRateLiftoffQtGuidance.json'
import taper from './data/historyReplayTaper.json'
import { HistoryReplay } from './historyReplay'
afterEach(cleanup)
function cards(input = data) {
  const { container } = render(<HistoryReplay data={input} readingControls onBack={() => {}} />)
  return [...container.querySelectorAll('.replay-path-chart')].filter(e => e.querySelector('img[data-approved-market-chart]'))
}
it('resolves both verified derived spread names and bp units without changing six chart cards', () => {
  const charts = cards()
  expect(charts).toHaveLength(6)
  const spread = charts.find(c => c.querySelector('img')!.getAttribute('src') === 'replay-rate-liftoff/03-spreads.svg')!
  expect(spread.querySelector('p:last-child')!.textContent).toBe('10年－2年 · bp；10年－3个月 · bp。观察期：2022年3月16日至2022年5月31日；来源与逐点记录见下。当前回取，不是当时快照。')
  for (const c of charts) expect(c.textContent).not.toMatch(/undefined|null|NaN|\[object Object\]/)
})
it('preserves every base series title and raw unit in all approved cards', () => {
  const charts = cards()
  for (const [i, chart] of data.marketPaths.approvedCharts.entries()) {
    for (const id of chart.seriesIds) {
      const item = data.marketPaths.series.find(s => s.id === id)
      if (item) expect(charts[i].textContent).toContain(`${item.title} · ${item.unit}`)
    }
  }
})
it('shows an unknown series ID verbatim with an explicit unknown unit', () => {
  const input = structuredClone(data)
  input.marketPaths.approvedCharts[2].seriesIds = ['unregistered-spread']
  const chart = cards(input)[2]
  expect(chart.textContent).toContain('unregistered-spread · 单位未知')
  expect(chart.textContent).not.toMatch(/undefined|null|NaN|\[object Object\]/)
})
it('resolves explicit derived metadata without requiring base observation fields', () => {
  const input = { ...data, marketPaths: { ...data.marketPaths, derivedSeries: [{ id: 'reviewed-derived', title: '已核定派生指标', unit: 'bp' }], approvedCharts: [{ ...data.marketPaths.approvedCharts[2], seriesIds: ['reviewed-derived'] }] } }
  expect(cards(input)[0].textContent).toContain('已核定派生指标 · bp')
})
it('preserves all sibling Taper series labels and units', () => {
  const { container } = render(<HistoryReplay data={taper} readingControls onBack={() => {}} />)
  const charts = [...container.querySelectorAll('.replay-path-chart')]
  for (const [i, chart] of taper.marketPaths.approvedCharts.entries()) {
    for (const id of chart.seriesIds) {
      const item = taper.marketPaths.series.find(s => s.id === id)!
      expect(charts[i].textContent).toContain(`${item.title} · ${item.unit}`)
    }
    expect(charts[i].textContent).not.toMatch(/undefined|null|NaN|\[object Object\]/)
  }
})
