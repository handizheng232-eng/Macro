import { formatReplayText } from './replayDateFormat'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'

it('微信当前覆盖审计在历史模式整体卸载，恢复日期仍为默认折叠', async () => {
  const user = userEvent.setup()
  const data: HistoryReplayData = {
    title: '测试覆盖回放', startDate: '2026-09-01', asOf: '2026-10-01', summary: [],
    sources: [], events: [], hypotheses: [], acquisition: [], reports: [],
    wechatCoverage: {
      requestedAccounts: [{ accountRequested: '测试检索原名', officialIdentityChecked: false, bodyObtainedCount: 0, status: '测试当前检索状态', limitations: '测试当前审计局限' }],
      actualAccounts: [{ accountActual: '测试真实发表账号', articleCount: 1 }],
      totalArticles: 1, totalOpinions: 0, limitations: ['测试当前覆盖局限'],
    },
  }
  render(<HistoryReplay data={data} onBack={() => {}} />)
  await user.click(screen.getByText('微信观点明细 · 0（点击展开）'))
  await user.click(screen.getByText('原始检索账号审计 · 1 个（点击展开）'))
  expect(screen.getByRole('region', { name: '微信公众号来源覆盖' })).toBeVisible()
  expect(screen.getByLabelText('公众号候选检索审计')).toHaveAttribute('open')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-30' } })
  expect(screen.queryByLabelText('微信观点明细')).not.toBeInTheDocument()
  expect(screen.queryByRole('region', { name: '微信公众号来源覆盖' })).not.toBeInTheDocument()
  for (const text of ['测试检索原名', '测试真实发表账号', '测试当前检索状态', '测试当前审计局限', '测试当前覆盖局限']) expect(screen.queryByText(new RegExp(text))).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByLabelText('微信观点明细')).not.toHaveAttribute('open')
  expect(screen.getByLabelText('公众号候选检索审计')).not.toHaveAttribute('open')
  expect(screen.getByRole('region', { name: '微信公众号来源覆盖' })).not.toBeVisible()
  await user.click(screen.getByText('微信观点明细 · 0（点击展开）'))
  expect(screen.getByRole('region', { name: '微信公众号来源覆盖' })).toHaveTextContent('测试真实发表账号 · 1 篇')
  expect(within(screen.getByLabelText('公众号候选检索审计')).getByRole('list')).not.toBeVisible()
})

beforeEach(() => window.history.replaceState(null, '', '#history/easing-to-tightening'))

it('正式研报按印刷刊发日展示，星球按文件名归档日展示，不混用冲突说明', async () => {
  const user = userEvent.setup()
  const data: HistoryReplayData = {
    title: '日期分层测试', startDate: '2026-01-01', asOf: '2026-08-31', summary: [],
    sources: [], events: [], hypotheses: [], acquisition: [],
    reports: [
      { id: 'formal', title: '正式报告日期测试', provider: '测试机构', path: 'formal.pdf',
        publicationDate: '2026-01-05', filenameDate: '2026-09-28', dateConflict: true,
        dateBasis: 'printed_publication_date; not_filename_date' },
      { id: 'star', title: '星球归档日期测试', provider: '知识星球', path: 'star.pdf',
        publicationDate: null, filenameDate: '2026-08-02', dateConflict: true,
        dateBasis: 'filename_date_user_preferred_publication_unverified' },
    ],
  }
  render(<HistoryReplay data={data} onBack={() => {}} />)
  await user.click(screen.getByText(/来源库 \/ 研报库 · 公开来源/))
  const formal = screen.getByText('正式报告日期测试').closest('article')!
  expect(formal).toHaveTextContent(formatReplayText('正文发布日期：2026-01-05'))
  expect(formal).toHaveTextContent('以正文发布日期为准')
  expect(formal).not.toHaveTextContent('以文件名归档日期优先')
  expect(screen.getByText('星球归档日期测试').closest('article')).toHaveTextContent(formatReplayText('研究归档日期（文件名优先）：2026-08-02'))
})

it('全站渠道标识区分知识星球已归档PDF与尚未建立实时接口', () => {
  render(<App />)
  expect(screen.getByLabelText('数据源状态')).toHaveTextContent('知识星球 PDF已归档')
  expect(screen.getByLabelText('数据源状态')).not.toHaveTextContent('知识星球待接入')
})

it('真实history.back和forward在父子页面间往返', async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: '进入重启加息：政策反转研究工作台' }))
  // Await native traversal before scanning the large report DOM. Polling getByRole
  // can exhaust waitFor's 1s budget before jsdom's nested traversal timers run.
  await act(async () => {
    const navigated = new Promise<void>((resolve) => window.addEventListener('popstate', () => resolve(), { once: true }))
    window.history.back()
    await navigated
  })
  await waitFor(() => expect(screen.getByRole('heading', { name: '细分时段复盘' })).toBeInTheDocument())
  await act(async () => {
    const navigated = new Promise<void>((resolve) => window.addEventListener('popstate', () => resolve(), { once: true }))
    window.history.forward()
    await navigated
  })
  await waitFor(() => expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument())
  expect(screen.getByRole('figure', { name: '复盘方法框架' })).toBeInTheDocument()
  for (const label of ['星球观点明细', 'Wind观点明细', '微信观点明细', '来源库 / 研报库明细']) {
    expect(screen.getByLabelText(label)).not.toHaveAttribute('open')
  }
  await user.click(screen.getByText(/来源库 \/ 研报库.*点击展开/))
  expect(screen.getByLabelText('来源库 / 研报库明细')).toHaveAttribute('open')
  expect(screen.getByRole('searchbox', { name: '检索资料' })).toBeVisible()
})

it('仅10.4与10.5提供入口，旧独立hash可加载并返回父阶段', async () => {
  const user = userEvent.setup()
  render(<App />)
  expect(screen.getAllByRole('button', { name: /进入.*研究工作台/ }).map((button) => button.textContent?.trim())).toEqual([
    '进入重启加息：政策反转研究工作台', '进入鹰派换届与反转酝酿研究工作台',
  ])
  await user.click(screen.getByRole('button', { name: '进入重启加息：政策反转研究工作台' }))
  expect(window.location.hash).toBe('#history/easing-to-tightening/policy-reversal')
  expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '返回父阶段复盘' }))
  expect(window.location.hash).toBe('#history/easing-to-tightening')
})

it('直接加载子页，前后退和hashchange恢复正确层级', () => {
  window.history.replaceState(null, '', '#history/easing-to-tightening/policy-reversal')
  render(<App />)
  expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument()
  window.history.replaceState(null, '', '#history/easing-to-tightening')
  act(() => window.dispatchEvent(new PopStateEvent('popstate')))
  expect(screen.getByRole('heading', { name: '细分时段复盘' })).toBeInTheDocument()
  window.history.replaceState(null, '', '#history/easing-to-tightening/policy-reversal')
  act(() => window.dispatchEvent(new HashChangeEvent('hashchange')))
  expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument()
})

it.each(['front-loaded-easing', 'tariff-pause', 'qt-end'])('不提供未构建子页 %s', (slug) => {
  window.history.replaceState(null, '', `#history/easing-to-tightening/${slug}`)
  render(<App />)
  expect(screen.queryByRole('heading', { name: '预期 → 现实：事件时间轴' })).not.toBeInTheDocument()
})
