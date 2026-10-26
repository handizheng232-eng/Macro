import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'

describe('Taper local admitted projection', () => {
  it('ships a limited local DTO rather than silently dropping the admitted chapter', () => {
    const file = `${process.cwd()}/src/data/historyReplayTaper.json`
    expect(existsSync(file)).toBe(true)
    const data = JSON.parse(readFileSync(file, 'utf8'))
    expect(data.localReview.fullStageReady).toBe(false)
    expect(data.localReview.publicReleaseAllowed).toBe(false)
    expect(data.marketAnalysis.sections).toHaveLength(5)
  })
})
