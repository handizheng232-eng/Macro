import { render } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData, type ReplayAnalysisEntry } from './historyReplay'
// Publication-1 is an immutable public fixture, not the current release contract.
import third from '../release/snapshots/renewed-easing-publication-1.json'
import template from './data/historyReplayHawkishTransition.json'

// Strict real artifact compatibility, no cast/any or relaxed shared interface.
const data: HistoryReplayData = third

it('实际第三载荷具有232唯一节点/81观点/5主题/5阶段总结/35方面/26图卡/48允许实例', () => {
  const sections: NonNullable<HistoryReplayData['marketAnalysis']>['sections'] = third.marketAnalysis.sections
  const nodes: ReplayAnalysisEntry[] = sections.flatMap(section => Object.values(section.deepDive!).flat())
  const views = [ ...third.researchEvidence, ...third.windResearchEvidence, ...third.wechatResearchEvidence ]
  expect(nodes).toHaveLength(232)
  expect(new Set(nodes.map(node => node.id)).size).toBe(232)
  expect(views).toHaveLength(81)
  expect(new Set(views.map(view => view.id)).size).toBe(81)
  expect(sections.map(section => section.id)).toEqual(['policy-path', 'inflation-vintages', 'demand-supply', 'treasury-curve', 'dollar-relative'])
  expect(sections.flatMap(section => section.periodSummary!.paragraphs)).toHaveLength(20)
  expect(sections.flatMap(section => Object.values(section.aspectSummaries!))).toHaveLength(35)
  expect(sections.flatMap(section => section.frameworkEvidence!)).toHaveLength(26)
  expect(sections.flatMap(section => section.frameworkEvidence!.flatMap(card => card.series))).toHaveLength(48)
  expect(data.title).toBe('再降息与QT收官')
  const sources = new Set(third.sources.map(source => source.id))
  const reports = new Set(third.reports.map(report => report.id))
  for (const node of nodes) {
    expect(node.sourceIds.every(id => sources.has(id))).toBe(true)
    expect(node.reportIds.every(id => reports.has(id))).toBe(true)
    const metadata = new Map(Object.entries(node))
    expect(metadata.get('historicalAsOfEligible')).toBe(false)
    expect(metadata.get('firstAvailableDate') ?? null).toBeNull()
  }
  for (const view of views) expect(view.evidenceExcerpt).toBeNull()
})

it('实际12格配额无缺口，星球非穷尽且网站总量未知，历史资格未升级', () => {
  expect(third.monthlyCoverage.acceptedCells).toBe(12)
  expect(third.monthlyCoverage.complete).toBe(true)
  expect(third.monthlyCoverage.rows.map(row => [row.channels.知识星球.bodyCount, row.channels.Wind.bodyCount, row.channels.微信公众号.bodyCount])).toEqual([[20,12,5], [20,10,5], [20,10,5], [21,10,5]])
  for (const row of third.monthlyCoverage.rows) {
    expect(row.channels.知识星球.searchExhaustive).toBe(false)
    expect(row.channels.知识星球.actualEligibleTotal).toBeNull()
  }
  expect(third.marketPaths.series).toHaveLength(13)
  expect(third.marketPaths.series.flatMap(series => series.observations).filter(point => point.value !== null)).toHaveLength(962)
  const framework = data.marketAnalysis!.sections.flatMap(section => section.frameworkEvidence!.flatMap(card => card.series))
  expect(framework.some(series => series.id === 'third-policy-path-liquidity-reserves')).toBe(false)
  const broad = framework.find(series => series.id === 'third-dollar-relative-usd-identity-broad_dollar')!
  expect(broad.unit).toBe('2006年1月=100')
  expect(broad.observations).toHaveLength(83)
  expect(third.candidateMetadata).toMatchObject({ published: false, publicationAuthorized: false, fullStageReady: false, pageQAComplete: false })
  expect(third.marketAnalysis.limitations.join('\n')).not.toMatch(/尚未获父独立接受的星球增量|不读尚待父方独立准入|旧星球1份|完整星球月度配额.*未完成/)
  expect(third.marketAnalysis.limitations.join('\n')).toMatch(/广义美元不是DXY/)
})

function outline(candidate: HistoryReplayData) {
  const { container, unmount } = render(<HistoryReplay data={candidate} onBack={() => {}} />)
  const article = container.querySelector('.history-replay')!
  const result = Array.from(article.children).map(element => [element.tagName, element.getAttribute('aria-label'), element.className])
  unmount()
  return result
}
it('真实第三与第二章共享v3主结构一致，不增加独立事件时间轴', () => {
  expect(outline(data)).toEqual(outline(template))
})
