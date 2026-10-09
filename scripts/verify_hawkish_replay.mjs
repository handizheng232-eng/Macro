import { createRequire } from 'node:module'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE ?? 'playwright')
const data = JSON.parse(await readFile(new URL('../src/data/historyReplayHawkishTransition.json', import.meta.url), 'utf8'))
const url = process.argv[2] ?? 'http://127.0.0.1:5178/Macro/#history/easing-to-tightening/hawkish-transition'
const out = process.argv[3] ?? 'C:/HermesData/cache/scratch/hawk-replay-qa'
await mkdir(out, { recursive: true })
assert.equal(data.endDate, '2026-08-31')
assert.equal(data.marketAnalysis?.sections.length, 5, 'Cannot verify an unfinished research skeleton')
assert.ok(data.events.length && data.sources.length)
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXE })
const errors = [], result = { url, asOf: data.asOf, checks: [] }
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } })
    page.on('pageerror', e => errors.push(e.message))
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
    assert.equal((await page.goto(url, { waitUntil: 'networkidle' })).status(), 200)
    await page.getByRole('heading', { name: data.title, exact: true }).waitFor()
    const workbench = page.locator('article.history-replay')
    assert.equal(await workbench.getAttribute('aria-label'), data.workbenchLabel)
    assert.match(await page.locator('.replay-heading').innerText(), /2026-01-01[\s\S]*2026-08-31/)
    assert.doesNotMatch(await page.locator('.replay-heading').innerText(), /终点未形成/)
    assert.equal(await page.locator('.replay-timeline li').count(), data.events.length)
    assert.equal(await page.locator('.replay-analysis-topic').count(), 5)
    assert.equal(await page.locator('.replay-path-chart svg').count(), 2)
    assert.equal(await page.locator('path[data-series-id]').count(), 3)
    const library = page.locator('details[aria-label="来源库 / 研报库明细"]')
    assert.equal(await library.evaluate(e => e.open), false)
    await library.locator(':scope > summary').click()
    const comparisons = page.locator('details[aria-label="逐条预期现实对照"]')
    assert.equal(await comparisons.evaluate(e => e.open), false)
    await comparisons.locator(':scope > summary').click()
    assert.equal(await comparisons.locator('tbody tr').count(), data.realityComparisons.length)
    assert.ok(await comparisons.locator(':scope > section > .replay-notice').isVisible())
    assert.match(await comparisons.locator(':scope > section > .replay-notice').innerText(), /实时预测胜率/)
    await comparisons.locator(':scope > section').scrollIntoViewIfNeeded()
    await page.screenshot({ path: path.join(out, `comparisons-${width}.png`) })
    assert.ok((await page.evaluate(() => document.documentElement.scrollWidth)) <= width + 1)
    await comparisons.locator(':scope > summary').click()
    await library.locator(':scope > summary').click()
    assert.ok(await page.getByRole('figure', { name: '复盘方法框架' }).isVisible())
    const channels = [['星球', 'researchEvidence'], ['Wind', 'windResearchEvidence'], ['微信', 'wechatResearchEvidence']]
    if (data.localResearchEvidence?.length) channels.push(['本地研报', 'localResearchEvidence'])
    for (const [channel, field] of channels) {
      if (channel === '本地研报') await library.locator(':scope > summary').click()
      const disclosure = page.locator(`details[aria-label="${channel}观点明细"]`)
      assert.equal(await disclosure.evaluate(e => e.open), false)
      await disclosure.locator(':scope > summary').click()
      assert.equal(await disclosure.evaluate(e => e.open), true)
      assert.equal(await disclosure.locator('.replay-audit-card').count(), data[field]?.length ?? 0)
      await disclosure.locator(':scope > summary').click()
      if (channel === '本地研报') await library.locator(':scope > summary').click()
    }
    assert.equal(await library.evaluate(e => e.open), false)
    await library.locator(':scope > summary').click()
    assert.equal(await page.locator('.replay-library-grid > div:nth-child(2) .replay-source').count(), data.reports.length)
    assert.equal(await page.locator('a[download]').count(), 0)
    await library.locator(':scope > summary').click()
    const geometry = await page.evaluate(() => {
      const rects = [...document.querySelectorAll('.replay-analysis-topic')].map(e => e.getBoundingClientRect())
      return { clientWidth: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth,
        overlaps: rects.slice(1).filter((r, i) => r.top < rects[i].bottom - 1).length }
    })
    assert.ok(geometry.scrollWidth <= geometry.clientWidth + 1)
    assert.equal(geometry.overlaps, 0)
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.screenshot({ path: path.join(out, `top-${width}.png`) })
    const cutoff = '2026-05-21'
    await page.locator('#replay-cutoff').fill(cutoff)
    assert.equal(await page.getByRole('region', { name: '综合市场分析', exact: true }).count(), 0)
    assert.equal(await page.locator('details[aria-label="逐条预期现实对照"]').count(), 0)
    assert.equal(await page.locator('path[data-series-id="DGS2"]').count(), 0)
    for (const [channel] of channels) assert.equal(await page.locator(`details[aria-label="${channel}观点明细"]`).count(), 0)
    assert.equal(await page.locator('.replay-timeline li').count(), data.events.filter(e => e.date <= cutoff && e.historicalAsOfEligible !== false && (e.availableFrom || e.date) <= cutoff).length)
    assert.equal(await page.getByRole('heading', { name: '总统正式提名Warsh', exact: true }).count(), 0)
    await page.getByRole('button', { name: '恢复资料截止日' }).click()
    assert.equal(await page.locator('.replay-analysis-topic').count(), 5)
    await page.getByRole('button', { name: '返回父阶段复盘' }).click()
    await page.getByRole('heading', { name: '降息起步后的双向政策时代', exact: true }).waitFor()
    await page.goBack()
    await page.getByRole('heading', { name: data.title, exact: true }).waitFor()
    result.checks.push({ width, geometry, events: data.events.length, reports: data.reports.length,
      sources: data.sources.length, themes: 5, pairs: data.realityComparisons.length,
      uniqueDocuments: data.archiveCoverage.uniqueDocuments, closedStage: 'PASS', historicalBoundary: 'PASS',
      disclosures: 'PASS', parentBack: 'PASS', originalStageRoute: '#history/easing-to-tightening/policy-reversal' })
    await page.close()
  }
  assert.deepEqual(errors, [])
  result.status = 'PASS'; result.consoleErrors = errors
  await writeFile(path.join(out, 'results.json'), JSON.stringify(result, null, 2) + '\n')
  console.log(JSON.stringify(result))
} finally { await browser.close() }
