import { formatReplayDate, formatReplayText } from './replayDateFormat'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import type { HistoryReplayData } from './historyReplay'
import policyReversalData from './data/historyReplay.json'
import hawkishTransitionData from './data/historyReplayHawkishTransition.json'

const parentHash = '#history/easing-to-tightening'
const hawkishHash = `${parentHash}/hawkish-transition`
const stages: { hash: string; label: string; data: HistoryReplayData; cutoff: string }[] = [
  { hash: `${parentHash}/policy-reversal`, label: '政策反转研究工作台', data: policyReversalData, cutoff: '2026-09-01' },
  { hash: hawkishHash, label: '鹰派换届研究工作台', data: hawkishTransitionData, cutoff: '2026-01-01' },
]

function syncHash(hash: string, event: 'hashchange' | 'popstate') {
  window.history.replaceState(null, '', hash)
  act(() => window.dispatchEvent(event === 'hashchange' ? new HashChangeEvent(event) : new PopStateEvent(event)))
}

beforeEach(() => window.history.replaceState(null, '', parentHash))

const switchCases = (['hashchange', 'popstate'] as const).flatMap((event) => stages.map((from, index) => ({ event, from, to: stages[(index + 1) % stages.length] })))
it.each(switchCases)('$event：从$from.label切页时截止、检索和展开状态重置，数据不串页', async ({ event, from, to }) => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', from.hash)
  render(<App />)
    const library = screen.getByLabelText('来源库 / 研报库明细')
    await user.click(library.querySelector('summary')!)
    fireEvent.change(screen.getByLabelText('检索资料'), { target: { value: '仅测试检索状态' } })
    fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: from.cutoff } })
    syncHash(to.hash, event)
    const workbench = screen.getByRole('article', { name: to.label })
    expect(workbench.querySelector('h1')).toHaveTextContent(to.data.title)
    expect(screen.queryByRole('article', { name: from.label })).not.toBeInTheDocument()
    expect(screen.getByLabelText('按日期截止查看')).toHaveValue(to.data.asOf)
    expect(screen.getByLabelText('检索资料')).toHaveValue('')
    for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细', '来源库 / 研报库明细']) {
      expect(screen.getByLabelText(label)).not.toHaveAttribute('open')
    }
    if (to.data.localResearchEvidence?.length) expect(screen.getByLabelText('本地研报观点明细')).not.toHaveAttribute('open')
    expect(screen.getByRole('status')).toHaveTextContent(`${formatReplayDate(to.data.asOf)} · ${to.data.events.filter((entry) => entry.date <= to.data.asOf).length} 条事件`)
    expect(within(screen.getByRole('region', { name: '市场路径对照' })).queryAllByRole('rowheader').map((heading) => heading.textContent)).toEqual(
      to.data.events.filter((entry) => entry.date <= to.data.asOf).sort((a, b) => a.date.localeCompare(b.date)).map((entry) => `${formatReplayDate(entry.date)}${entry.title}`),
    )
    const libraryHeading = screen.getByLabelText('来源库 / 研报库明细').querySelector('summary')!
    expect(libraryHeading).toHaveTextContent(`授权研报 ${to.data.reports.filter((report) => {
      const date = report.filenameDate !== undefined && (!report.dateBasis || report.dateBasis.includes('filename_date_')) ? report.filenameDate : report.publicationDate !== undefined ? report.publicationDate : report.date
      return !date || date <= to.data.asOf
    }).length}`)
})

it('真实back/forward在总览、父阶段、新子页间往返，主导航离开卸载工作台', async () => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', '#history')
  render(<App />)
  await user.click(screen.getByRole('button', { name: '进入当前阶段细分复盘' }))
  await user.click(screen.getByRole('button', { name: '进入鹰派换届与反转酝酿研究工作台' }))
  const traverse = async (direction: 'back' | 'forward') => {
    await act(async () => {
      const navigated = new Promise<void>((resolve) => window.addEventListener('popstate', () => resolve(), { once: true }))
      window.history[direction]()
      await navigated
    })
  }
  await traverse('back')
  expect(window.location.hash).toBe(parentHash)
  expect(screen.getByRole('heading', { name: '细分时段复盘' })).toBeInTheDocument()
  await traverse('back')
  expect(window.location.hash).toBe('#history')
  expect(screen.getByRole('heading', { name: '一级时期总览' })).toBeInTheDocument()
  await traverse('forward')
  expect(screen.getByRole('heading', { name: '细分时段复盘' })).toBeInTheDocument()
  await traverse('forward')
  expect(window.location.hash).toBe(hawkishHash)
  expect(screen.getByRole('article', { name: '鹰派换届研究工作台' })).toBeInTheDocument()
  for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细']) expect(screen.getByLabelText(label)).not.toHaveAttribute('open')
  await user.click(screen.getByRole('button', { name: '今日总览' }))
  expect(screen.queryByRole('article', { name: '鹰派换届研究工作台' })).not.toBeInTheDocument()
  expect(screen.queryByLabelText('按日期截止查看')).not.toBeInTheDocument()
  await traverse('back')
  expect(screen.getByRole('article', { name: '鹰派换届研究工作台' })).toBeInTheDocument()
  expect(screen.getByLabelText('按日期截止查看')).toHaveValue(hawkishTransitionData.asOf)
})

it('新阶段三渠道默认独立关闭，进入历史截面卸载、恢复不继承展开状态', async () => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', hawkishHash)
  render(<App />)
  const channels = ['星球', 'Wind', '微信']
  if (hawkishTransitionData.localResearchEvidence.length) channels.push('本地研报')
  for (const channel of channels) {
    if (channel === '本地研报') {
      const library = screen.getByLabelText('来源库 / 研报库明细')
      expect(library).not.toHaveAttribute('open')
      await user.click(library.querySelector(':scope > summary')!)
    }
    const details = screen.getByLabelText(`${channel}观点明细`)
    expect(details).not.toHaveAttribute('open')
    await user.click(details.querySelector(':scope > summary')!)
    expect(details).toHaveAttribute('open')
    expect(screen.getByRole('region', { name: `${channel}观点独立追溯` })).toBeVisible()
  }
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-01-01' } })
  for (const channel of channels) {
    expect(screen.queryByLabelText(`${channel}观点明细`)).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: `${channel}观点独立追溯` })).not.toBeInTheDocument()
  }
  expect(screen.queryByRole('region', { name: '综合市场分析' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  for (const channel of channels) expect(screen.getByLabelText(`${channel}观点明细`)).not.toHaveAttribute('open')
})

it('从父阶段进入鹰派换届独立子页，完整日期与返回父阶段均正确', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: '进入鹰派换届与反转酝酿研究工作台' }))
  expect(window.location.hash).toBe(hawkishHash)
  const workbench = screen.getByRole('article', { name: '鹰派换届研究工作台' })
  expect(workbench.querySelector('h1')).toHaveTextContent('鹰派换届与反转酝酿')
  expect(workbench.querySelector('.replay-heading')).toHaveTextContent(formatReplayText('2026-01-01—2026-08-31'))
  expect(workbench.querySelector('.replay-heading')).not.toHaveTextContent('终点未形成')
  expect(screen.getByLabelText('按日期截止查看')).toHaveValue('2026-08-31')
  await user.click(screen.getByRole('button', { name: '返回父阶段复盘' }))
  expect(window.location.hash).toBe(parentHash)
  expect(screen.getByRole('heading', { name: '细分时段复盘' })).toBeInTheDocument()
  expect(screen.queryByRole('article', { name: '鹰派换届研究工作台' })).not.toBeInTheDocument()
})

it('直接加载鹰派换届hash，不回退到时期总览或九月工作台', () => {
  window.history.replaceState(null, '', hawkishHash)
  render(<App />)
  expect(screen.getByRole('article', { name: '鹰派换届研究工作台' })).toBeInTheDocument()
  expect(screen.queryByRole('article', { name: '政策反转研究工作台' })).not.toBeInTheDocument()
  expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument()
  act(() => window.dispatchEvent(new HashChangeEvent('hashchange')))
  expect(screen.getByRole('article', { name: '鹰派换届研究工作台' })).toBeInTheDocument()
})
