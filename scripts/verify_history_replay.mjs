import { createRequire } from 'node:module'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import assert from 'node:assert/strict'
import path from 'node:path'

const require = createRequire(import.meta.url)
const modulePath = process.env.PLAYWRIGHT_MODULE ?? 'playwright'
const { chromium } = require(modulePath)
const data = JSON.parse(await readFile(new URL('../src/data/historyReplay.json', import.meta.url), 'utf8'))
const url = process.argv[2] ?? 'http://127.0.0.1:5178/Macro/#history/easing-to-tightening/policy-reversal'
const out = process.argv[3] ?? 'C:/HermesData/cache/scratch/history-replay-qa'
await mkdir(out, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXE })
const errors = []
const result = { url, asOf: data.asOf, checks: [] }
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } })
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 })
    assert.equal(response.status(), 200)
    assert.equal(await page.locator('.replay-timeline li').count(), data.events.length)
    const disclosures = ['星球观点明细', 'Wind观点明细', '微信观点明细', '来源库 / 研报库明细']
    for (const label of disclosures) {
      const disclosure = page.locator(`details[aria-label="${label}"]`)
      assert.equal(await disclosure.count(), 1)
      assert.equal(await disclosure.evaluate(e => e.open), false, `${label} must default closed`)
      assert.equal(await disclosure.locator(':scope > section').isVisible(), false)
    }
    const framework = page.getByRole('figure', { name: '复盘方法框架' })
    assert.ok(await framework.isVisible())
    assert.equal(await framework.locator('li').count(), 4)
    assert.ok(await page.locator('.replay-heading').evaluate(e => e.nextElementSibling.classList.contains('replay-method-map')))
    const methodGeometry = await framework.locator('li').evaluateAll(items => items.map(e => {
      const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }
    }))
    for (const box of methodGeometry) assert.ok(box.width >= 70 && box.height >= 20)
    for (let i = 0; i < methodGeometry.length; i++) for (let j = i + 1; j < methodGeometry.length; j++) {
      const a = methodGeometry[i], b = methodGeometry[j]
      assert.ok(Math.min(a.x + a.width, b.x + b.width) <= Math.max(a.x, b.x) || Math.min(a.y + a.height, b.y + b.height) <= Math.max(a.y, b.y), 'Framework boxes must not overlap')
    }
    const analysis = page.getByRole('region', { name: '综合市场分析' })
    assert.ok(await analysis.isVisible())
    assert.equal(await analysis.locator('.replay-analysis-topic').count(), data.marketAnalysis.sections.length)
    assert.ok(await analysis.evaluate(e => Boolean(e.compareDocumentPosition(document.querySelector('.replay-timeline')) & Node.DOCUMENT_POSITION_FOLLOWING)))
    for (const section of data.marketAnalysis.sections) {
      const topic = analysis.locator('.replay-analysis-topic').filter({ has: page.getByRole('heading', { name: section.title, exact: true }) })
      const text = await topic.innerText()
      for (const key of ['judgement', 'expectation', 'reality', 'mechanism', 'divergence', 'implication', 'validation']) assert.ok(text.includes(section[key]))
      for (const id of section.reportIds) assert.ok(text.includes(data.reports.find(r => r.id === id).title))
      assert.ok(!text.includes('研报未在截止日前核验'))
    }
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1))
    await page.screenshot({ path: path.join(out, `collapsed-top-${width}.png`), fullPage: false })
    for (const label of disclosures) {
      const disclosure = page.locator(`details[aria-label="${label}"]`)
      await disclosure.locator(':scope > summary').click()
      assert.equal(await disclosure.evaluate(e => e.open), true)
      assert.ok(await disclosure.locator(':scope > section').isVisible())
    }
    assert.equal(await page.locator('.replay-library-grid > div').first().locator('.replay-source').count(), data.sources.filter(s => /^https?:\/\//i.test(s.url)).length)
    assert.equal(await page.locator('.replay-library-grid > div').last().locator('.replay-source').count(), data.reports.length)
    const windEvidence = data.windResearchEvidence ?? []
    const wechatEvidence = data.wechatResearchEvidence ?? []
    assert.equal(await page.locator('.replay-audit-card').count(), data.researchEvidence.length + windEvidence.length + wechatEvidence.length)
    const starRegion = page.getByRole('region', { name: '星球观点独立追溯' })
    const windRegion = page.getByRole('region', { name: 'Wind观点独立追溯' })
    assert.equal(await starRegion.locator('.replay-audit-card').count(), data.researchEvidence.length)
    if (windEvidence.length) {
      assert.equal(await windRegion.locator('.replay-audit-card').count(), windEvidence.length)
      assert.ok((await windRegion.innerText()).includes('事后报告不倒填会前预期'))
      for (const view of windEvidence) {
        const card = windRegion.locator('.replay-audit-card').filter({ hasText: view.claim })
        assert.equal(await card.count(), 1)
        const text = await card.innerText()
        for (const field of [view.expressedAt, view.localPath, view.evidenceExcerpt, view.status]) {
          assert.ok(text.includes(field), `Missing audited Wind field: ${field}`)
        }
        if (!view.reality) assert.ok(text.includes('尚无已核验的对应现实，待验证。'))
      }
    }
    const wechatRegion = page.getByRole('region', { name: '微信观点独立追溯' })
    assert.equal(await wechatRegion.locator('.replay-audit-card').count(), wechatEvidence.length)
    if (data.wechatCoverage) {
      const coverage = page.getByRole('region', { name: '微信公众号来源覆盖' })
      assert.ok(await coverage.isVisible())
      const coverageText = await coverage.innerText()
      assert.match(coverageText, new RegExp(`${data.wechatCoverage.totalArticles}\\s*篇`))
      assert.match(coverageText, new RegExp(`${data.wechatCoverage.totalOpinions}\\s*条`))
      for (const row of data.wechatCoverage.actualAccounts) assert.ok(coverageText.includes(row.accountActual))
      const audit = coverage.locator('details[aria-label="公众号候选检索审计"]')
      assert.equal(await audit.evaluate(e => e.open), false)
      await audit.locator(':scope > summary').click()
      assert.equal(await audit.evaluate(e => e.open), true)
      const auditText = await audit.innerText()
      for (const row of data.wechatCoverage.requestedAccounts) {
        assert.ok(auditText.includes(row.accountRequested))
        assert.ok(auditText.includes(row.status))
      }
      await audit.locator(':scope > summary').click()
      assert.equal(await audit.evaluate(e => e.open), false)
      await coverage.locator('h3').evaluate(e => e.scrollIntoView({ block: 'start' }))
      await page.evaluate(() => window.scrollBy(0, -90))
      await page.screenshot({ path: path.join(out, `wechat-coverage-${width}.png`), fullPage: false })
    }
    for (const view of wechatEvidence) {
      const card = wechatRegion.locator('.replay-audit-card').filter({ hasText: view.claim })
      const text = await card.innerText()
      for (const field of [view.expressedAt, view.localPath, view.evidenceExcerpt, view.status, `证据段：${view.pages.join('、')}`]) assert.ok(text.includes(field))
      assert.ok(!text.includes(`证据页：${view.pages.join('、')}`))
      if (!view.reality) assert.ok(text.includes('尚无已核验的对应现实，待验证。'))
    }
    assert.equal(await page.locator('.replay-path-chart svg').count(), 2)
    assert.equal(await page.locator('.replay-path-chart svg').first().locator('path[data-series-id]').count(), 2)
    const realityLinks = await page.locator('.replay-audit-card a').evaluateAll(items => items.map(a => a.getAttribute('href')))
    const publicEvidenceUrls = new Set(data.sources.map(source => source.url).filter(url => /^https?:\/\//i.test(url)))
    assert.ok(realityLinks.every(url => publicEvidenceUrls.has(url)), 'Opinion cards may only link registered public reality sources')
    assert.equal(await page.locator('.replay-audit-card a[download]').count(), 0)
    const knownReportDate = report => report.filenameDate !== undefined ? report.filenameDate : report.publicationDate !== undefined ? report.publicationDate : report.date
    const library = page.locator('.replay-library-grid > div').last()
    for (const report of data.reports.filter(r => r.filenameDate !== undefined)) {
      const card = library.locator('.replay-source').filter({ hasText: report.path })
      const text = await card.innerText()
      assert.ok(text.includes(report.filenameDate ? `研究归档日期（文件名优先）：${report.filenameDate}` : '正文发布日期：未知'))
      assert.ok(text.includes(`平台发帖日：${report.postDate}`))
      if (report.dateConflict) assert.ok(text.includes('日期冲突：文件名日期与平台日期不一致'))
    }
    const geometry = await page.evaluate(() => {
      const overlap = [...document.querySelectorAll('.replay-panel > header')].filter(header => {
        const heading = header.querySelector('h2')?.getBoundingClientRect()
        const other = header.querySelector('span,label')?.getBoundingClientRect()
        return heading && other && Math.min(heading.right, other.right) > Math.max(heading.left, other.left) + 1 && Math.min(heading.bottom, other.bottom) > Math.max(heading.top, other.top) + 1
      }).length
      const cardOverlaps = [...document.querySelectorAll('.replay-analysis-topic h3,.replay-audit-card h3')].filter(h => {
        const a = h.getBoundingClientRect(), b = h.nextElementSibling?.getBoundingClientRect()
        return b && a.width > 0 && b.width > 0 && b.top < a.bottom - 1
      }).length
      return { clientWidth: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth, headerOverlaps: overlap, cardOverlaps }
    })
    assert.ok(geometry.scrollWidth <= geometry.clientWidth + 1, JSON.stringify(geometry))
    assert.equal(geometry.headerOverlaps, 0)
    assert.equal(geometry.cardOverlaps, 0)
    const timelineGeometry = await page.locator('.replay-timeline').evaluate(e => {
      const header = e.querySelector('header').getBoundingClientRect()
      const body = e.querySelector('ol').getBoundingClientRect()
      return { headerHeight: header.height, headerBottom: header.bottom, bodyTop: body.top }
    })
    assert.ok(timelineGeometry.headerHeight < 120, 'Timeline header must not inherit the older page grid')
    assert.ok(timelineGeometry.bodyTop >= timelineGeometry.headerBottom - 1, 'Timeline events belong below their heading')
    const reportLinks = await page.locator('.replay-library-grid > div').last().locator('a').count()
    assert.equal(reportLinks, 0, 'Authorized PDF paths must not be published download links')
    await page.screenshot({ path: path.join(out, `desktop-${width}.png`), fullPage: false })
    if (windEvidence.length) {
      await windRegion.scrollIntoViewIfNeeded()
      await page.screenshot({ path: path.join(out, `wind-evidence-${width}.png`), fullPage: false })
    }
    if (wechatEvidence.length) {
      await wechatRegion.scrollIntoViewIfNeeded()
      await page.screenshot({ path: path.join(out, `wechat-evidence-${width}.png`), fullPage: false })
    }
    await page.getByLabel('按日期截止查看').fill('2026-09-16')
    assert.equal(await page.locator('.replay-timeline li').count(), data.events.filter(e => e.date <= '2026-09-16').length)
    assert.equal(await page.locator('.replay-interpretation').count(), 0)
    assert.equal(await page.locator('.replay-audit-card').count(), 0)
    assert.equal(await page.getByRole('region', { name: '微信公众号来源覆盖' }).count(), 0)
    assert.equal(await page.locator('.replay-library-grid > div').last().locator('.replay-source').count(), data.reports.filter(r => r.historicalAsOfEligible !== false && knownReportDate(r) && knownReportDate(r) <= '2026-09-16').length)
    assert.equal(await page.locator('.replay-market-analysis').count(), 0)
    for (const label of disclosures.slice(0, 3)) assert.equal(await page.locator(`details[aria-label="${label}"]`).count(), 0)
    assert.ok(await framework.isVisible())
    assert.equal(await page.locator('.replay-path-chart svg').count(), 1, 'Treasury first-release dates are not confirmed')
    for (const item of data.marketPaths.series) {
      const eligible = item.observations.filter(o => o.date <= '2026-09-16' && o.historicalAsOfEligible === true && o.releaseDate && o.releaseDate <= '2026-09-16')
      const rows = page.getByRole('table', { name: `${item.title}观测记录`, includeHidden: true }).locator('tbody tr')
      assert.equal(await rows.count(), eligible.length)
    }
    const transcript = data.sources.find(s => s.id === 'public-4')
    assert.equal(await page.locator('.history-replay').getByRole('link', { name: `${transcript.title} ↗`, exact: true }).count(), 0)
    const text = await page.locator('.history-replay').innerText()
    assert.ok(!text.includes('总PCE较主席先前估计低0.2个百分点'), 'Future PCE should be excluded')
    assert.ok(!text.includes('第三次估计将二季度GDP'), 'Future GDP vintage should be excluded')
    await page.getByLabel('按日期截止查看').fill('2026-09-30')
    assert.equal(await page.locator('.replay-audit-card').count(), 0, 'Current Wind comparisons must not leak into historical mode')
    assert.equal(await page.locator('.history-replay').getByRole('link', { name: `${transcript.title} ↗`, exact: true }).count(), 0, 'FINAL first-release date is still unknown on 9/30')
    await page.getByRole('button', { name: '恢复资料截止日' }).click()
    assert.equal(await page.locator('.replay-timeline li').count(), data.events.length)
    assert.ok(await page.getByRole('region', { name: '综合市场分析' }).isVisible())
    for (const label of disclosures.slice(0, 3)) assert.equal(await page.locator(`details[aria-label="${label}"]`).evaluate(e => e.open), false)
    await page.getByRole('searchbox', { name: '检索资料' }).fill('宽松回撤')
    assert.ok(await page.locator('.replay-library-grid > div').last().locator('.replay-source').count() >= 1)
    await page.getByRole('searchbox', { name: '检索资料' }).fill('')
    await page.getByRole('button', { name: '返回父阶段复盘' }).click()
    assert.ok(page.url().endsWith('#history/easing-to-tightening'))
    assert.equal(await page.locator('.subperiod-list article').first().locator('small').first().innerText(), '2026.09—至今')
    assert.equal(await page.getByRole('button', { name: /进入.*研究工作台/ }).count(), 2)
    assert.equal(await page.getByRole('button', { name: '进入鹰派换届与反转酝酿研究工作台', exact: true }).count(), 1)
    await page.getByRole('button', { name: '进入重启加息：政策反转研究工作台' }).click()
    assert.ok(page.url().endsWith('#history/easing-to-tightening/policy-reversal'))
    await page.goBack()
    assert.ok(await page.getByRole('heading', { name: '细分时段复盘' }).isVisible())
    await page.goForward()
    assert.ok(await page.getByRole('heading', { name: '预期 → 现实：事件时间轴' }).isVisible())
    result.checks.push({ width, geometry, methodGeometry, timelineGeometry, eventCount: data.events.length, sourceCount: data.sources.length, reportCount: data.reports.length, evidenceCount: data.researchEvidence.length, windEvidenceCount: windEvidence.length, wechatEvidenceCount: wechatEvidence.length, totalEvidenceCount: data.researchEvidence.length + windEvidence.length + wechatEvidence.length, wechatBodyCount: data.wechatCoverage?.totalArticles, requestedWechatAccounts: data.wechatCoverage?.requestedAccounts.length, actualWechatAccounts: data.wechatCoverage?.actualAccounts.length, wechatCoverageAudit: data.wechatCoverage ? 'PASS' : 'NOT_PRESENT', analysisTopicCount: data.marketAnalysis.sections.length, chartCount: 2, defaultCollapsedAndExpand: 'PASS', frameworkAndAnalysisPlacement: 'PASS', filenameDatePriorityAndConflicts: 'PASS', wechatOriginalParagraphEvidence: 'PASS', historicalUnknownDateExclusion: 'PASS', windAuditedOpinionsAndHistoricalExclusion: 'PASS', finalTranscriptExclusion: 'PASS', cutoffAndSearch: 'PASS', parentChildAndHistory: 'PASS', localPdfPrivacy: 'PASS' })
    await page.close()
  }
  assert.deepEqual(errors, [])
  result.status = 'PASS'
  result.consoleErrors = errors
  await writeFile(path.join(out, 'results.json'), JSON.stringify(result, null, 2))
  console.log(JSON.stringify(result, null, 2))
} finally { await browser.close() }
