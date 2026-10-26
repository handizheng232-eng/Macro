import { createHash } from 'node:crypto'
import { render, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import data from './data/historyReplayRateLiftoffQtGuidance.json'
import pins from './test/rateLiftoffPublicPins.json'
import { HistoryReplay } from './historyReplay'
afterEach(cleanup)
const resolve = (pointer: string): string => {
  if (pointer.includes('#paragraph/')) return data.marketAnalysis.conclusion.split('\n\n')[Number(pointer.split('/').at(-1))]
  let value: unknown = data
  for (const key of pointer.slice(1).split('/')) value = (value as Record<string, unknown>)[key]
  return value as string
}
it('preserves all 203 admitted public nodes and all 283 projections without private fixtures', () => {
  expect(new Set(pins.map(p => p.id)).size).toBe(203)
  for (const pin of pins) expect(createHash('sha256').update(resolve(pin.pointer)).digest('hex'), pin.id + pin.pointer).toBe(pin.sha256)
  expect(data.localReview.fullStageReady).toBe(false)
  expect(data.localReview.publicReleaseAllowed).toBe(false)
  expect(data.localReview.strictHistoricalEligible).toBe(false)
  expect(data.sources).toHaveLength(112)
})
it('renders complete 142 deep bodies, five themes and forty independent columns', () => {
  const { container } = render(<HistoryReplay data={data} readingControls onBack={() => {}} />)
  expect(container.querySelectorAll('[data-reading-column]')).toHaveLength(40)
  for (const section of data.marketAnalysis.sections) {
    for (const entries of Object.values(section.deepDive)) for (const entry of entries) {
      const node = container.querySelector(`[data-analysis-entry="${entry.id}"]`)!
      expect(node).toBeTruthy()
      expect(node.textContent).toContain(entry.text)
    }
    const summary = container.querySelector(`[data-period-summary="${section.id}"]`)!
    for (const text of section.periodSummary.paragraphs) expect(summary.textContent).toContain(text)
  }
  expect(container.querySelectorAll('[data-reading-column][open]')).toHaveLength(0)
  expect(container.querySelectorAll('.replay-outline [data-depth="3"]')).toHaveLength(0)
  const ids = [...container.querySelectorAll('[id]')].map(e => e.id)
  expect(new Set(ids).size).toBe(ids.length)
})
it('closes source and report aliases without admitting arbitrary unknown IDs', () => {
  const ids = new Set([...data.sources.map(s => s.id), ...data.reports.map(r => r.id)])
  for (const section of data.marketAnalysis.sections) {
    const records = [section, section.periodSummary, ...Object.values(section.aspectSummaries), ...Object.values(section.deepDive).flat()]
    for (const record of records) for (const id of [...record.sourceIds, ...record.reportIds]) expect(ids.has(id), id).toBe(true)
  }
  expect(JSON.stringify(data)).not.toMatch(/(?:file:\/\/|[A-Za-z]:[\\/](?:HermesData|Users)|completeOriginalSupport)/)
  for (const section of data.marketAnalysis.sections) for (const entry of Object.values(section.deepDive).flat()) for (const evidence of entry.supportingEvidence || []) expect(evidence.evidenceBasis).toBeNull()
})
