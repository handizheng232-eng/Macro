import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { replayCutoff, replayDisclosure, replaySearch, replayWorkbench, replayHeading } from './historyReplay.testHelpers'
import firstData from './data/historyReplay.json'
import secondData from './data/historyReplayHawkishTransition.json'

const parent = '#history/easing-to-tightening'
const third = `${parent}/renewed-easing-qt-end`
beforeEach(() => window.history.replaceState(null, '', parent))

it('父阶段提供再降息与QT收官真实入口，窗口与截止正确，返回父阶段', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: '进入再降息与QT收官研究工作台' }))
  expect(window.location.hash).toBe(third)
  const workbench = replayWorkbench('再降息与QT收官研究工作台')
  expect(workbench.querySelector('h1')).toHaveTextContent('再降息与QT收官')
  expect(workbench.querySelector('.replay-heading')).toHaveTextContent('2025年9月1日至2025年12月31日')
  expect(replayCutoff()).toHaveValue('2025-12-31')
  await user.click(replayHeading().getByRole('button', { name: '返回父阶段复盘' }))
  expect(window.location.hash).toBe(parent)
  expect(screen.getByRole('heading', { name: '细分时段复盘' })).toBeInTheDocument()
})

const siblingCases = (['hashchange', 'popstate'] as const).flatMap(event => ['policy-reversal', 'hawkish-transition'].flatMap(sibling => [
  { event, from: third, to: `${parent}/${sibling}`, title: sibling === 'policy-reversal' ? firstData.title : secondData.title, asOf: sibling === 'policy-reversal' ? firstData.asOf : secondData.asOf },
  { event, from: `${parent}/${sibling}`, to: third, title: '再降息与QT收官', asOf: '2025-12-31' },
])).flatMap(route => (['截止日', '检索与展开'] as const).map(state => ({ ...route, state })))
// Keep both directions and both native event listeners; isolate independent
// local-state contracts instead of accumulating unnecessary full-page redraws.
it.each(siblingCases)('$event 从$from 到$to：$state 不串页', ({ event, from, to, title, asOf, state }) => {
  window.history.replaceState(null, '', from)
  const { container } = render(<App />)
  if (state === '检索与展开') {
    // Search, cutoff and disclosure state coexist in the lightweight historical
    // view; preparing it first avoids redrawing the unrelated full archive.
    const historicalCutoff = from === third ? '2025-09-01' : from.endsWith('hawkish-transition') ? secondData.startDate : firstData.startDate
    fireEvent.change(replayCutoff(), { target: { value: historicalCutoff } })
    expect(replayCutoff()).toHaveValue(historicalCutoff)
    const library = replayDisclosure('来源库 / 研报库明细')
    fireEvent.click(library.querySelector(':scope > summary')!)
    expect(library).toHaveAttribute('open')
    fireEvent.change(replaySearch(), { target: { value: '仅第三路由测试' } })
    expect(replaySearch()).toHaveValue('仅第三路由测试')
  } else {
    const cutoff = from === third ? '2025-09-01' : '2026-09-01'
    fireEvent.change(replayCutoff(), { target: { value: cutoff } })
    expect(replayCutoff()).toHaveValue(cutoff)
  }
  window.history.replaceState(null, '', to)
  act(() => window.dispatchEvent(event === 'hashchange' ? new HashChangeEvent(event) : new PopStateEvent(event)))
  expect(container.querySelector('.history-replay h1')).toHaveTextContent(title)
  expect(replayCutoff()).toHaveValue(asOf)
  expect(replaySearch()).toHaveValue('')
  for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细', '来源库 / 研报库明细']) expect(replayDisclosure(label)).not.toHaveAttribute('open')
})

it('真实浏览器history back/forward恢复第三页，主导航离开卸载', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: '进入再降息与QT收官研究工作台' }))
  const traverse = async (direction: 'back' | 'forward') => act(async () => {
    const done = new Promise<void>(resolve => window.addEventListener('popstate', () => resolve(), { once: true }))
    window.history[direction]()
    await done
  })
  await traverse('back')
  expect(window.location.hash).toBe(parent)
  await traverse('forward')
  expect(window.location.hash).toBe(third)
  expect(replayWorkbench('再降息与QT收官研究工作台')).toBeInTheDocument()
  await user.click(within(screen.getByRole('navigation', { name: '主导航' })).getByRole('button', { name: '今日总览' }))
  expect(screen.queryByLabelText('按日期截止查看')).not.toBeInTheDocument()
})

it('第三独立hash保留240节点、5+35导读，移除辅助图表且历史边界卸载', () => {
  window.history.replaceState(null, '', third)
  const { container } = render(<App />)
  expect(replayWorkbench('再降息与QT收官研究工作台')).toBeInTheDocument()
  expect(container.querySelectorAll('.replay-analysis-entries > li')).toHaveLength(240)
  expect(container.querySelectorAll('[data-period-summary]')).toHaveLength(5)
  expect(container.querySelectorAll('[data-aspect-summary]')).toHaveLength(35)
  expect(container.querySelectorAll('.replay-framework-card')).toHaveLength(0)
  expect(container.querySelectorAll('[data-reading-column]')).toHaveLength(40)
  expect(container.querySelector('#reading-paths svg')).not.toBeNull()
  for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细', '来源库 / 研报库明细']) expect(replayDisclosure(label)).not.toHaveAttribute('open')
  expect(screen.queryByRole('heading', { name: '预期 → 现实：事件时间轴' })).not.toBeInTheDocument()
  fireEvent.change(replayCutoff(), { target: { value: '2025-10-01' } })
  expect(screen.queryByRole('region', { name: '综合市场分析' })).not.toBeInTheDocument()
  expect(container.querySelectorAll('[data-period-summary], [data-aspect-summary], .replay-framework-card')).toHaveLength(0)
  for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细', '逐月预期现实与修订链', '月份与渠道覆盖']) expect(screen.queryByLabelText(label)).not.toBeInTheDocument()
  act(() => window.dispatchEvent(new HashChangeEvent('hashchange')))
  expect(replayCutoff()).toHaveValue('2025-10-01')
})
