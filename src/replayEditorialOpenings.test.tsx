import { expect, it } from 'vitest'
import taper from './data/historyReplayTaper.json'
import liftoff from './data/historyReplayRateLiftoffQtGuidance.json'
import matrix from './test/replayEditorialOpenings.json'
const pages = { A: taper, B: liftoff }
function resolve(data: unknown, pointer: string): unknown {
  return pointer.slice(1).split('/').reduce((value, key) => (value as Record<string, unknown>)[key], data)
}
it('renders a reviewed opening contract for all fifty cells with exact fallback mirrors', () => {
  expect(matrix).toHaveLength(50)
  expect(new Set(matrix.map(r => `${r.page}/${r.section}/${r.role}`)).size).toBe(50)
  for (const row of matrix) {
    const data = pages[row.page as keyof typeof pages]
    expect(resolve(data, row.pointer), `${row.page}${row.pointer}`).toBe(row.after)
    expect(resolve(data, row.mirrorPointer)).toBe(row.after)
    expect(row.after).not.toBe(row.before)
  }
})
it('keeps source aliases closed and research readiness separate from editorial completion', () => {
  for (const data of Object.values(pages)) {
    const ids = new Set([...data.sources, ...data.reports].map(s => s.id))
    expect(data.marketAnalysis.sections).toHaveLength(5)
    for (const section of data.marketAnalysis.sections) {
      for (const ref of section.periodSummary.paragraphSources[0]) expect(ids.has(ref.sourceId)).toBe(true)
      for (const aspect of Object.values(section.aspectSummaries)) for (const id of aspect.sourceIds) expect(ids.has(id)).toBe(true)
    }
    expect(data.localReview.fullStageReady).toBe(false)
    expect(JSON.stringify(data)).not.toMatch(/(?:file:\/\/|[A-Za-z]:[\\/](?:HermesData|Users))/)
  }
})
