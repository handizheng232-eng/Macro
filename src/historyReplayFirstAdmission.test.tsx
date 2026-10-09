import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'
import first from './data/historyReplay.json'
import second from './data/historyReplayHawkishTransition.json'

// Presentation-only fixture: it never writes production data or invents sources
// for the research build. Real first/second artifacts supply the shared shell.
const section = (id: string) => ({
  id, title: `测试主题 ${id}`, judgement: '测试判断', expectation: '测试预期 [fixture-opinion]',
  reality: '测试现实 [fixture-analysis-only-source]', mechanism: '测试机制 [2Y−10Y]',
  divergence: '测试分歧', implication: '测试含义', validation: '测试验证条件',
  sourceIds: ['fixture-analysis-only-source'], reportIds: [],
})
const data: HistoryReplayData = {
  ...first, asOf: '2026-10-09', reports: [], researchEvidence: [], windResearchEvidence: [], wechatResearchEvidence: [],
  sources: [{ id: 'fixture-analysis-only-source', title: '测试后发确认来源', publisher: '测试', date: '2026-10-08',
    url: 'https://example.com/fixture', kind: '测试', note: '', status: '测试', historicalAsOfEligible: false }],
  events: [],
  marketAnalysis: { title: '综合市场分析', conclusion: '测试结论', limitations: [],
    sections: ['policy-path', 'inflation-vintages', 'demand-supply', 'treasury-curve', 'dollar-relative'].map(section) },
  monthlyReplay: ['2026-09', '2026-10'].map(month => ({ ...section(`fixture-${month}`), month,
    sourceIds: [], opinionIds: ['fixture-opinion'], factIds: [], dynamicConvergence: '测试逐月收敛' })),
  revisionChains: [{ id: 'fixture-chain', label: '测试修正链', description: '测试条件链', opinionIds: [], limitation: '测试夹具，非研究结论' }],
}
const outline = (root: HTMLElement) => Array.from(root.children).map(node => [node.tagName, node.getAttribute('aria-label') || '', node.className])
afterEach(cleanup)

it('第一篇两个月追溯夹具复用第二章主结构、五主题及既有库内修正链', () => {
  const template = render(<HistoryReplay data={second} onBack={() => {}} />)
  const expected = outline(template.container.querySelector('.history-replay')!)
  cleanup()
  const view = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(outline(view.container.querySelector('.history-replay')!)).toEqual(expected)
  const library = screen.getByLabelText('来源库 / 研报库明细')
  const monthly = screen.getByLabelText('逐月预期现实与修订链')
  expect(library).toContainElement(monthly)
  expect(library).not.toHaveAttribute('open')
  expect(monthly).not.toHaveAttribute('open')
  for (const channel of ['星球', 'Wind', '微信']) expect(screen.getByLabelText(`${channel}观点明细`)).not.toHaveAttribute('open')
  expect(Array.from(monthly.querySelectorAll('[data-replay-month]')).map(n => n.getAttribute('data-replay-month'))).toEqual(['2026-09','2026-10'])
  expect(monthly.querySelectorAll('[data-revision-chain]')).toHaveLength(1)
  expect(view.container.querySelectorAll('.replay-analysis-topic')).toHaveLength(5)
  const analysis = screen.getByLabelText('综合市场分析')
  expect(analysis).not.toHaveTextContent('[fixture-analysis-only-source]')
  expect(analysis).not.toHaveTextContent('[fixture-opinion]')
  expect(analysis).toHaveTextContent('[2Y−10Y]')
})

it('新两月当前分析、三渠道、月份、链与后发确认来源在严格历史模式全部卸载', () => {
  const view = render(<HistoryReplay data={data} onBack={() => {}} />)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-30' } })
  for (const label of ['综合市场分析','逐月预期现实与修订链','星球观点明细','Wind观点明细','微信观点明细']) {
    expect(screen.queryByLabelText(label)).not.toBeInTheDocument()
  }
  expect(view.container.querySelectorAll('[data-replay-month], [data-revision-chain]')).toHaveLength(0)
  expect(screen.queryByText('测试后发确认来源')).not.toBeInTheDocument()
})
