import { render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'
import { formatReplayDate, formatReplayText } from './replayDateFormat'

// All values below are TEST ONLY fixtures, never public research observations.
const raw = '会议于9/16公布，会议日期9/15—16；观测期2026-09，预测2026Q2；2025-12-31—2026-01-02。2/10年期利差、1/2比值、https://example.org/9/16、E:/9/16/report.pdf、audit_2026-09-16不变。'
const fixture: HistoryReplayData = {
  title: 'TEST ONLY 日期阅读层', startDate: '2025-12-31', endDate: '2026-10-01', asOf: '2026-10-01', summary: [],
  sources: [], events: [], hypotheses: [], reports: [], acquisition: [],
  marketAnalysis: { title: '综合市场分析', conclusion: raw, limitations: [], sections: [] },
  windResearchEvidence: [{ reportId: 'test-only', expressedAt: '2026-09-16', dateBasis: 'TEST ONLY', actor: '测试作者',
    claim: 'TEST ONLY', scope: '日期', observationPeriod: '2026Q2', pages: [1], evidenceExcerpt: '原句：会议于9/16公布。', localPath: 'E:/9/16/report.pdf' }],
}

it('只在日期字段与明确阅读语境规范中文日期，原文、ISO状态和保护对象不变', () => {
  const before = JSON.stringify(fixture)
  const { container } = render(<HistoryReplay data={fixture} onBack={() => {}} />)
  expect(container.querySelector('.replay-heading')).toHaveTextContent('2025年12月31日至2026年10月1日')
  expect(screen.getByLabelText('按日期截止查看')).toHaveValue('2026-10-01')
  const analysis = screen.getByRole('region', { name: '综合市场分析' })
  expect(analysis).toHaveTextContent('会议于9月16日公布，会议日期9月15日至9月16日')
  expect(analysis).toHaveTextContent('观测期2026年9月，预测2026年第二季度')
  expect(analysis).toHaveTextContent('2025年12月31日至2026年1月2日')
  for (const value of ['2/10年期利差', '1/2比值', 'https://example.org/9/16', 'E:/9/16/report.pdf', 'audit_2026-09-16']) expect(analysis).toHaveTextContent(value)
  expect(screen.getByText('原句：会议于9/16公布。')).toBeInTheDocument()
  expect(screen.getByLabelText('Wind观点独立追溯')).toHaveTextContent('观测期：2026年第二季度')
  expect(JSON.stringify(fixture)).toBe(before)
})

it.each([
  ['9/16', '9月16日'], ['9/15—16', '9月15日至9月16日'],
  ['9/30—10/2', '9月30日至10月2日'],
  ['2025/12/31—2026/1/2', '2025年12月31日至2026年1月2日'],
  ['2026-09-16', '2026年9月16日'], ['2026-09', '2026年9月'],
  ['2026Q2', '2026年第二季度'], ['2026-Q4', '2026年第四季度'],
  ['2025-Q4—2026Q1', '2025年第四季度至2026年第一季度'],
  ['2026-02-29', '2026-02-29'], ['2026-13', '2026-13'], ['13/16', '13/16'],
])('明确日期字段保留精度并验证日期 %s', (raw, label) => {
  expect(formatReplayDate(raw)).toBe(label)
})

it('阅读层日期允许ISO双端范围与版本时间戳，但不改中文路径/文件名', () => {
  expect(formatReplayDate('2026-09-15/2026-09-16')).toBe('2026年9月15日至2026年9月16日')
  expect(formatReplayDate('2026-09-29T04:00:17+00:00')).toBe('2026年9月29日 04:00:17+00:00')
  for (const raw of ['9/16会议.pdf', '会议/2026-09-16/原文.pdf', '会议日期2/10年期利差', '在1/2分数下']) expect(formatReplayText(raw)).toBe(raw)
})

it('日期后接事件名构成明确语境，跨年写全；无语境斜杠、文件与ID不是日期', () => {
  expect(formatReplayText('9/16会议，9/15—16公布；日期2025/12/31—2026/1/2。')).toBe('9月16日会议，9月15日至9月16日公布；日期2025年12月31日至2026年1月2日。')
  for (const raw of ['9/16', '2/10年期利差', '在1/2比值下', '2026-09-16.pdf', '目录/9/16/原文.pdf', 'id_2026-09-16', '9/16/2026', 'https://example.org/2026-09-16']) expect(formatReplayText(raw)).toBe(raw)
})

it('覆盖用户指定公开日期语境，不把一般介词后的样本分数改成日期', () => {
  expect(formatReplayText('公开9/15—16的材料，9/16披露的声明。')).toBe('公开9月15日至9月16日的材料，9月16日披露的声明。')
  expect(formatReplayText('在1/2的样本中成立，于1/2样本中检验；公开2/10年期利差。')).toBe('在1/2的样本中成立，于1/2样本中检验；公开2/10年期利差。')
})
