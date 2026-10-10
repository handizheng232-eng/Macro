import { fireEvent, render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'

// TEST ONLY display fixtures, no empirical data or forecasts.
function fixture(): HistoryReplayData {
  return { title: '测试复盘', startDate: '1999-01-01', asOf: '1999-01-31', summary: [], sources: [], reports: [], events: [], acquisition: [], hypotheses: [],
    marketAnalysis: { title: '综合市场分析', conclusion: '测试总判断', limitations: [], sections: [{ id: 'test-topic', title: '测试主题', judgement: '测试核心判断', expectation: '', reality: '', mechanism: '', divergence: '', implication: '', validation: '', sourceIds: [], reportIds: [],
      deepDive: { expectationTimeline: [{ id: 'test-entry', date: '1999-01-02', title: '测试节点', text: '测试详细内容', sourceIds: [], reportIds: [], evidenceRefs: [] }] },
    }] },
  }
}

it('每个主题的详细阶段总结位于分项展开之前，原判断和原节点保持', () => {
  const data = fixture()
  const summary = { paragraphs: ['测试阶段背景与主要转折。', '测试机制、分歧和阶段末状态。'], sourceIds: [], reportIds: [], evidenceRefs: ['test-entry'] }
  Object.assign(data.marketAnalysis!.sections[0], { periodSummary: summary })
  const before = JSON.stringify(data)
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  const period = container.querySelector('[data-period-summary]')
  expect(period).toHaveTextContent('测试阶段背景与主要转折。')
  expect(period).toHaveTextContent('测试机制、分歧和阶段末状态。')
  expect(screen.getByRole('heading', { name: '阶段总结' })).toBeVisible()
  expect(period!.compareDocumentPosition(container.querySelector('.replay-deep-dive')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(container).toHaveTextContent('测试核心判断')
  expect(container).toHaveTextContent('测试详细内容')
  expect(JSON.stringify(data)).toBe(before)
})

it('分项精炼总结位于该方面时间线之前，不用节点正文代替导读', () => {
  const data = fixture()
  Object.assign(data.marketAnalysis!.sections[0], { aspectSummaries: { expectationTimeline: { text: '测试全阶段预期变化与共同条件的概括。', sourceIds: [], reportIds: [], evidenceRefs: ['test-entry'] } } })
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  const summary = container.querySelector('[data-aspect-summary="expectationTimeline"]')
  expect(summary).toHaveTextContent('测试全阶段预期变化与共同条件的概括。')
  expect(summary!.compareDocumentPosition(container.querySelector('.replay-analysis-entries')!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(container).toHaveTextContent('测试详细内容')
})

it('未知日期仅为次要提示，保留可核查说明与null而不制造日期', () => {
  const data = fixture()
  data.marketAnalysis!.sections[0].deepDive!.expectationTimeline![0].date = null
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(container).not.toHaveTextContent('日期未注明（不补造）')
  const note = screen.getByText('日期未详')
  expect(note).toHaveClass('replay-date-unknown')
  expect(note).toHaveAttribute('title', '资料未注明具体日期，保留未知，不补造日期精度。')
  expect(note).not.toHaveAttribute('datetime')
  expect(data.marketAnalysis!.sections[0].deepDive!.expectationTimeline![0].date).toBeNull()
})

it('双层总结与当前研究一起在严格历史截面卸载，恢复后正常出现', () => {
  const data = fixture()
  Object.assign(data.marketAnalysis!.sections[0], {
    periodSummary: { paragraphs: ['测试阶段总结'], sourceIds: [], reportIds: [], evidenceRefs: ['test-entry'] },
    aspectSummaries: { expectationTimeline: { text: '测试分项导读', sourceIds: [], reportIds: [], evidenceRefs: ['test-entry'] } },
  })
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '1999-01-02' } })
  expect(container.querySelector('[data-period-summary],[data-aspect-summary]')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByText('测试阶段总结')).toBeVisible()
  expect(screen.getByText('测试分项导读')).toBeVisible()
})
