import { fireEvent, render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'

it('首次可得日期晚于截面时卸载来源、依赖事件标题与原件书目', () => {
  const data = {
    title: '新窗口测试', startDate: '2026-09-01', asOf: '2026-10-09', summary: [],
    hypotheses: [], acquisition: [],
    sources: [{ id: 'late-proof', title: '后发确认来源测试', publisher: '测试', date: '2026-09-16',
      firstAvailableDate: '2026-10-08', historicalAsOfEligible: true,
      url: 'https://example.com/late', kind: '测试', status: '测试', note: '' }],
    reports: [{ id: 'unknown-first', title: '首次可得未知书目测试', provider: '测试', path: '', date: '2026-09-15',
      firstAvailableDate: null, historicalAsOfEligible: true }],
    events: [{ id: 'early-event', date: '2026-09-16', title: '依赖十月来源的九月事件测试',
      observationPeriod: '测试', expectation: '', expectationSourceIds: [], reality: '测试',
      realitySourceIds: ['late-proof'], interpretation: '', marketResponse: '', confidence: '测试' }],
  } as HistoryReplayData
  render(<HistoryReplay data={data} onBack={() => {}} />)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-30' } })
  expect(screen.queryByText('后发确认来源测试')).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: '依赖十月来源的九月事件测试' })).not.toBeInTheDocument()
  expect(screen.queryByText('首次可得未知书目测试')).not.toBeInTheDocument()
})

it('历史截面不显示只有更晚追溯来源才能确认的事件标题', () => {
  const data = {
    title: '追溯来源测试', startDate: '2026-01-01', asOf: '2026-08-31', summary: [],
    sources: [], hypotheses: [], acquisition: [], reports: [],
    events: [{ id: 'retrospective', date: '2026-03-04', title: '只有五月来源的提名测试',
      availableFrom: '2026-05-22', observationPeriod: '测试', expectation: '', expectationSourceIds: [],
      reality: '', realitySourceIds: [], interpretation: '', marketResponse: '', confidence: '测试' }],
  } as HistoryReplayData
  render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(screen.getByRole('heading', { name: '只有五月来源的提名测试' })).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-04-01' } })
  expect(screen.queryByRole('heading', { name: '只有五月来源的提名测试' })).not.toBeInTheDocument()
})

it('晚取得的追溯行情来源保留真实日期，仅当前完整视图可见', () => {
  const data = {
    title: '追溯行情来源测试', startDate: '2026-01-01', asOf: '2026-08-31', summary: [],
    sources: [{ id: 'retro', title: '当前取得行情测试', publisher: '测试', date: '2026-10-02',
      url: 'https://example.com/series', kind: '测试', status: '测试', note: '',
      retrospectiveOnly: true, historicalAsOfEligible: false }],
    events: [], hypotheses: [], acquisition: [], reports: [],
  } as HistoryReplayData
  render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(screen.getByText('当前取得行情测试')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-08-01' } })
  expect(screen.queryByText('当前取得行情测试')).not.toBeInTheDocument()
})

it('逐条预期现实对照展示期限、状态和页码，历史模式卸载', () => {
  const data = {
    title: '逐条对照测试', startDate: '2026-01-01', asOf: '2026-08-31', summary: [],
    sources: [], events: [], hypotheses: [], acquisition: [], reports: [],
    realityComparisons: [{ id: 'pair', reportId: 'report', actor: '测试作者', expressedAt: '2026-01-08',
      expectation: '测试二季度条件预测', observationPeriod: '2026Q2', pages: [2],
      reality: '测试限定期现实', realitySourceIds: [], status: '全年部分待验', limitation: '首次可得未核' }],
    archiveCoverage: { channelEntries: 2, uniqueDocuments: 1, sharedDocuments: 1 },
  } as HistoryReplayData
  render(<HistoryReplay data={data} onBack={() => {}} />)
  const disclosure = screen.getByLabelText('逐条预期现实对照')
  expect(disclosure).not.toHaveAttribute('open')
  fireEvent.click(screen.getByLabelText('来源库 / 研报库明细').querySelector(':scope > summary')!)
  fireEvent.click(disclosure.querySelector('summary')!)
  expect(screen.getByText('测试二季度条件预测')).toBeInTheDocument()
  expect(screen.getByText('全年部分待验')).toBeInTheDocument()
  expect(screen.getByText(/2条渠道记录.*1份不同归档文件（SHA去重）.*文件数不代表独立作品数/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-07-01' } })
  expect(screen.queryByLabelText('逐条预期现实对照')).not.toBeInTheDocument()
})
