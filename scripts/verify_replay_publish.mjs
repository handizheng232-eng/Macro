// Prevent an incomplete or private-source replay from reaching GitHub Pages.
import { readFileSync, readdirSync, existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve, relative, isAbsolute, sep, dirname } from 'node:path'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'

const channels = ['知识星球', 'Wind', '微信公众号']
const months = Array.from({ length: 8 }, (_, index) => `2026-${String(index + 1).padStart(2, '0')}`)
const archiveHash = /^[0-9a-f]{64}$/i
const absoluteLocalPath = /^(?:[a-z]:[\\/]|\\\\|\/Users\/|\/home\/|\/mnt\/)/i

const requiredCounts = { 知识星球: 20, Wind: 10, 微信公众号: 5 }
function qualityValid(item, channel) {
  const q = item?.sourceQuality
  if (!q || !['parentLedgerVerified', 'originalBodyVerified', 'datePolicyVerified', 'scopeVerified'].every(k => q[k] === true)) return false
  if (channel === '知识星球') return q.tag === '调研纪要' && ['original_audio_transcript_pdf', 'platform_original_full_speech_transcript', 'platform_original_continuous_transcript'].includes(q.versionType)
  if (channel === 'Wind') return q.versionType === 'institutional_research_pdf' && q.printedPublicationVerified === true
  return q.versionType === 'official_original_article_text' && q.officialHeaderVerified === true && typeof q.account === 'string' && q.account.length > 0
}
function dateValid(value, month) {
  if (value === month) return true
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && value.startsWith(month + '-') &&
    !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value
}
function reportDate(report, channel) {
  return channel === '知识星球' ? report.filenameDate :
    channel === 'Wind' && report.publicationDate === null && report.publicationDatePrecision === 'month' ?
      report.verifiedPublicationMonth : report.publicationDate
}
export function checkCoverage(coverage, reports) {
  const failures = []
  if (!coverage || coverage.startDate !== '2026-01-01' || coverage.endDate !== '2026-08-31' ||
      coverage.requiredCells !== 24 || coverage.acceptedCells !== 24 || coverage.complete !== true) {
    failures.push('overall Jan–Aug coverage is not complete')
  }
  if (!Array.isArray(coverage?.rows) || coverage.rows.length !== 8 ||
      coverage.rows.some((row, index) => row.month !== months[index])) failures.push('month rows are not exactly January through August')
  const byId = new Map((Array.isArray(reports) ? reports : []).map(r => [r.id, r]))
  if (!Array.isArray(reports) || byId.size !== reports.length) failures.push('missing or duplicate library identities')
  let accepted = 0
  for (const month of months) {
    const row = coverage?.rows?.find(item => item.month === month)
    if (!row || Object.keys(row.channels ?? {}).length !== 3 || Object.keys(row.channels ?? {}).some(c => !channels.includes(c))) {
      failures.push(`${month}: channels are not exactly the required three`)
    }
    for (const channel of channels) {
      const cell = row?.channels?.[channel]
      const archives = Array.isArray(cell?.archives) ? cell.archives : []
      const distribution = Array.isArray(cell?.distributionRecords) ? cell.distributionRecords : []
      const workIds = new Set(distribution.map(a => a.independentWorkId))
      const count = workIds.size
      const proof = cell?.shortageEvidence
      const shortage = channel === '知识星球' && cell?.shortageEvidenceVerified === true &&
        cell.searchExhaustive === true && cell.searchExecuted === true &&
        proof?.actualEligibleTotal === count && Number.isInteger(count) && count >= 0 && count < 20 &&
        proof.month === month && proof.channel === channel && proof.requiredTopicTag === '调研纪要' &&
        proof.onlyOriginalPdf === true && proof.searchExecuted === true && proof.searchExhaustive === true &&
        proof.blocked === false && archiveHash.test(proof.proofSHA256 ?? '')
      const recordValid = a => {
        const report = byId.get(a.reportId)
        const actualChannel = report?.channel === '微信' ? '微信公众号' : report?.channel
        return report && actualChannel === channel && archiveHash.test(a.sha256 ?? '') &&
          a.sha256 === (report.sha256 ?? report.bodySha256) && a.path === report.path &&
          dateValid(a.date, month) && (a.date !== month || channel === 'Wind' &&
            report.publicationDate === null && report.publicationDatePrecision === 'month' && report.verifiedPublicationMonth === month) &&
          a.date === reportDate(report, channel) &&
          typeof a.independentWorkId === 'string' && a.independentWorkId.length > 0 &&
          a.independentWorkId === report.independentWorkId && qualityValid(a, channel) && qualityValid(report, channel)
      }
      const archiveValid = cell && Number.isInteger(cell.bodyCount) && cell.bodyCount === count &&
        cell.verifiedBodyCount === count && cell.archiveEntries === distribution.length &&
        (count > 0 || shortage) && archives.length === count &&
        new Set(archives.map(a => a.independentWorkId)).size === count &&
        new Set(archives.map(a => a.sha256)).size === count &&
        new Set(distribution.map(a => a.reportId)).size === distribution.length &&
        archives.every(recordValid) && distribution.every(recordValid) &&
        archives.every(a => distribution.some(d => d.reportId === a.reportId && d.sha256 === a.sha256))
      const accounts = new Set(distribution.map(a => a.sourceQuality?.account).filter(Boolean))
      const blocked = cell?.blocked === true || /blocked|受阻/i.test(cell?.status ?? '')
      const quotaValid = cell?.requiredCount === requiredCounts[channel] && (count >= requiredCounts[channel] || shortage) &&
        !blocked && (channel !== '微信公众号' || accounts.size >= 2 && cell.accountCount === accounts.size) &&
        cell?.acceptanceBasis === (count >= requiredCounts[channel] ? 'minimum_verified_originals' : 'verified_actual_eligible_total')
      if (!archiveValid) failures.push(`${month} ${channel}: archive missing, quality invalid or library/count mismatch`)
      if (!quotaValid) failures.push(`${month} ${channel}: quota not met (${count}/${requiredCounts[channel]}); no verified actual-shortage proof`)
      if (archiveValid && quotaValid) {
        accepted++
        if (cell.accepted !== true || cell.quotaAccepted !== true) failures.push(`${month} ${channel}: acceptance flag not verified`)
      }
    }
  }
  if (coverage?.acceptedCells !== accepted) failures.push(`accepted cell total disagrees with recomputation (${accepted}/24)`)
  return failures
}

export function checkArchiveFiles(coverage, root, stageRelative = '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08') {
  const failures = []
  const stage = resolve(root, stageRelative)
  for (const row of coverage?.rows ?? []) for (const [channel, cell] of Object.entries(row.channels ?? {})) {
    for (const archive of cell.distributionRecords ?? []) {
      const fail = () => failures.push(`${row.month} ${channel}: private archive file missing, out of stage or bytes/SHA invalid`)
      if (typeof archive.path !== 'string' || isAbsolute(archive.path) || absoluteLocalPath.test(archive.path)) { fail(); continue }
      const path = resolve(root, archive.path)
      const local = relative(stage, path)
      if (local.startsWith('..' + sep) || local === '..' || isAbsolute(local) || !/\.(pdf|txt)$/i.test(path)) { fail(); continue }
      try {
        const bytes = readFileSync(path)
        if (!bytes.length || createHash('sha256').update(bytes).digest('hex') !== archive.sha256 ||
            (channel !== '微信公众号' && !bytes.subarray(0, 1024).includes(Buffer.from('%PDF-')))) fail()
      } catch { fail() }
    }
  }
  return failures
}

export function checkShortageFiles(coverage, root, bindings = [], stageRelative = '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08') {
  const failures = []
  const stage = resolve(root, stageRelative)
  const locate = value => {
    if (typeof value !== 'string') throw new Error('bad proof path')
    let path = resolve(root, value)
    if (!isAbsolute(value) && !absoluteLocalPath.test(value) && !existsSync(path)) path = resolve(stage, value)
    const local = relative(stage, path)
    if (local.startsWith('..' + sep) || local === '..' || isAbsolute(local) ||
        /(?:credential|authlog|cookie|token|password|storageState|profile)/i.test(local)) throw new Error('out of proof scope')
    return path
  }
  for (const row of coverage?.rows ?? []) for (const [channel, cell] of Object.entries(row.channels ?? {})) {
    if (cell.shortageEvidenceVerified !== true) continue
    try {
      const binding = bindings.find(b => b.sha256 === cell.shortageEvidence?.proofSHA256)
      if (!binding) throw new Error('no nominated parent proof')
      const bytes = readFileSync(locate(binding.path))
      if (createHash('sha256').update(bytes).digest('hex') !== binding.sha256) throw new Error('proof SHA drift')
      const proof = JSON.parse(bytes.toString('utf8'))
      const total = proof.actualEligibleTotal
      if (channel !== '知识星球' || proof.channel !== channel || proof.month !== row.month ||
          proof.requiredTopicTag !== '调研纪要' || proof.onlyOriginalPdf !== true || proof.searchExecuted !== true ||
          proof.searchExhaustive !== true || proof.blocked !== false || !Number.isInteger(total) || total < 0 || total >= 20 ||
          total !== cell.shortageEvidence.actualEligibleTotal || !Array.isArray(proof.eligibleWorks) ||
          proof.eligibleWorks.length !== total || !Array.isArray(proof.evidenceArtifacts) || !proof.evidenceArtifacts.length) throw new Error('bad independent shortage proof')
      for (const artifact of proof.evidenceArtifacts) {
        if (!archiveHash.test(artifact.sha256 ?? '') || createHash('sha256').update(readFileSync(locate(artifact.path))).digest('hex') !== artifact.sha256) throw new Error('search artifact SHA drift')
      }
      const identity = a => JSON.stringify([a.independentWorkId, a.sha256, locate(a.path), a.date])
      const expected = proof.eligibleWorks.map(identity).sort()
      const obtained = (cell.archives ?? []).map(identity).sort()
      if (new Set(proof.eligibleWorks.map(a => a.independentWorkId)).size !== total ||
          JSON.stringify(expected) !== JSON.stringify(obtained)) throw new Error('eligible total not fully obtained')
    } catch {
      failures.push(`${row.month} ${channel}: actual-shortage parent proof not nominated, invalid or search artifacts changed`)
    }
  }
  return failures
}

export function checkPublicPaths(payload) {
  const failures = []
  function visit(value, key = '') {
    if (Array.isArray(value)) {
      value.forEach(item => visit(item, key))
    } else if (value && typeof value === 'object') {
      Object.entries(value).forEach(([name, item]) => {
        if (/^(fullText|pypdfText|pymupdfText|pageText|rawHTML|renderedHTML|contacts?|privateAudit|privateSourceScreenshot|signURL)$/i.test(name)) failures.push(name)
        else visit(item, name)
      })
    } else if (typeof value === 'string' && (absoluteLocalPath.test(value) ||
        /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(value) ||
        /https?:[^\s]*[?&](?:token|access_token|signature|sign|auth|X-Amz-Signature)=/i.test(value))) {
      failures.push(key)
    }
  }
  visit(payload)
  return failures
}

export function checkPublicationReceipt(receipt, firstBytes, secondBytes) {
  const failures = []
  const hash = bytes => createHash('sha256').update(bytes).digest('hex')
  try {
    const second = JSON.parse(secondBytes.toString('utf8'))
    const entries = (second.monthlyCoverage?.rows ?? []).reduce((sum, row) => sum +
      Object.values(row.channels ?? {}).reduce((n, cell) => n + (cell.distributionRecords?.length ?? 0), 0), 0)
    if (receipt?.schema !== 'replay.publication.receipt.v1' ||
        receipt.verificationMode !== 'local-private-archive-readback' || receipt.privateChecksPassed !== true ||
        !receipt.verifiedAt || Number.isNaN(Date.parse(receipt.verifiedAt)) ||
        receipt.verifiedArchiveEntries !== entries || receipt.acceptedCells !== 24 ||
        receipt.artifactSHA256?.['src/data/historyReplay.json'] !== hash(firstBytes) ||
        receipt.artifactSHA256?.['src/data/historyReplayHawkishTransition.json'] !== hash(secondBytes)) {
      failures.push('public receipt is absent, stale or not bound to locally verified snapshots')
    }
    failures.push(...checkCoverage(second.monthlyCoverage, second.reports))
  } catch {
    failures.push('public receipt or bound snapshot is malformed')
  }
  return failures
}

function receiptPath(value, root) {
  const target = resolve(root, value)
  const local = relative(root, target)
  if (!local.startsWith('release' + sep) || !local.endsWith('.json')) throw new Error('Receipt must be a JSON file inside release/')
  return target
}

function checkDist(dir) {
  const failures = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) failures.push(...checkDist(path))
    else if (/\.(pdf|zip)$/i.test(entry.name)) failures.push('private document included in Pages artifact')
  }
  return failures
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const root = fileURLToPath(new URL('../', import.meta.url))
  const firstBytes = readFileSync(join(root, 'src/data/historyReplay.json'))
  const secondBytes = readFileSync(join(root, 'src/data/historyReplayHawkishTransition.json'))
  const first = JSON.parse(firstBytes.toString('utf8'))
  const second = JSON.parse(secondBytes.toString('utf8'))
  const shortageBindings = []
  let publicReceiptPath, writeReceiptPath
  for (let index = 2; index < process.argv.length; index++) {
    if (['--public-receipt', '--write-public-receipt'].includes(process.argv[index])) {
      const flag = process.argv[index]
      if (!process.argv[index + 1]) throw new Error('Receipt argument missing')
      const target = receiptPath(process.argv[++index], root)
      if (flag === '--public-receipt') publicReceiptPath = target
      else writeReceiptPath = target
      continue
    }
    if (process.argv[index] !== '--parent-source-manifest' || !process.argv[index + 1]) throw new Error('Unknown or missing publication-gate argument')
    const candidate = process.argv[++index]
    const stage = resolve(root, '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08')
    let path = isAbsolute(candidate) ? candidate : resolve(root, candidate)
    if (!existsSync(path) && !isAbsolute(candidate)) path = resolve(stage, candidate)
    const local = relative(stage, path)
    if (local.startsWith('..' + sep) || local === '..' || isAbsolute(local)) throw new Error('Manifest outside declared replay stage')
    const manifest = JSON.parse(readFileSync(path, 'utf8'))
    shortageBindings.push(...(manifest.shortageProofs ?? []))
  }
  if (publicReceiptPath && writeReceiptPath) throw new Error('A receipt cannot be created from public-only verification')
  const receipt = publicReceiptPath ? JSON.parse(readFileSync(publicReceiptPath, 'utf8')) : null
  const failures = [...checkCoverage(second.monthlyCoverage, second.reports), ...checkPublicPaths(first), ...checkPublicPaths(second),
                    ...(receipt ? [...checkPublicationReceipt(receipt, firstBytes, secondBytes), ...checkPublicPaths(receipt)] :
                      [...checkArchiveFiles(second.monthlyCoverage, root), ...checkShortageFiles(second.monthlyCoverage, root, shortageBindings)]),
                    ...checkDist(join(root, 'dist'))]
  if (failures.length) {
    console.error(`Publication blocked: ${failures.length} unmet checks;`, failures.slice(0, 30))
    process.exitCode = 1
  } else {
    if (writeReceiptPath) {
      const records = second.monthlyCoverage.rows.flatMap(row => Object.values(row.channels).flatMap(cell => cell.distributionRecords))
      const output = { schema: 'replay.publication.receipt.v1', verifiedAt: new Date().toISOString(),
        verificationMode: 'local-private-archive-readback', privateChecksPassed: true,
        verifiedArchiveEntries: records.length, acceptedCells: second.monthlyCoverage.acceptedCells,
        artifactSHA256: { 'src/data/historyReplay.json': createHash('sha256').update(firstBytes).digest('hex'),
          'src/data/historyReplayHawkishTransition.json': createHash('sha256').update(secondBytes).digest('hex') },
        scope: 'Private archive bytes/SHA checked locally; public CI checks these exact snapshots and never claims to reread private originals.' }
      mkdirSync(dirname(writeReceiptPath), { recursive: true })
      writeFileSync(writeReceiptPath, JSON.stringify(output, null, 2) + '\n')
    }
    console.log(receipt ? 'Publication gate: public snapshots match the local private-verification receipt; CI public checks passed' :
      'Publication gate: Jan–Aug monthly evidence, public paths and local private artifact files verified')
  }
}
