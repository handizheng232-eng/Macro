import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { checkCoverage, checkPublicPaths } from './verify_replay_publish.mjs'
const channels = ['知识星球', 'Wind', '微信公众号']
const minimum = { 知识星球: 20, Wind: 10, 微信公众号: 5 }
function fixture() {
  const rows = Array.from({ length: 8 }, (_, index) => {
    const month = `2026-${String(index + 1).padStart(2, '0')}`
    return { month, channels: Object.fromEntries(channels.map(channel => {
      const archives = Array.from({ length: minimum[channel] }, (_, n) => ({
        reportId: `${month}-${channel}-${n}`, independentWorkId: `${month}-${channel}-${n}`,
        path: `stage/${month}-${channel}-${n}.${channel === '微信公众号' ? 'txt' : 'pdf'}`,
        sha256: createHash('sha256').update(`${month}-${channel}-${n}`).digest('hex'), date: `${month}-12`,
        sourceQuality: { parentLedgerVerified: true, originalBodyVerified: true, datePolicyVerified: true,
          scopeVerified: true, tag: channel === '知识星球' ? '调研纪要' : undefined,
          versionType: channel === '知识星球' ? 'original_audio_transcript_pdf' : channel === 'Wind' ? 'institutional_research_pdf' : 'official_original_article_text',
          printedPublicationVerified: channel === 'Wind', officialHeaderVerified: channel === '微信公众号',
          account: channel === '微信公众号' ? `TEST ACCOUNT ${n % 2}` : undefined },
      }))
      return [channel, { accepted: true, quotaAccepted: true, covered: true, searchExecuted: true,
        searchComplete: false, searchExhaustive: false, blocked: false,
        bodyCount: archives.length, verifiedBodyCount: archives.length, requiredCount: minimum[channel],
        archiveEntries: archives.length, archives, distributionRecords: archives, accountCount: channel === '微信公众号' ? 2 : 0,
        acceptanceBasis: 'minimum_verified_originals', shortageEvidenceVerified: false, shortageEvidence: null }]
    })) }
  })
  return { startDate: '2026-01-01', endDate: '2026-08-31', requiredCells: 24, acceptedCells: 24, complete: true, rows }
}
function library(c) {
  return c.rows.flatMap(r => channels.flatMap(channel => r.channels[channel].distributionRecords.map(a => ({
    ...a, id: a.reportId, channel: channel === '微信公众号' ? '微信' : channel,
    filenameDate: channel === '知识星球' ? a.date : undefined, publicationDate: channel === '知识星球' ? null : a.date,
    firstAvailableDate: null, historicalAsOfEligible: false,
  }))))
}
describe('public replay release gate', () => {
  it('accepts every verified quota without demanding exhaustive search', () => {
    const c = fixture(); assert.deepEqual(checkCoverage(c, library(c)), [])
  })
  it('rejects 24 one-body assertions', () => {
    const c = fixture()
    for (const r of c.rows) for (const cell of Object.values(r.channels)) {
      cell.archives = cell.archives.slice(0, 1); cell.distributionRecords = cell.archives
      cell.bodyCount = cell.verifiedBodyCount = cell.archiveEntries = 1
    }
    assert.ok(checkCoverage(c, library(c)).some(m => m.includes('quota')))
  })
  it('accepts parent-verified continuous original transcripts without changing the quota', () => {
    const c = fixture()
    for (const row of c.rows) for (const archive of row.channels['知识星球'].distributionRecords) {
      archive.sourceQuality.versionType = 'platform_original_continuous_transcript'
    }
    assert.deepEqual(checkCoverage(c, library(c)), [])
  })
  it('rejects unverified continuous transcripts despite a declared original version', () => {
    const c = fixture()
    c.rows[0].channels['知识星球'].archives[0].sourceQuality.versionType = 'platform_original_continuous_transcript'
    c.rows[0].channels['知识星球'].archives[0].sourceQuality.parentLedgerVerified = false
    assert.ok(checkCoverage(c, library(c)).length)
  })
  it('requires exact days for star filenames and article headers; only printed Wind issues may be month-only', () => {
    for (const channel of ['知识星球', '微信公众号']) {
      const c = fixture()
      for (const a of c.rows[0].channels[channel].distributionRecords) a.date = '2026-01'
      assert.ok(checkCoverage(c, library(c)).length)
    }
  })
  it('requires matching library SHA and original quality', () => {
    const c = fixture(); const reports = library(c)
    reports[0].sha256 = '0'.repeat(64); assert.ok(checkCoverage(c, reports).length)
    reports[0].sha256 = c.rows[0].channels['知识星球'].archives[0].sha256
    reports[0].sourceQuality = { ...reports[0].sourceQuality, originalBodyVerified: false }
    assert.ok(checkCoverage(c, reports).length)
  })
  it('rejects malformed totals, unknown channels, duplicate archives and missing months', () => {
    for (const alter of [c => c.rows.pop(), c => c.rows[0].channels.other = c.rows[0].channels.Wind,
      c => c.rows[0].channels.Wind.bodyCount++, c => c.rows[0].channels.Wind.requiredCount = 1,
      c => c.rows[0].channels.Wind.archives.push(c.rows[0].channels.Wind.archives[0])]) {
      const c = fixture(); alter(c); assert.ok(checkCoverage(c, library(c)).length)
    }
  })
  it('rejects a fabricated shortage, blocked search or absent body', () => {
    const c = fixture(); const cell = c.rows[0].channels['知识星球']
    cell.archives = cell.archives.slice(0, 6); cell.distributionRecords = cell.archives
    cell.bodyCount = cell.verifiedBodyCount = cell.archiveEntries = 6
    cell.shortageEvidenceVerified = true; cell.acceptanceBasis = 'verified_actual_eligible_total'
    assert.ok(checkCoverage(c, library(c)).some(m => m.includes('quota')))
    const full = fixture(); full.rows[1].channels.Wind.blocked = true
    assert.ok(checkCoverage(full, library(full)).length)
    const empty = fixture(); empty.rows[0].channels['微信公众号'].archives = []
    assert.ok(checkCoverage(empty, library(empty)).some(m => m.includes('archive missing')))
  })
  it('accepts a genuinely verified actual shortage, including an actual eligible total of zero', () => {
    for (const actual of [6, 0]) {
      const c = fixture(); const cell = c.rows[0].channels['知识星球']
      cell.archives = cell.archives.slice(0, actual); cell.distributionRecords = cell.archives
      cell.bodyCount = cell.verifiedBodyCount = cell.archiveEntries = actual
      cell.covered = actual > 0; cell.searchExhaustive = true
      cell.shortageEvidenceVerified = true; cell.acceptanceBasis = 'verified_actual_eligible_total'
      cell.shortageEvidence = { actualEligibleTotal: actual, month: '2026-01', channel: '知识星球',
        requiredTopicTag: '调研纪要', onlyOriginalPdf: true, searchExecuted: true,
        searchExhaustive: true, blocked: false, proofSHA256: 'b'.repeat(64) }
      assert.deepEqual(checkCoverage(c, library(c)), [])
    }
  })
  it('rechecks exact private archive bytes and rejects drift or out-of-stage paths', async () => {
    const gate = await import('./verify_replay_publish.mjs')
    assert.equal(typeof gate.checkArchiveFiles, 'function', 'physical archive readback is missing')
    const { mkdtempSync, mkdirSync, writeFileSync, rmSync } = await import('node:fs')
    const { join } = await import('node:path')
    const root = mkdtempSync(join(process.env.TMPDIR || 'C:/HermesData/cache/scratch', 'replay-gate-test-'))
    try {
      mkdirSync(join(root, 'stage'))
      const bytes = Buffer.from('%PDF-1.7 TEST ONLY archive file identity fixture')
      writeFileSync(join(root, 'stage', 'test.pdf'), bytes)
      const coverage = { rows: [{ month: '2026-01', channels: { Wind: {
        distributionRecords: [{ path: 'stage/test.pdf', sha256: createHash('sha256').update(bytes).digest('hex') }],
      } } }] }
      assert.deepEqual(gate.checkArchiveFiles(coverage, root, 'stage'), [])
      writeFileSync(join(root, 'stage', 'test.pdf'), 'TEST ONLY altered bytes')
      assert.ok(gate.checkArchiveFiles(coverage, root, 'stage').length)
      coverage.rows[0].channels.Wind.distributionRecords[0].path = '../not-an-archive.txt'
      assert.ok(gate.checkArchiveFiles(coverage, root, 'stage').length)
    } finally { rmSync(root, { recursive: true, force: true }) }
  })
  it('requires a nominated parent shortage receipt and physically hashed search artifacts', async () => {
    const gate = await import('./verify_replay_publish.mjs')
    assert.equal(typeof gate.checkShortageFiles, 'function', 'independent shortage readback is missing')
    const { mkdtempSync, mkdirSync, writeFileSync, rmSync } = await import('node:fs')
    const { join } = await import('node:path')
    const root = mkdtempSync(join(process.env.TMPDIR || 'C:/HermesData/cache/scratch', 'replay-shortage-test-'))
    try {
      mkdirSync(join(root, 'stage'))
      const search = Buffer.from('TEST ONLY full-month eligible search enumeration, actual total zero')
      writeFileSync(join(root, 'stage', 'search.txt'), search)
      const proof = { month: '2026-01', channel: '知识星球', actualEligibleTotal: 0, eligibleWorks: [],
        requiredTopicTag: '调研纪要', onlyOriginalPdf: true, searchExecuted: true, searchExhaustive: true,
        blocked: false, evidenceArtifacts: [{ path: 'stage/search.txt', sha256: createHash('sha256').update(search).digest('hex') }] }
      const bytes = Buffer.from(JSON.stringify(proof))
      writeFileSync(join(root, 'stage', 'parent-proof.json'), bytes)
      const sha256 = createHash('sha256').update(bytes).digest('hex')
      const coverage = { rows: [{ month: '2026-01', channels: { 知识星球: { archives: [],
        shortageEvidenceVerified: true, shortageEvidence: { proofSHA256: sha256, actualEligibleTotal: 0 } } } }] }
      assert.ok(gate.checkShortageFiles(coverage, root, [], 'stage').length)
      const binding = [{ path: 'stage/parent-proof.json', sha256 }]
      assert.deepEqual(gate.checkShortageFiles(coverage, root, binding, 'stage'), [])
      writeFileSync(join(root, 'stage', 'search.txt'), 'TEST ONLY mutated search artifact')
      assert.ok(gate.checkShortageFiles(coverage, root, binding, 'stage').length)
    } finally { rmSync(root, { recursive: true, force: true }) }
  })
  it('rejects private body fields, signed URLs, contacts and machine paths without echoing values', () => {
    assert.deepEqual(checkPublicPaths({ sourcePath: 'E:\\Private\\source.pdf', nested: [{ auditPath: '/Users/name/audit.json' }] }), ['sourcePath', 'auditPath'])
    assert.ok(checkPublicPaths({ fullText: 'private paid body', contacts: 'person@example.com', url: 'https://example.com/?token=secret' }).length)
  })
  it('binds public CI to the exact snapshots verified against local private archives', async () => {
    const gate = await import('./verify_replay_publish.mjs')
    assert.equal(typeof gate.checkPublicationReceipt, 'function', 'public receipt verification is missing')
    const c = fixture()
    const first = Buffer.from(JSON.stringify({ sources: [], reports: [] }))
    const second = Buffer.from(JSON.stringify({ monthlyCoverage: c, reports: library(c) }))
    const receipt = {
      schema: 'replay.publication.receipt.v1', verifiedAt: '2026-10-09T18:00:00+08:00',
      verificationMode: 'local-private-archive-readback', privateChecksPassed: true,
      verifiedArchiveEntries: library(c).length, acceptedCells: 24,
      artifactSHA256: {
        'src/data/historyReplay.json': createHash('sha256').update(first).digest('hex'),
        'src/data/historyReplayHawkishTransition.json': createHash('sha256').update(second).digest('hex'),
      },
    }
    assert.deepEqual(gate.checkPublicationReceipt(receipt, first, second), [])
    assert.ok(gate.checkPublicationReceipt(receipt, first, Buffer.concat([second, Buffer.from('\n')])).length)
    assert.ok(gate.checkPublicationReceipt({ ...receipt, privateChecksPassed: false }, first, second).length)
    assert.ok(gate.checkPublicationReceipt({ ...receipt, verifiedArchiveEntries: 1 }, first, second).length)
  })
})
