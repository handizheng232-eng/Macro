import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'
import replayData from './data/historyReplay.json'

// Artificial fixtures are test-only, never production research data.
const fixture: HistoryReplayData = {
  title: '测试工作台', startDate: '2026-09-01', asOf: '2026-10-01', summary: ['事后总结'],
  sources: [
    { id: 'prior', title: '测试事前来源', publisher: '测试机构', date: '2026-09-10', url: 'https://example.org/prior', kind: '预期', status: '已核验', note: '' },
    { id: 'release', title: '测试发布来源', publisher: '测试机构', date: '2026-09-16', url: 'https://example.org/release', kind: '事实', status: '已核验', note: '事后来源备注' },
    { id: 'later', title: '未来来源', publisher: '测试机构', date: '2026-09-30', url: 'https://example.org/later', kind: '修订', status: '已核验', note: '' },
    { id: 'unsafe', title: '非公开来源', publisher: '测试机构', date: '2026-09-16', url: 'file:///private/report.pdf', kind: '研报', status: '授权', note: '' },
  ],
  events: [
    { id: 'meeting', date: '2026-09-16', title: '测试会议', observationPeriod: '2026-08', expectation: '事前预期内容', expectationSourceIds: ['prior'], reality: '发布现实内容', realitySourceIds: ['release'], interpretation: '事后解释内容', marketResponse: '事后市场反应', confidence: '测试评级' },
    { id: 'revision', date: '2026-09-30', title: '测试修订', observationPeriod: '2026-08', expectation: '后来写的预期', expectationSourceIds: ['later'], reality: '修订现实', realitySourceIds: ['later'], interpretation: '', marketResponse: '', confidence: '' },
  ],
  hypotheses: [{ title: '当前判断', test: '验证条件', invalidator: '反证条件', status: '待验证' }],
  acquisition: [{ provider: '测试渠道', status: '授权受限', detail: '不可下载' }],
  reports: [{ title: '本地授权报告', date: '2026-09-16', provider: '测试机构', path: 'E:/private/report.pdf', scope: '测试主题', note: '仅本地' }],
}

it('已结束阶段以独立工作台标识显示完整起止日期，不显示开放期文案', () => {
  // Only UI metadata; no empirical claims are supplied by this fixture.
  const closedStage: HistoryReplayData & { endDate: string; workbenchLabel: string; eyebrow: string } = {
    title: '鹰派换届与反转酝酿', startDate: '2026-01-01', endDate: '2026-08-31', asOf: '2026-08-31',
    workbenchLabel: '鹰派换届研究工作台', eyebrow: 'HAWKISH TRANSITION · RESEARCH WORKBENCH',
    summary: [], sources: [], events: [], hypotheses: [], acquisition: [], reports: [],
  }
  render(<HistoryReplay data={closedStage} onBack={() => {}} />)
  const workbench = screen.getByRole('article', { name: '鹰派换届研究工作台' })
  expect(workbench.querySelector('.replay-heading')).toHaveTextContent('2026-01-01—2026-08-31')
  expect(workbench.querySelector('.replay-heading')).toHaveTextContent(closedStage.eyebrow)
  expect(workbench.querySelector('.replay-heading')).not.toHaveTextContent('开放时期')
  expect(workbench.querySelector('.replay-heading')).not.toHaveTextContent('终点未形成')
  expect(screen.getByLabelText('按日期截止查看')).toHaveValue(closedStage.asOf)
})

it('本地PDF观点独立默认折叠，不伪装星球；历史模式卸载且恢复仍折叠', async () => {
  const user = userEvent.setup()
  const item = { reportId: 'local-ui-report', expressedAt: '2026-09-12', dateBasis: '测试正文日期',
    actor: '测试本地机构', claim: '仅测试本地渠道观点', scope: '测试主题', pages: [1],
    evidenceExcerpt: '测试本地短摘录', limitations: ['测试局限'] }
  const data: HistoryReplayData & { localResearchEvidence: typeof item[] } = {
    ...fixture, localResearchEvidence: [item],
  }
  render(<HistoryReplay data={data} onBack={() => {}} />)
  const details = screen.getByLabelText('本地研报观点明细')
  expect(details).not.toHaveAttribute('open')
  fireEvent.click(screen.getByLabelText('来源库 / 研报库明细').querySelector(':scope > summary')!)
  await user.click(within(details).getByText('本地研报观点明细 · 1（点击展开）'))
  const region = screen.getByRole('region', { name: '本地研报观点独立追溯' })
  expect(region).toBeVisible()
  expect(region).toHaveTextContent(item.claim)
  expect(region).toHaveTextContent('证据页：1')
  expect(region).toHaveTextContent('事后报告不倒填会前预期')
  expect(region).not.toHaveTextContent('平台发帖日')
  expect(screen.getByLabelText('星球观点明细')).not.toHaveTextContent(item.claim)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-20' } })
  expect(screen.queryByLabelText('本地研报观点明细')).not.toBeInTheDocument()
  expect(screen.queryByText(item.claim)).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByLabelText('本地研报观点明细')).not.toHaveAttribute('open')
  expect(screen.getByRole('region', { name: '本地研报观点独立追溯' })).not.toBeVisible()
})

it('短摘录缺失时明确标注页码已核而非留空或补造原文', () => {
  const item = { reportId: 'test-pdf', expressedAt: '2026-02-11', dateBasis: '印刷日',
    actor: '测试机构', claim: '测试条件性观点', scope: '美国利率', pages: [13, 14], evidenceExcerpt: '' }
  render(<HistoryReplay data={{ ...fixture, windResearchEvidence: [item] }} onBack={() => {}} />)
  expect(screen.getByLabelText('Wind观点独立追溯')).toHaveTextContent('无可引短摘录；页码与原文位置已核验')
  expect(screen.getByLabelText('Wind观点独立追溯')).toHaveTextContent('证据页：13、14')
})

it('截止筛选事件、来源、研报并隐藏事后判断，恢复日期返回完整资料', async () => {
  const user = userEvent.setup()
  render(<HistoryReplay data={fixture} onBack={() => {}} />)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-16' } })
  expect(screen.getByRole('heading', { name: '测试会议' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: '测试修订' })).not.toBeInTheDocument()
  expect(screen.queryByText('未来来源')).not.toBeInTheDocument()
  expect(screen.queryByText('事后总结')).not.toBeInTheDocument()
  expect(screen.queryByText('当前判断')).not.toBeInTheDocument()
  expect(screen.queryByText('事后解释内容')).not.toBeInTheDocument()
  expect(screen.queryByText('事后市场反应')).not.toBeInTheDocument()
  expect(screen.queryByText('事后来源备注')).not.toBeInTheDocument()
  expect(screen.getAllByText('事前预期内容')).toHaveLength(2)
  await user.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByRole('heading', { name: '测试修订' })).toBeInTheDocument()
  expect(screen.getByText('事后总结')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-10' } })
  expect(screen.queryByText('本地授权报告')).not.toBeInTheDocument()
})

it('显示精确来源URL，检索双资料库，本地授权路径不成为下载链接', async () => {
  const user = userEvent.setup()
  render(<HistoryReplay data={fixture} onBack={() => {}} />)
  expect(screen.getByRole('link', { name: '测试事前来源 ↗' })).toHaveAttribute('href', 'https://example.org/prior')
  const details = screen.getByLabelText('来源库 / 研报库明细')
  expect(details.tagName).toBe('DETAILS')
  expect(details).not.toHaveAttribute('open')
  expect(screen.getByRole('region', { name: '来源与研报库' })).not.toBeVisible()
  await user.click(within(details).getByText('来源库 / 研报库 · 公开来源 3 / 授权研报 1（点击展开）'))
  expect(details).toHaveAttribute('open')
  const library = screen.getByRole('region', { name: '来源与研报库' })
  expect(library).toBeVisible()
  expect(within(library).getByText('E:/private/report.pdf')).toBeInTheDocument()
  expect(within(library).getAllByRole('link').every((link) => link.getAttribute('href')?.startsWith('https://'))).toBe(true)
  expect(screen.getByText(/量化数据缺失/)).toBeInTheDocument()
  await user.type(screen.getByRole('searchbox', { name: '检索资料' }), '测试主题')
  expect(within(library).getByText('本地授权报告')).toBeInTheDocument()
  expect(within(library).queryByText('测试事前来源')).not.toBeInTheDocument()
})

it('完整视图登记121份正文日期未知的授权PDF，平台日不是正文发布日期', () => {
  const reports = Array.from({ length: 121 }, (_, index) => ({
    id: `planet-${index}`, title: `星球转录-${index}`, date: null,
    publicationDate: null, postDate: '2026-09-12', dateBasis: 'platform_post_date_only',
    provider: '知识星球', path: `E:/private/planet-${index}.pdf`, geography: '美国', topics: ['联储政策'],
  }))
  render(<HistoryReplay data={{ ...fixture, reports }} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/来源库 \/ 研报库.*点击展开/))
  const library = screen.getByRole('region', { name: '来源与研报库' })
  expect(within(library).getByRole('heading', { name: '授权研报 · 121' })).toBeInTheDocument()
  expect(within(library).getAllByText('正文发布日期：未知')).toHaveLength(121)
  expect(within(library).getAllByText(/平台发帖日：2026-09-12/)).toHaveLength(121)
  expect(within(library).getAllByText(/platform_post_date_only/)).toHaveLength(121)
  expect(within(library).getAllByText(/对象：美国 · 主题：联储政策/)).toHaveLength(121)
  expect(within(library).getAllByRole('link').every((link) => !link.getAttribute('href')?.endsWith('.pdf'))).toBe(true)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-20' } })
  expect(within(library).queryByText('星球转录-0')).not.toBeInTheDocument()
  expect(within(library).getByRole('heading', { name: '授权研报 · 0' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(within(library).getByRole('heading', { name: '授权研报 · 121' })).toBeInTheDocument()
  fireEvent.change(screen.getByRole('searchbox', { name: '检索资料' }), { target: { value: '联储政策' } })
  expect(within(library).getByRole('heading', { name: '授权研报 · 121' })).toBeInTheDocument()
})

it('父方书目scope与主题分别显示，即使未单独提供geography也不丢失对象', () => {
  render(<HistoryReplay data={{ ...fixture, reports: [{ id: 'parent-report', title: '父方书目', date: null,
    provider: '机构未确认', path: '报告/知识星球/a.pdf', scope: '平台区间候选·美国', topics: ['美联储与货币政策'],
    postDate: '2026-09-01', dateBasis: 'publication_date_unconfirmed; attachment_topic_link_unconfirmed' }] }} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/来源库 \/ 研报库.*点击展开/))
  expect(screen.getByText('对象：平台区间候选·美国 · 主题：美联储与货币政策')).toBeInTheDocument()
  expect(screen.getByText(/attachment_topic_link_unconfirmed/)).toBeInTheDocument()
})

it('12条已审计星球观点仅当前复盘可追溯，保留平台日期局限和待验证状态', () => {
  const researchEvidence = Array.from({ length: 12 }, (_, index) => ({
    reportId: `planet-${index}`, eventId: index === 0 ? 'meeting' : null,
    expressedAt: '2026-09-12', dateBasis: 'platform_post_date_only', actor: '测试作者',
    claim: `审计观点-${index}`, scope: '美国利率', value: null, unit: null,
    observationPeriod: '2026-09', pages: [1, 2], evidenceExcerpt: `审计摘录-${index}`,
    limitations: ['正文日期未确认'], reportTitle: `审计PDF-${index}`, localPath: `E:/private/audit-${index}.pdf`,
    reality: index === 0 ? '已关联会议现实' : null, eventDate: index === 0 ? '2026-09-16' : null,
    status: index === 0 ? '已对照' : '待验证',
  }))
  render(<HistoryReplay data={{ ...fixture, researchEvidence }} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/星球观点明细.*点击展开/))
  const section = screen.getByRole('region', { name: '星球观点独立追溯' })
  expect(within(section).getAllByRole('article')).toHaveLength(12)
  expect(within(section).getByText(/不构成严格事前市场共识/)).toBeInTheDocument()
  expect(within(section).getByText(/平台发帖日.*正文发布日期.*事件日期关联不明/)).toBeInTheDocument()
  expect(within(section).getByText('审计观点-0')).toBeInTheDocument()
  expect(within(section).getByText('已关联会议现实')).toBeInTheDocument()
  expect(within(section).getAllByText('待验证')).toHaveLength(11)
  expect(within(section).getAllByText(/platform_post_date_only/)).toHaveLength(12)
  expect(within(section).getByText('审计摘录-0')).toBeInTheDocument()
  expect(within(section).getAllByText(/证据页：1、2/)).toHaveLength(12)
  expect(within(section).getByText('E:/private/audit-0.pdf')).toBeInTheDocument()
  expect(within(section).queryAllByRole('link')).toHaveLength(0)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-20' } })
  expect(screen.queryByRole('region', { name: '星球观点独立追溯' })).not.toBeInTheDocument()
  expect(screen.queryByText('审计观点-0')).not.toBeInTheDocument()
  expect(screen.queryByText('审计摘录-0')).not.toBeInTheDocument()
})

it('观点原始数值对象保留条件字段，不把条件情景对象写成确定预测', () => {
  const researchEvidence = [{ reportId: 'conditional-report', expressedAt: '2026-09-06', dateBasis: '平台日，正文未确认',
    actor: '条件观点作者', claim: '条件未成立则不得判定预测失败', scope: 'institutional_conditional_expectation',
    value: { conditionalChangeBp: 0, unchangedScenarioVote: [9, 3] }, unit: '基点（条件成立时）',
    pages: [7], evidenceExcerpt: '测试极短摘录', limitations: '不是无条件预测' }]
  render(<HistoryReplay data={{ ...fixture, researchEvidence }} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/星球观点明细.*点击展开/))
  const section = screen.getByRole('region', { name: '星球观点独立追溯' })
  expect(section.textContent).toContain('"conditionalChangeBp": 0')
  expect(section.textContent).toContain('"unchangedScenarioVote"')
  expect(section.textContent).not.toContain('[object Object]')
  expect(section.textContent).toContain('基点（条件成立时）')
})

it('Wind正文审计观点独立展示，事后报告不得冒充会前共识，历史模式隐藏当前对照', () => {
  const windResearchEvidence = [{ reportId: 'wind-pdf-test', expressedAt: '2026-09-19', dateBasis: '正文封面日期已核验',
    actor: '测试Wind机构', claim: '后续行动测试预测', scope: '美国货币政策', value: null, unit: null,
    pages: [2], evidenceExcerpt: '短摘录测试', limitations: ['结果尚未发生'], reportTitle: '测试Wind报告',
    localPath: '报告/Wind/test.pdf', reality: '待后续验证', status: '待验证' }]
  render(<HistoryReplay data={{ ...fixture, windResearchEvidence }} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/Wind观点明细.*点击展开/))
  const region = screen.getByRole('region', { name: 'Wind观点独立追溯' })
  expect(within(region).getByRole('heading', { name: 'Wind观点 → 现实 / 待验证 · 1' })).toBeInTheDocument()
  expect(region).toHaveTextContent('事后报告不倒填会前预期')
  expect(region).toHaveTextContent('具名机构观点不等同于市场共识')
  expect(within(region).getByText('后续行动测试预测')).toBeInTheDocument()
  expect(within(region).getByText('观点日期：2026-09-19 · 日期依据：正文封面日期已核验')).toBeInTheDocument()
  expect(within(region).queryAllByRole('link')).toHaveLength(0)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-30' } })
  expect(screen.queryByRole('region', { name: 'Wind观点独立追溯' })).not.toBeInTheDocument()
})

// Artificial market observations are test-only and do not populate the research artifact.
const marketPaths = {
  series: [
    { id: 'fed-upper', title: '联储目标上限', unit: '%', sourceUrl: 'https://example.org/fed', status: '已取得', limitations: ['政策目标不是期货隐含路径'], observations: [
      { date: '2026-09-10', value: 4.5, releaseDate: '2026-09-10', historicalAsOfEligible: true },
      { date: '2026-09-11', value: null, releaseDate: '2026-09-11', historicalAsOfEligible: true, missingReason: '测试真实缺口' },
      { date: '2026-09-12', value: 4.25, releaseDate: '2026-09-12', historicalAsOfEligible: true },
    ] },
    { id: 'treasury-10y', title: '美国十年国债收益率', unit: '%', sourceUrl: 'https://example.org/treasury', status: '当前取得', limitations: ['首次发布日期未确认'], observations: [
      { date: '2026-09-10', value: 4.12, releaseDate: null, historicalAsOfEligible: false, availableBy: '2026-10-01' },
      { date: '2026-09-12', value: 4.08, releaseDate: null, historicalAsOfEligible: false, availableBy: '2026-10-01' },
    ] },
    { id: 'broad-dollar', title: '贸易加权广义美元指数', unit: '2006年1月=100', sourceUrl: 'https://example.org/dollar', status: '已取得', limitations: ['不是DXY'], observations: [
      { date: '2026-09-10', value: 119.25, releaseDate: '2026-09-11', historicalAsOfEligible: true },
      { date: '2026-09-12', value: 119.5, releaseDate: '2026-09-25', historicalAsOfEligible: true },
    ] },
  ],
  cmeHistoricalImpliedPath: { status: '缺失', limitations: ['未取得历史概率快照'] },
}

it('真实行情按百分比同轴和非DXY美元独立轴显示，null断线且缺口文案随真实序列改变', () => {
  render(<HistoryReplay data={{ ...fixture, marketPaths }} onBack={() => {}} />)
  const region = screen.getByRole('region', { name: '真实行情路径' })
  const rates = within(region).getByRole('img', { name: '利率路径（%）' })
  const dollar = within(region).getByRole('img', { name: '贸易加权广义美元指数（2006年1月=100）' })
  expect(rates.querySelectorAll('path[data-series-id]')).toHaveLength(2)
  expect(dollar.querySelectorAll('path[data-series-id]')).toHaveLength(1)
  const fedPath = rates.querySelector('path[data-series-id="fed-upper"]')?.getAttribute('d') || ''
  expect(fedPath.match(/M/g)).toHaveLength(2)
  expect(fedPath).not.toContain('L')
  expect(rates.querySelectorAll('circle')).toHaveLength(4)
  expect(within(region).getByText('测试真实缺口')).toBeInTheDocument()
  expect(within(region).getByText(/美元独立轴.*不是DXY/)).toBeInTheDocument()
  expect(screen.queryByText(/尚无经核验的.*全区间美元与美债序列/)).not.toBeInTheDocument()
  expect(screen.getByText(/真实序列已接入/)).toBeInTheDocument()
  expect(screen.getByText(/会前利率期货隐含路径仍缺失/)).toBeInTheDocument()
  expect(within(region).getAllByText('首次发布日期未确认').length).toBeGreaterThan(0)
  expect(within(region).getByRole('link', { name: '美国十年国债收益率 · 原始来源 ↗' })).toHaveAttribute('href', 'https://example.org/treasury')
})

it('沿用审计行情原生单位，percent_per_annum两条国债收益率合并同轴', () => {
  const nativePaths = { ...marketPaths, series: marketPaths.series.map((series) => ({
    ...series, unit: series.unit === '%' ? 'percent_per_annum' : 'index_Jan2006_100',
  })) }
  render(<HistoryReplay data={{ ...fixture, marketPaths: nativePaths }} onBack={() => {}} />)
  const rates = screen.getByRole('img', { name: '利率路径（%）' })
  expect(rates.querySelectorAll('path[data-series-id]')).toHaveLength(2)
  expect(screen.getByRole('img', { name: '贸易加权广义美元指数（2006年1月=100）' })).toBeInTheDocument()
})

it('历史行情只含严格可得且已发布的观测，不泄漏国债未确认发布日期值或当前元数据', () => {
  const paths = { ...marketPaths, series: marketPaths.series.map((series) => ({
    ...series, status: '当前获取的事后状态', limitations: ['事后区间变化为隐藏数字'],
    derivedIntervalChange: { change: '隐藏衍生数值' },
  })) }
  render(<HistoryReplay data={{ ...fixture, marketPaths: paths }} onBack={() => {}} />)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-12' } })
  const region = screen.getByRole('region', { name: '真实行情路径' })
  expect(region.textContent).not.toContain('4.12')
  expect(region.textContent).not.toContain('4.08')
  expect(region.textContent).not.toContain('119.5')
  expect(region.innerHTML).not.toContain('119.5')
  expect(region.innerHTML).not.toContain('2026-09-25')
  expect(region.textContent).not.toContain('当前获取的事后状态')
  expect(region.textContent).not.toContain('隐藏数字')
  expect(region.textContent).not.toContain('隐藏衍生数值')
  const rates = within(region).getByRole('img', { name: '利率路径（%）' })
  expect(rates.querySelectorAll('circle')).toHaveLength(2)
  expect(rates.querySelector('path[data-series-id="treasury-10y"]')?.getAttribute('d')?.trim()).toBe('')
  const dollar = within(region).getByRole('img', { name: '贸易加权广义美元指数（2006年1月=100）' })
  expect(dollar.querySelectorAll('circle')).toHaveLength(1)
  expect(region.textContent).toContain('119.25')
  expect(within(region).getByText(/historicalAsOfEligible.*releaseDate.*截止日/)).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-09' } })
  expect(within(region).queryAllByRole('img')).toHaveLength(0)
  expect(region.textContent).not.toContain('119.25')
  expect(within(region).getAllByText(/暂无可绘制观测/)).toHaveLength(2)
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(region.textContent).toContain('4.12')
  expect(region.textContent).toContain('119.5')
})

it('顶部方法框架紧随标题、先于日期工具与时间轴，历史截面仍保留', () => {
  const { container } = render(<HistoryReplay data={fixture} onBack={() => {}} />)
  const framework = screen.getByRole('figure', { name: '复盘方法框架' })
  expect(container.querySelector('.replay-heading')?.nextElementSibling).toBe(framework)
  expect(within(framework).getAllByRole('listitem').map((node) => node.textContent)).toEqual([
    '事前预期', '数据 / 政策事件', '美债 / 美元重定价', '后续验证 / 修正',
  ])
  expect(framework).toHaveTextContent('↶ 反馈：修正预期')
  expect(framework).toHaveTextContent('日频变化不等于因果')
  expect(framework.compareDocumentPosition(screen.getByRole('region', { name: '事件时间轴' })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-16' } })
  expect(screen.getByRole('figure', { name: '复盘方法框架' })).toBeInTheDocument()
})

it('前置综合分析呈现观点到验证链、解析引用，不重复摘要且严格历史截面整体卸载', async () => {
  const user = userEvent.setup()
  const data = { ...fixture,
    reports: [{ ...fixture.reports[0], id: 'analysis-report' }],
    marketAnalysis: { title: '综合市场分析', conclusion: '测试综合结论', sections: [{
      id: 'rates', title: '利率研究主题', judgement: '测试主题判断', expectation: '测试机构观点',
      reality: '测试落地事实', mechanism: '测试传导机制', divergence: '测试预期差',
      implication: '测试市场含义', validation: '测试验证条件',
      sourceIds: ['prior', 'unsafe', 'missing-source'], reportIds: ['analysis-report', 'missing-report'],
    }], limitations: ['测试综合研究局限'] },
  }
  render(<HistoryReplay data={data} onBack={() => {}} />)
  const analysis = screen.getByRole('region', { name: '综合市场分析' })
  expect(analysis.closest('details')).toBeNull()
  expect(screen.getByRole('figure', { name: '复盘方法框架' }).compareDocumentPosition(analysis) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(analysis.compareDocumentPosition(screen.getByRole('region', { name: '事件时间轴' })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(within(analysis).getAllByRole('term').map((term) => term.textContent)).toEqual(['观点 / 事前预期', '现实', '机制', '分歧 / 预期差', '市场含义', '验证条件'])
  for (const text of ['测试综合结论', '测试主题判断', '测试机构观点', '测试落地事实', '测试传导机制', '测试预期差', '测试市场含义', '测试验证条件', '测试综合研究局限']) expect(analysis).toHaveTextContent(text)
  expect(within(analysis).getByRole('link', { name: '测试事前来源 ↗' })).toHaveAttribute('href', 'https://example.org/prior')
  expect(within(analysis).getByText('非公开来源 · 无公开URL')).toBeInTheDocument()
  expect(analysis).toHaveTextContent('本地授权报告')
  expect(analysis).toHaveTextContent('研报未在截止日前核验')
  expect(within(analysis).getAllByRole('link').every((link) => !link.getAttribute('href')?.endsWith('.pdf'))).toBe(true)
  expect(screen.queryByRole('region', { name: '研究摘要' })).not.toBeInTheDocument()
  expect(screen.queryByText('事后总结')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-30' } })
  expect(screen.queryByRole('region', { name: '综合市场分析' })).not.toBeInTheDocument()
  expect(screen.queryByText('测试综合结论')).not.toBeInTheDocument()
  expect(screen.queryByText('测试传导机制')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByRole('region', { name: '综合市场分析' })).toHaveTextContent('测试综合结论')
})

it.each(['星球', 'Wind', '微信'] as const)('%s观点独立默认折叠、可点击展开，严格历史截面卸载', async (channel) => {
  const user = userEvent.setup()
  const item = { reportId: 'test-report', expressedAt: '2026-09-12', dateBasis: '测试日期依据',
    actor: '测试作者', claim: '测试渠道观点', scope: '美国政策', pages: [1], evidenceExcerpt: '测试短摘录', limitations: ['测试局限'] }
  const data = { ...fixture, researchEvidence: [item], windResearchEvidence: [item], wechatResearchEvidence: [item] }
  render(<HistoryReplay data={data} onBack={() => {}} />)
  const details = screen.getByLabelText(`${channel}观点明细`)
  expect(details.tagName).toBe('DETAILS')
  expect(details).not.toHaveAttribute('open')
  expect(screen.getByRole('region', { name: `${channel}观点独立追溯` })).not.toBeVisible()
  await user.click(within(details).getByText(`${channel}观点明细 · 1（点击展开）`))
  expect(details).toHaveAttribute('open')
  expect(screen.getByRole('region', { name: `${channel}观点独立追溯` })).toHaveTextContent('测试渠道观点')
  for (const other of ['星球', 'Wind', '微信'].filter((name) => name !== channel)) expect(screen.getByLabelText(`${other}观点明细`)).not.toHaveAttribute('open')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-20' } })
  for (const name of ['星球', 'Wind', '微信']) expect(screen.queryByLabelText(`${name}观点明细`)).not.toBeInTheDocument()
  expect(screen.queryByText('测试渠道观点')).not.toBeInTheDocument()
})

// Test-only acquisition audit: candidate accounts are not obtained article bodies.
const coverageFixture = {
  requestedAccounts: ['CS宏观研究', '中金宏观', '奇霖宏观', '招商宏观静思录', '泽平宏观', '郭磊宏观茶座', '梁中华宏观研究', '经济学家圈', '张伟经济观察', '首席经济学家论坛'].map((accountRequested) => ({
    accountRequested, officialIdentityChecked: accountRequested === '首席经济学家论坛',
    bodyObtainedCount: accountRequested === '首席经济学家论坛' ? 2 : 0,
    status: accountRequested === '首席经济学家论坛' ? '正文已取得' : '仅检索线索，正文未取得',
    limitations: accountRequested === '中金宏观' ? '中金点睛为开放池扩展来源，不强配为中金宏观。' : '测试检索局限',
  })),
  actualAccounts: [{ accountActual: '中金点睛', articleCount: 1 }, { accountActual: '首席经济学家论坛', articleCount: 2 }],
  totalArticles: 3, totalOpinions: 4, limitations: ['测试覆盖局限：并非穷尽检索。'],
}

it('微信覆盖说明区分实际正文与十账号检索审计，保持两层默认折叠', async () => {
  const user = userEvent.setup()
  render(<HistoryReplay data={{ ...fixture, wechatCoverage: coverageFixture }} onBack={() => {}} />)
  const outer = screen.getByLabelText('微信观点明细')
  expect(outer).not.toHaveAttribute('open')
  const coverage = screen.getByRole('region', { name: '微信公众号来源覆盖' })
  expect(coverage).not.toBeVisible()
  await user.click(within(outer).getByText('微信观点明细 · 0（点击展开）'))
  expect(coverage).toBeVisible()
  expect(coverage).toHaveTextContent('已取得正文 3 篇 · 提取观点 4 条')
  expect(coverage).toHaveTextContent('中金点睛 · 1 篇')
  expect(coverage).toHaveTextContent('首席经济学家论坛 · 2 篇')
  expect(coverage).toHaveTextContent('检索清单不等于已取得正文')
  expect(coverage).toHaveTextContent('论坛不视为独立研究机构')
  expect(coverage).toHaveTextContent('同机构多个渠道不计为独立共识')
  expect(coverage).toHaveTextContent('测试覆盖局限：并非穷尽检索。')
  const audit = within(coverage).getByLabelText('公众号候选检索审计')
  expect(audit).not.toHaveAttribute('open')
  expect(within(audit).getByRole('list')).not.toBeVisible()
  await user.click(within(audit).getByText('原始检索账号审计 · 10 个（点击展开）'))
  const rows = within(audit).getAllByRole('listitem')
  expect(rows).toHaveLength(10)
  expect(rows.map((row) => row.querySelector('strong')?.textContent)).toEqual(coverageFixture.requestedAccounts.map((account) => account.accountRequested))
  const requestedCicc = rows[1]
  expect(requestedCicc).toHaveTextContent('仅检索线索，正文未取得')
  expect(requestedCicc).toHaveTextContent('已取得正文 0 篇')
  expect(requestedCicc).toHaveTextContent('官方身份未确认')
  expect(requestedCicc).toHaveTextContent('中金点睛为开放池扩展来源，不强配为中金宏观。')
  expect(rows[9]).toHaveTextContent('官方身份已核验')
  expect(within(coverage).queryAllByRole('link')).toHaveLength(0)
  expect(within(coverage).queryAllByRole('article')).toHaveLength(0)
  expect(screen.getByLabelText('Wind观点明细')).not.toHaveAttribute('open')
  expect(screen.getByLabelText('星球观点明细')).not.toHaveAttribute('open')
})

it('微信书目区分发表账号与原始研究来源，保留作者及原创转载属性', async () => {
  const user = userEvent.setup()
  const report = { ...fixture.reports[0], id: 'reposted', title: '测试转载文章',
    accountActual: '首席经济学家论坛', authors: ['测试作者甲', '测试作者乙'], researchOrigin: '测试原始研究机构', distributionType: '转载' }
  const original = { ...fixture.reports[0], id: 'original', title: '测试原创文章',
    accountActual: '测试原创账号', authors: '测试原创作者', researchOrigin: '测试原创研究机构', distributionType: '原创' }
  const wechatResearchEvidence = [report, original].map((entry) => ({
    reportId: entry.id, expressedAt: '2026-09-16', dateBasis: '测试正文日期', actor: '测试观点作者',
    claim: entry.title, scope: '测试政策', pages: ['p001'], evidenceExcerpt: '测试短摘录', limitations: [],
  }))
  render(<HistoryReplay data={{ ...fixture, reports: [report, original], wechatResearchEvidence }} onBack={() => {}} />)
  await user.click(screen.getByText('微信观点明细 · 2（点击展开）'))
  const region = screen.getByRole('region', { name: '微信观点独立追溯' })
  const cards = within(region).getAllByRole('article')
  expect(cards[0]).toHaveTextContent('发表账号：首席经济学家论坛')
  expect(cards[0]).toHaveTextContent('作者：测试作者甲、测试作者乙')
  expect(cards[0]).toHaveTextContent('研究来源：测试原始研究机构')
  expect(cards[0]).toHaveTextContent('分发类型：转载')
  expect(cards[1]).toHaveTextContent('发表账号：测试原创账号')
  expect(cards[1]).toHaveTextContent('作者：测试原创作者')
  expect(cards[1]).toHaveTextContent('分发类型：原创')
  expect(within(region).queryAllByRole('link')).toHaveLength(0)
  await user.click(screen.getByText(/来源库 \/ 研报库.*点击展开/))
  const library = screen.getByRole('region', { name: '来源与研报库' })
  expect(library).toHaveTextContent('发表账号：首席经济学家论坛')
  expect(library).toHaveTextContent('研究来源：测试原始研究机构')
})

it('微信未提供正文证据时显示零条空状态，不造观点', async () => {
  const user = userEvent.setup()
  render(<HistoryReplay data={fixture} onBack={() => {}} />)
  const supplement = screen.getByLabelText('本地研报观点明细')
  expect(supplement).not.toHaveAttribute('open')
  expect(within(supplement).queryAllByRole('article')).toHaveLength(0)
  const details = screen.getByLabelText('微信观点明细')
  expect(details).not.toHaveAttribute('open')
  await user.click(within(details).getByText('微信观点明细 · 0（点击展开）'))
  const region = screen.getByRole('region', { name: '微信观点独立追溯' })
  expect(region).toHaveTextContent('暂无已核验的微信观点正文，尚未形成观点与现实对照。')
  expect(within(region).queryAllByRole('article')).toHaveLength(0)
  expect(within(region).queryByRole('region', { name: '微信公众号来源覆盖' })).not.toBeInTheDocument()
  expect(within(region).queryByText(/发表账号：|研究来源：|分发类型：/)).not.toBeInTheDocument()
})

it('文件名优先显示研究归档日、平台日备查与冲突警告，不冒充正文发布且历史排除不可得报告', () => {
  const reports = [{ id: 'filename-report', title: '文件名归档报告', date: '2026-09-20', filenameDate: '2026-09-19',
    publicationDate: null, postDate: '2026-09-20', dateBasis: 'filename_date_user_preferred; publication_date_unconfirmed',
    dateConflict: true, historicalAsOfEligible: false, provider: '知识星球', path: '报告/知识星球/260919.pdf' },
    { id: 'ineligible', title: '发布日期已知但可得性未确认', publicationDate: '2026-09-10',
      historicalAsOfEligible: false, provider: '测试机构', path: '报告/private.pdf' }]
  render(<HistoryReplay data={{ ...fixture, reports }} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/来源库 \/ 研报库.*点击展开/))
  const library = screen.getByRole('region', { name: '来源与研报库' })
  const report = within(library).getByRole('heading', { name: '文件名归档报告' }).closest('article')!
  expect(report).toHaveTextContent('研究归档日期（文件名优先）：2026-09-19')
  expect(report).toHaveTextContent('平台发帖日：2026-09-20（备查，不等同于正文发布日期）')
  expect(report).toHaveTextContent('日期冲突：文件名日期与平台日期不一致，以文件名归档日期优先；不证明历史可得。')
  expect(report.textContent).not.toContain('正文发布日期：2026-09-19')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-25' } })
  expect(within(library).queryByText('文件名归档报告')).not.toBeInTheDocument()
  expect(within(library).queryByText('发布日期已知但可得性未确认')).not.toBeInTheDocument()
  expect(within(library).getByRole('heading', { name: '授权研报 · 0' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(within(library).getByText('研究归档日期（文件名优先）：2026-09-19')).toBeInTheDocument()
})

it('正式PDF提及候选文件名日期不触发文件名优先政策', () => {
  const reports = [{ id: 'printed-date', title: 'TEST ONLY 正式PDF日期', provider: 'TEST ONLY',
    publicationDate: '2026-09-12', filenameDate: '2026-09-28', path: '报告/TEST_ONLY.pdf',
    dateBasis: 'printed_publication_date; filename_date_candidate_unverified' }]
  render(<HistoryReplay data={{ ...fixture, reports }} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/来源库 \/ 研报库.*点击展开/))
  const library = screen.getByRole('region', { name: '来源与研报库' })
  expect(within(library).getByText('正文发布日期：2026-09-12')).toBeInTheDocument()
  expect(within(library).queryByText('正文发布日期：2026-09-28')).not.toBeInTheDocument()
})

it('星球文件名归档观点日期不写作平台日或已核正文日', () => {
  const item = { reportId: 'filename-view', expressedAt: '2026-09-19', dateBasis: 'filename_date_user_preferred; publication_date_unconfirmed',
    actor: '测试作者', claim: '文件名日期观点', scope: '美国', pages: [1], evidenceExcerpt: '测试短摘录', limitations: ['历史可得性未确认'] }
  render(<HistoryReplay data={{ ...fixture, researchEvidence: [item] }} onBack={() => {}} />)
  fireEvent.click(screen.getByText('星球观点明细 · 1（点击展开）'))
  const region = screen.getByRole('region', { name: '星球观点独立追溯' })
  expect(region).toHaveTextContent('观点归档日期（文件名优先）：2026-09-19')
  expect(region).toHaveTextContent('文件名归档日期不等同于已核正文发布日期或历史可得时间')
  expect(region.textContent).not.toContain('观点日期 / 平台日：2026-09-19')
})

it('实际公众号观点保留段号及条件数组，原文字正文不标成PDF页码', () => {
  render(<HistoryReplay onBack={() => {}} />)
  fireEvent.click(screen.getByText(/微信观点明细.*点击展开/))
  const region = screen.getByRole('region', { name: '微信观点独立追溯' })
  const data: HistoryReplayData = replayData
  expect(within(region).getAllByRole('article')).toHaveLength(data.wechatResearchEvidence?.length || 0)
  if (data.wechatCoverage) {
    const coverage = within(region).getByRole('region', { name: '微信公众号来源覆盖' })
    expect(data.wechatCoverage.totalOpinions).toBe(data.wechatResearchEvidence?.length)
    expect(data.wechatCoverage.actualAccounts.reduce((sum, account) => sum + account.articleCount, 0)).toBe(data.wechatCoverage.totalArticles)
    expect(coverage).toHaveTextContent(`已取得正文 ${data.wechatCoverage.totalArticles} 篇 · 提取观点 ${data.wechatCoverage.totalOpinions} 条`)
    for (const account of data.wechatCoverage.actualAccounts) expect(coverage).toHaveTextContent(`${account.accountActual} · ${account.articleCount} 篇`)
  }
  const items = data.wechatResearchEvidence || []
  expect(items.length).toBeGreaterThan(0)
  const cards = within(region).getAllByRole('article')
  items.forEach((item, index) => {
    expect(item.pages?.every(page => typeof page === 'string' && /^p\d+$/.test(page))).toBe(true)
    expect(cards[index]).toHaveTextContent(`证据段：${item.pages?.join('、')}`)
    expect(cards[index]).not.toHaveTextContent('证据页：p')
    expect(cards[index]).toHaveTextContent(item.claim)
    expect(cards[index]).toHaveTextContent(item.evidenceExcerpt || '')
    expect(cards[index]).toHaveTextContent('条件：')
    expect(cards[index]).toHaveTextContent('期限：')
  })
  const publicURLs = new Set(data.sources.map(source => source.url).filter(url => /^https?:\/\//.test(url)))
  expect(within(region).queryAllByRole('link').every(link => publicURLs.has(link.getAttribute('href') || ''))).toBe(true)
})

it('实际星球观点的归档日期标题采用文件名口径', () => {
  render(<HistoryReplay onBack={() => {}} />)
  fireEvent.click(screen.getByText(/星球观点明细.*点击展开/))
  const region = screen.getByRole('region', { name: '星球观点独立追溯' })
  const items = (replayData as HistoryReplayData).researchEvidence || []
  expect(items.length).toBeGreaterThan(0)
  const cards = within(region).getAllByRole('article')
  items.forEach((item, index) => {
    expect(item.dateBasis).toContain('filename_date_user_preferred')
    expect(cards[index]).toHaveTextContent(`观点归档日期（文件名优先）：${item.expressedAt}`)
    expect(cards[index]).not.toHaveTextContent(`观点日期 / 平台日：${item.expressedAt}`)
  })
})

it('当前完整资料视图与严格历史截面明确分开标示', () => {
  render(<HistoryReplay data={fixture} onBack={() => {}} />)
  expect(screen.getByRole('status')).toHaveTextContent('当前完整资料视图')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-09-16' } })
  expect(screen.getByRole('status')).toHaveTextContent('严格历史截面')
})

it.each(['2026-09-16', '2026-09-30'])('讲话日早于截止%s仍不得把首次发布时间未知的FINAL逐字稿放入历史截面', (cutoff) => {
  const data = { ...fixture, sources: [...fixture.sources, {
    id: 'speech-final', title: '记者会FINAL逐字稿', date: '2026-09-16', publisher: '测试官方',
    url: 'https://example.org/speech-final.pdf', kind: '官方讲话', status: '当前已归档', note: '',
    historicalAsOfEligible: false, dateBasis: '讲话发生日；FINAL版9月24日生成，首次发布时间未核实',
  }], events: fixture.events.map((event) => event.id === 'meeting' ? { ...event,
    reality: 'FINAL版本才有的问答现实', realitySourceIds: ['speech-final'],
  } : event) }
  render(<HistoryReplay data={data} onBack={() => {}} />)
  fireEvent.click(screen.getByText(/来源库 \/ 研报库.*点击展开/))
  expect(screen.getByRole('heading', { name: '记者会FINAL逐字稿' })).toBeInTheDocument()
  expect(screen.getAllByText('FINAL版本才有的问答现实')).toHaveLength(2)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: cutoff } })
  expect(screen.queryByRole('heading', { name: '记者会FINAL逐字稿' })).not.toBeInTheDocument()
  expect(screen.queryByText('FINAL版本才有的问答现实')).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: '记者会FINAL逐字稿 ↗' })).not.toBeInTheDocument()
  // The stricter dependency boundary unmounts the dependent event title too;
  // a withheld source no longer leaves a misleading placeholder event behind.
  expect(screen.queryByRole('heading', { name: '测试会议' })).not.toBeInTheDocument()
  if (cutoff === '2026-09-16') expect(screen.getByText('当前截止日期内暂无已核验事件。')).toBeInTheDocument()
  else expect(screen.getAllByText('缺少当时可得来源，暂不作结论').length).toBeGreaterThan(0)
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(screen.getByRole('heading', { name: '记者会FINAL逐字稿' })).toBeInTheDocument()
  expect(screen.getByText('日期依据：讲话发生日；FINAL版9月24日生成，首次发布时间未核实')).toBeInTheDocument()
  expect(screen.getAllByText('FINAL版本才有的问答现实')).toHaveLength(2)
})

it('没有可用事前来源时不得把后来观点呈现为当时预期', () => {
  render(<HistoryReplay data={fixture} onBack={() => {}} />)
  expect(screen.queryByText('后来写的预期')).not.toBeInTheDocument()
  expect(screen.getAllByText('缺少当时可得来源，暂不作结论').length).toBeGreaterThan(0)
})
