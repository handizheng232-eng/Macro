import { fireEvent, render, screen, within } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'

// Test-only receipt states, not production macro data or acquisition results.
const cell = (bodyCount: number) => ({ bodyCount, archiveEntries: bodyCount,
  searchExecuted: false, status: bodyCount ? '已有正文·逐月检索待核' : '未取得正文', reason: '', archives: [] })
const fixture: HistoryReplayData = {
  title: '覆盖矩阵测试', startDate: '2026-01-01', asOf: '2026-08-31', summary: [],
  sources: [], events: [], hypotheses: [], acquisition: [], reports: [],
  monthlyCoverage: { requiredCells: 24, coveredCells: 1, acceptedCells: 0, complete: false,
    basis: 'TEST ONLY', rows: Array.from({ length: 8 }, (_, index) => ({
      month: `2026-${String(index + 1).padStart(2, '0')}`,
      channels: { '知识星球': cell(index === 7 ? 1 : 0), Wind: cell(0), '微信公众号': cell(0) },
    })) },
}

it('逐月矩阵显示全部月份及三渠道；末月有正文不等于整段覆盖完成', () => {
  render(<HistoryReplay data={fixture} onBack={() => {}} />)
  const region = screen.getByRole('region', { name: '月份与渠道覆盖' })
  expect(within(region).getByRole('table')).toBeInTheDocument()
  expect(within(region).getAllByRole('row')).toHaveLength(9)
  for (const channel of ['知识星球', 'Wind', '微信公众号']) {
    expect(within(region).getByRole('columnheader', { name: channel })).toBeInTheDocument()
  }
  expect(region).toHaveTextContent('未满足逐月覆盖验收')
  expect(region).toHaveTextContent('已有正文 1 / 24 格')
  expect(region).toHaveTextContent('月度原文配额已验收 0 / 24 格')
  expect(region).not.toHaveTextContent('逐月检索已核验')
  expect(region).toHaveTextContent('左右滑动表格，查看各渠道')
})

it('SHA去重档案数不冒充独立作品，异SHA同文另列关联数', () => {
  render(<HistoryReplay data={{ ...fixture, archiveCoverage: {
    channelEntries: 2, uniqueDocuments: 2, sharedDocuments: 0, textVerifiedAliasCount: 1,
  } }} onBack={() => {}} />)
  expect(screen.getByText(/2份不同归档文件（SHA去重）/)).toBeInTheDocument()
  expect(screen.getByText(/1条异SHA同文关联/)).toBeInTheDocument()
  expect(screen.getByRole('region', { name: '月份与渠道覆盖' })).not.toHaveTextContent('份独立原文')
})

it('历史截面不泄露当前批次覆盖；恢复后缺口仍如实显示', () => {
  render(<HistoryReplay data={fixture} onBack={() => {}} />)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-03-31' } })
  expect(screen.queryByRole('region', { name: '月份与渠道覆盖' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByRole('region', { name: '月份与渠道覆盖' })).toHaveTextContent('未满足逐月覆盖验收')
})
