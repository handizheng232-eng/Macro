
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'
import first from './data/historyReplay.json'
import reviewedArtifact from './data/historyReplayHawkishTransition.json'

// Exercise the exact public artifact shipped to Pages; private archives are
// neither needed by these rendering tests nor copied into the repository.
const second = reviewedArtifact as HistoryReplayData
const outline = (root: HTMLElement) => Array.from(root.children).map(node => [node.tagName, node.getAttribute('aria-label') || '', node.className])

afterEach(cleanup)

it('真实八月研究与四条修订链仅挂在既有来源库内，第一篇同壳空状态', () => {
  const a = render(<HistoryReplay data={first} onBack={() => {}} />)
  const firstOutline = outline(a.container.querySelector('.history-replay')!)
  const firstLibrary = screen.getByLabelText('来源库 / 研报库明细')
  const empty = screen.getByLabelText('逐月预期现实与修订链')
  expect(firstLibrary).toContainElement(empty)
  expect(empty).not.toHaveAttribute('open')
  expect(empty.querySelectorAll('[data-replay-month]')).toHaveLength(0)
  cleanup()
  const b = render(<HistoryReplay data={second} onBack={() => {}} />)
  expect(outline(b.container.querySelector('.history-replay')!)).toEqual(firstOutline)
  const library = screen.getByLabelText('来源库 / 研报库明细')
  const monthly = screen.getByLabelText('逐月预期现实与修订链')
  expect(library).toContainElement(monthly)
  expect(library).not.toHaveAttribute('open')
  expect(monthly).not.toHaveAttribute('open')
  fireEvent.click(library.querySelector(':scope > summary')!)
  fireEvent.click(monthly.querySelector(':scope > summary')!)
  const months = monthly.querySelectorAll('[data-replay-month]')
  expect(Array.from(months).map(node => node.getAttribute('data-replay-month'))).toEqual(['2026-01','2026-02','2026-03','2026-04','2026-05','2026-06','2026-07','2026-08'])
  expect(monthly.querySelectorAll('[data-revision-chain]')).toHaveLength(4)
  expect(monthly).not.toHaveTextContent('verified-opinion-')
  expect(monthly).not.toHaveTextContent('[rate-decision-')
  expect(monthly).toHaveTextContent('原文与官方依据')
  expect(screen.getByLabelText('综合市场分析')).not.toHaveTextContent('verified-opinion-')
  expect(monthly).toHaveTextContent('同机构修订链，不是多个独立机构或市场共识')
  expect(b.container.querySelectorAll('.replay-market-analysis > .replay-analysis-topic')).toHaveLength(5)
})

it('严格历史切窗卸载真实八月链及所有新观点，而非仅隐藏正文', () => {
  const view = render(<HistoryReplay data={second} onBack={() => {}} />)
  expect(view.container.querySelectorAll('[data-replay-month]')).toHaveLength(8)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-07-31' } })
  expect(screen.queryByLabelText('逐月预期现实与修订链')).not.toBeInTheDocument()
  expect(view.container.querySelectorAll('[data-replay-month]')).toHaveLength(0)
  expect(view.container.querySelectorAll('[data-revision-chain]')).toHaveLength(0)
  expect(screen.queryByLabelText('星球观点明细')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Wind观点明细')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('微信观点明细')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('综合市场分析')).not.toBeInTheDocument()
})

it('真实39观点保留条件、期限及现实来源，不把未来九月判为已失败', () => {
  const view = render(<HistoryReplay data={second} onBack={() => {}} />)
  const sections = ['星球观点独立追溯','Wind观点独立追溯','微信观点独立追溯'].map(name => screen.getByLabelText(name))
  expect(sections.reduce((sum,node) => sum + node.querySelectorAll('.replay-audit-card').length,0)).toBe(39)
  for (const section of sections) {
    expect(section).toHaveTextContent('条件：')
    expect(section).toHaveTextContent('期限：')
  }
  const monthOnly = second.windResearchEvidence!.find(item => item.claim.includes('9月或降一次25bp'))!
  const horizon = view.container.querySelector(`[data-opinion-id="${(monthOnly as { id: string }).id}"]`)
  expect(monthOnly.status).toBe('ongoing')
  expect(horizon).toHaveTextContent('ongoing')
})
