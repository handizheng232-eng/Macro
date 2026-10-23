import { formatReplayDate, formatReplayText } from './replayDateFormat'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { replayCutoff, replayDisclosure, replaySearch, replayWorkbench, queryReplayWorkbench, replayHeading, replayToolbar } from './historyReplay.testHelpers'
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

// Content isolation, cutoff reset and search/disclosure reset are independent
// contracts. Exercise each event and direction in a fresh App, rather than charge
// several full research renders plus all archive assertions to one 5s test.
const switchCases = (['hashchange', 'popstate'] as const).flatMap((event) => stages.flatMap((from, index) =>
  (['内容隔离', '截止日重置', '检索与展开重置'] as const).map(state => ({ event, from, fromLabel: from.label, to: stages[(index + 1) % stages.length], state })),
))
it.each(switchCases)('$event：从 $fromLabel 切页，$state', async ({ event, from, to, state }) => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', from.hash)
  render(<App />)
  if (state === '检索与展开重置') {
    // The same controlled search remains available in historical mode. Set the
    // cutoff first so typing does not redraw the unrelated current research DOM;
    // all three dirty states still have to reset on the real route event.
    fireEvent.change(replayCutoff(), { target: { value: from.cutoff } })
    expect(replayCutoff()).toHaveValue(from.cutoff)
    const library = replayDisclosure('来源库 / 研报库明细')
    await user.click(library.querySelector(':scope > summary')!)
    expect(library).toHaveAttribute('open')
    fireEvent.change(replaySearch(), { target: { value: '仅测试检索状态' } })
    expect(replaySearch()).toHaveValue('仅测试检索状态')
  }
  if (state === '截止日重置') {
    fireEvent.change(replayCutoff(), { target: { value: from.cutoff } })
    expect(replayCutoff()).toHaveValue(from.cutoff)
  }
  syncHash(to.hash, event)
  const workbench = replayWorkbench(to.label)
  expect(workbench.querySelector('h1')).toHaveTextContent(to.data.title)
  expect(queryReplayWorkbench(from.label)).not.toBeInTheDocument()
  expect(replayCutoff()).toHaveValue(to.data.asOf)
  expect(replaySearch()).toHaveValue('')
  for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细', '来源库 / 研报库明细']) {
    expect(replayDisclosure(label)).not.toHaveAttribute('open')
  }
  if (to.data.localResearchEvidence?.length) expect(replayDisclosure('本地研报观点明细')).not.toHaveAttribute('open')
  if (state === '内容隔离') {
    expect(replayToolbar().getByRole('status')).toHaveTextContent(`${formatReplayDate(to.data.asOf)} · ${to.data.events.filter((entry) => entry.date <= to.data.asOf).length} 条事件`)
    expect(within(screen.getByRole('region', { name: '市场路径对照' })).queryAllByRole('rowheader').map((heading) => heading.textContent)).toEqual(
      to.data.events.filter((entry) => entry.date <= to.data.asOf).sort((a, b) => a.date.localeCompare(b.date)).map((entry) => `${formatReplayDate(entry.date)}${entry.title}`),
    )
    const libraryHeading = replayDisclosure('来源库 / 研报库明细').querySelector(':scope > summary')!
    expect(libraryHeading).toHaveTextContent(`授权研报 ${to.data.reports.filter((report) => {
      const date = report.filenameDate !== undefined && (!report.dateBasis || report.dateBasis.includes('filename_date_')) ? report.filenameDate : report.publicationDate !== undefined ? report.publicationDate : report.date
      return !date || date <= to.data.asOf
    }).length}`)
  }
})

async function traverse(direction: 'back' | 'forward') {
  await act(async () => {
    const navigated = new Promise<void>((resolve) => window.addEventListener('popstate', () => resolve(), { once: true }))
    window.history[direction]()
    await navigated
  })
}

it('真实back/forward在总览、父阶段、新子页间往返', async () => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', '#history')
  render(<App />)
  await user.click(screen.getByRole('button', { name: '进入当前阶段细分复盘' }))
  await user.click(screen.getByRole('button', { name: '进入鹰派换届与反转酝酿研究工作台' }))

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
  expect(replayWorkbench('鹰派换届研究工作台')).toBeInTheDocument()
  for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细']) expect(replayDisclosure(label)).not.toHaveAttribute('open')
})

it('主导航离开卸载工作台，真实back恢复鹰派子页与资料截止日', async () => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', hawkishHash)
  render(<App />)
  await user.click(within(screen.getByRole('navigation', { name: '主导航' })).getByRole('button', { name: '今日总览' }))
  expect(queryReplayWorkbench('鹰派换届研究工作台')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('按日期截止查看')).not.toBeInTheDocument()
  await traverse('back')
  expect(replayWorkbench('鹰派换届研究工作台')).toBeInTheDocument()
  expect(replayCutoff()).toHaveValue(hawkishTransitionData.asOf)
})

const channels = ['星球', 'Wind', '微信', ...(hawkishTransitionData.localResearchEvidence.length ? ['本地研报'] : [])]
const channelCases = channels.flatMap(channel => (['默认关闭与独立展开', '历史卸载与恢复关闭'] as const).map(state => ({ channel, state })))
it.each(channelCases)('$channel 渠道：$state', async ({ channel, state }) => {
  const user = userEvent.setup()
  window.history.replaceState(null, '', hawkishHash)
  render(<App />)
  if (state === '默认关闭与独立展开') {
    for (const name of channels) expect(replayDisclosure(`${name}观点明细`)).not.toHaveAttribute('open')
  }
  // Resolve both labelled disclosures before toggling either: opening the outer
  // library invalidates jsdom's style cache across the entire research archive.
  const details = replayDisclosure(`${channel}观点明细`)
  const library = channel === '本地研报' ? replayDisclosure('来源库 / 研报库明细') : null
  if (library) {
    expect(library).not.toHaveAttribute('open')
    if (state === '默认关闭与独立展开') await user.click(library.querySelector(':scope > summary')!)
    else fireEvent.click(library.querySelector(':scope > summary')!)
    expect(library).toHaveAttribute('open')
  }
  // Pointer/focus behavior is exercised by the independent expansion case.
  // This case still uses the native summary click default action (never sets
  // `open` directly) while testing unmount/remount and discarded local state.
  if (state === '默认关闭与独立展开') await user.click(details.querySelector(':scope > summary')!)
  else fireEvent.click(details.querySelector(':scope > summary')!)
  expect(details).toHaveAttribute('open')
  if (state === '默认关闭与独立展开') {
    expect(within(details).getByRole('region', { name: `${channel}观点独立追溯` })).toBeVisible()
    for (const name of channels.filter(name => name !== channel)) expect(replayDisclosure(`${name}观点明细`)).not.toHaveAttribute('open')
  } else {
    fireEvent.change(replayCutoff(), { target: { value: '2026-01-01' } })
    for (const name of channels) {
      expect(screen.queryByLabelText(`${name}观点明细`)).not.toBeInTheDocument()
      expect(screen.queryByRole('region', { name: `${name}观点独立追溯` })).not.toBeInTheDocument()
    }
    expect(screen.queryByRole('region', { name: '综合市场分析' })).not.toBeInTheDocument()
    await user.click(replayToolbar().getByRole('button', { name: '恢复资料截止日' }))
    for (const name of channels) expect(replayDisclosure(`${name}观点明细`)).not.toHaveAttribute('open')
  }
})

it('从父阶段进入鹰派换届独立子页，完整日期与返回父阶段均正确', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: '进入鹰派换届与反转酝酿研究工作台' }))
  expect(window.location.hash).toBe(hawkishHash)
  const workbench = replayWorkbench('鹰派换届研究工作台')
  expect(workbench.querySelector('h1')).toHaveTextContent('鹰派换届与反转酝酿')
  expect(workbench.querySelector('.replay-heading')).toHaveTextContent(formatReplayText('2026-01-01—2026-08-31'))
  expect(workbench.querySelector('.replay-heading')).not.toHaveTextContent('终点未形成')
  expect(replayCutoff()).toHaveValue('2026-08-31')
  await user.click(replayHeading().getByRole('button', { name: '返回父阶段复盘' }))
  expect(window.location.hash).toBe(parentHash)
  expect(screen.getByRole('heading', { name: '细分时段复盘' })).toBeInTheDocument()
  expect(queryReplayWorkbench('鹰派换届研究工作台')).not.toBeInTheDocument()
})

it('直接加载鹰派换届hash，不回退到时期总览或九月工作台', () => {
  window.history.replaceState(null, '', hawkishHash)
  render(<App />)
  expect(replayWorkbench('鹰派换届研究工作台')).toBeInTheDocument()
  expect(queryReplayWorkbench('政策反转研究工作台')).not.toBeInTheDocument()
  expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument()
  act(() => window.dispatchEvent(new HashChangeEvent('hashchange')))
  expect(replayWorkbench('鹰派换届研究工作台')).toBeInTheDocument()
})
