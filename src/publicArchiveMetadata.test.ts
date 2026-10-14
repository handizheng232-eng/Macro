import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'
import { redactArchiveMetadata } from '../buildPlugins/publicArchiveMetadata'

const sha256 = (input: string | Uint8Array) => createHash('sha256').update(input).digest('hex')

it.each(['usEmploymentData.json', 'usLateModulesData.json'])('public build strips only %s rawSnapshots absolute paths and preserves all values/versions', (filename) => {
  const path = resolve('src', 'data', filename)
  const beforeBytes = readFileSync(path)
  const source = beforeBytes.toString('utf8')
  const before = JSON.parse(source)
  const transformed = redactArchiveMetadata(source, `/work/src/data/${filename}`)
  expect(transformed).not.toBeNull()
  const after = JSON.parse(transformed!)
  const expected = structuredClone(before)
  let changed = 0
  for (const [key, value] of Object.entries(expected.rawSnapshots)) {
    if (typeof value === 'string' && /^[A-Za-z]:[\\/]/.test(value)) {
      expected.rawSnapshots[key] = null
      changed += 1
    }
  }
  expect(changed).toBe(2)
  expect(sha256(JSON.stringify(after))).toBe(sha256(JSON.stringify(expected)))
  expect(sha256(readFileSync(path))).toBe(sha256(beforeBytes))
})

it('never silently changes the approved third or either prior replay JSON', () => {
  const source = JSON.stringify({ rawSnapshots: { local: 'E:/private/archive.json' }, series: [1, 2, 3] })
  for (const name of ['historyReplay.json', 'historyReplayHawkishTransition.json', 'historyReplayRenewedEasingQtEnd.json']) {
    expect(redactArchiveMetadata(source, `/work/src/data/${name}`)).toBeNull()
  }
})

it('preserves public URLs, relative references and observation dates', () => {
  const source = JSON.stringify({ rawSnapshots: { official: 'https://www.federalreserve.gov/releases/h41/', relative: 'data/raw/snapshot.json' }, date: '2025-12-31', value: 81.67 })
  expect(redactArchiveMetadata(source, '/work/src/data/usLateModulesData.json')).toBeNull()
})
