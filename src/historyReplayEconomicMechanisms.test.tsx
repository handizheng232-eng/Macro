import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayRenewedEasingQtEnd.json'
import { createHash } from 'node:crypto'
import baseline from './data/historyReplayEconomicMechanisms02.fixture.json'

afterEach(cleanup)
it('binds each monthly economic summary paragraph to readable sources and unloads them in strict history', () => {
  const topics = data.marketAnalysis.sections.filter(s => ['inflation-vintages', 'demand-supply'].includes(s.id))
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  for (const topic of topics) {
    expect(topic.periodSummary.paragraphs).toHaveLength(12)
    expect(topic.periodSummary.paragraphs.map(p => p.match(/^\d+月/)?.[0])).toEqual(['9月','9月','9月','10月','10月','10月','11月','11月','11月','12月','12月','12月'])
    const root = container.querySelector(`[data-period-summary="${topic.id}"]`)!
    const paragraphs = root.querySelectorAll('[data-summary-paragraph]')
    expect(paragraphs).toHaveLength(12)
    paragraphs.forEach((node, index) => {
      expect(node.querySelector('p')?.textContent).toBe(topic.periodSummary.paragraphs[index])
      const links = Array.from(node.querySelectorAll('a[data-summary-source]'))
      expect(links.length).toBeGreaterThan(0)
      for (const link of links) {
        const source = data.sources.find(s => s.id === link.getAttribute('data-summary-source'))!
        expect(source).toBeDefined()
        expect(link).toHaveAttribute('href', source.url)
        expect(link.textContent).not.toContain('来源登记')
      }
    })
    if (topic.id === 'demand-supply') {
      for (let i = 0; i < 12; i += 3) {
        expect(topic.periodSummary.paragraphs[i]).toContain('增长：')
        expect(topic.periodSummary.paragraphs[i + 1]).toContain('就业：')
      }
    }
  }
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2025-12-30' } })
  expect(container.querySelector('[data-summary-paragraph]')).toBeNull()
  expect(container.querySelector('[data-summary-source]')).toBeNull()
})

it('retains all sixteen official paragraphs and references while adding eight dated, supported institutional interpretations', () => {
  const hash = (s: string) => createHash('sha256').update(s).digest('hex')
  for (const fixture of baseline) {
    const topic = data.marketAnalysis.sections.find(s => s.id === fixture.topic)!
    const summary = topic.periodSummary
    expect(summary.historicalAsOfEligible).toBe(false)
    expect(summary.firstAvailableDate).toBeNull()
    const nodes = Object.values(topic.deepDive).flat()
    for (let monthIndex = 0; monthIndex < 4; monthIndex++) {
      for (let within = 0; within < 2; within++) {
        const oldIndex = monthIndex * 2 + within, newIndex = monthIndex * 3 + within
        expect(hash(summary.paragraphs[newIndex])).toBe(fixture.mechanismSHA256[oldIndex])
        expect(summary.paragraphSources![newIndex]).toEqual(fixture.mechanismSources[oldIndex])
      }
      const expected = fixture.institutions[monthIndex], index = monthIndex * 3 + 2
      expect(summary.paragraphs[index]).toContain(`${expected.month}月｜机构解读与分歧：`)
      expect(hash(summary.paragraphs[index])).toBe(expected.textSHA256)
      expect(summary.paragraphs[index]).toMatch(/\d+月\d+日/)
      if (topic.id === 'demand-supply') {
        expect(summary.paragraphs[index]).toMatch(/增长|需求/)
        expect(summary.paragraphs[index]).toMatch(/就业|招聘/)
      }
      for (const id of expected.nodes) expect(summary.evidenceRefs).toContain(id)
      const supportingNodes = expected.nodes.map(id => nodes.find(n => n.id === id)!)
      expect(supportingNodes.every(Boolean)).toBe(true)
      for (const id of expected.sourceIds) {
        expect(summary.reportIds).toContain(id)
        expect(summary.sourceIds).toContain(id)
        expect(summary.paragraphSources![index].some(ref => ref.sourceId === id)).toBe(true)
        const report = data.reports.find(r => r.id === id)!
        expect(report.publicationDate?.slice(0, 7)).toBe(`2025-${String(expected.month).padStart(2, '0')}`)
        expect(report.historicalAsOfEligible).toBe(false)
        expect(report.firstAvailableDate).toBeNull()
        expect(supportingNodes.some(n => n.reportIds.includes(id) && n.sourceIds.includes(id))).toBe(true)
      }
      expect(summary.paragraphSources![index].map(r => r.sourceId)).not.toContain('wind-e0fcfc6ce00c58ae')
    }
  }
})
