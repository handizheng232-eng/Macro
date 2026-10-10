import { render, cleanup, fireEvent, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'
import first from './data/historyReplay.json'
import second from './data/historyReplayHawkishTransition.json'

const outline = (root: HTMLElement) => Array.from(root.children).map((node) => ({
  tag: node.tagName,
  label: node.getAttribute('aria-label') || '',
  className: node.className,
}))

it('两篇真实复盘的主章节、顺序与层级一致；补充证据不另增主章节', () => {
  const a = render(<HistoryReplay data={first} onBack={() => {}} />)
  const firstOutline = outline(a.container.querySelector('.history-replay')!)
  cleanup()
  const b = render(<HistoryReplay data={second} onBack={() => {}} />)
  const secondOutline = outline(b.container.querySelector('.history-replay')!)
  // The accessible document name and stage boundaries intentionally differ.
  expect(secondOutline).toEqual(firstOutline)
  const library = screen.getByLabelText('来源库 / 研报库明细')
  expect(library).toContainElement(screen.getByLabelText('逐条预期现实对照'))
  expect(library).toContainElement(screen.getByLabelText('本地研报观点明细'))
})

it('两篇均保留三渠道默认折叠及相同的五主题分析字段', () => {
  for (const data of [first, second]) {
    const view = render(<HistoryReplay data={data} onBack={() => {}} />)
    for (const name of ['星球', 'Wind', '微信']) {
      expect(screen.getByLabelText(`${name}观点明细`)).not.toHaveAttribute('open')
    }
    const topics = Array.from(view.container.querySelectorAll('.replay-analysis-topic'))
    expect(topics).toHaveLength(5)
    for (const [index, topic] of topics.entries()) {
      expect(Array.from(topic.querySelectorAll('dt')).map(node => node.textContent)).toEqual([
        '观点 / 事前预期', '现实', '机制', '分歧 / 预期差', '市场含义',
        ...((data as HistoryReplayData).marketAnalysis?.sections[index].deepDive?.examples?.length ? ['实例 / 原文与数据'] : []), '验证条件',
      ])
    }
    const library = screen.getByLabelText('来源库 / 研报库明细')
    expect(library).not.toHaveAttribute('open')
    fireEvent.click(library.querySelector(':scope > summary')!)
    expect(library).toHaveAttribute('open')
    cleanup()
  }
})

it.each([first, second])('$title：独立事件时间轴从DOM真正删除，事件核验配对与判断反证保留', (data) => {
  const rawEvents = JSON.stringify(data.events)
  const view = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(view.container.querySelector('.replay-timeline')).toBeNull()
  expect(view.container.querySelector('.replay-grid')).toBeNull()
  expect(screen.queryByRole('region', { name: '事件时间轴' })).not.toBeInTheDocument()
  expect(view.container.textContent).not.toContain('事件时间轴')
  expect(screen.getByRole('region', { name: '判断与反证' })).toBeInTheDocument()
  const pairs = screen.getByRole('region', { name: '市场路径对照' })
  for (const event of data.events.filter(event => event.date <= data.asOf)) expect(pairs).toHaveTextContent(event.title)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: data.startDate } })
  expect(view.container.querySelector('.replay-timeline')).toBeNull()
  expect(JSON.stringify(data.events)).toBe(rawEvents)
})

// TEST ONLY deepDive fixture. No real empirical data or research is fabricated.
const deepFixture = {
  title: 'TEST ONLY 深度分析', startDate: '2026-01-01', asOf: '2026-08-31', summary: [],
  events: [], hypotheses: [], acquisition: [],
  sources: [{ id: 'test-source', title: '测试官方原稿', publisher: '测试官方机构', date: '2026-06-01',
    url: 'https://example.org/test-only', kind: '测试', status: '测试', note: '' }],
  reports: [{ id: 'test-report', title: '测试署名报告', provider: '测试研究机构', path: 'TEST_ONLY.pdf',
    publicationDate: '2026-05-01', authors: ['测试作者甲'], researchOrigin: '测试研究机构' }],
  researchEvidence: [{ id: 'test-opinion', reportId: 'test-report', expressedAt: '2026-05-01',
    dateBasis: 'TEST ONLY', actor: '测试作者甲', claim: '测试有条件预测', scope: '测试',
    pages: [2], evidenceExcerpt: 'TEST ONLY 原句于9/16发布', conditions: ['测试：就业持续走弱'],
    forecastHorizon: { literalResearchWindow: '2026Q3' } }],
  marketAnalysis: { title: '综合市场分析', conclusion: '测试综合结论', limitations: [],
    sections: ['货币政策', '通胀', '增长与就业', '美债收益率曲线', '美元'].map((title, index) => ({
      id: `test-topic-${index}`, title, judgement: '测试判断', expectation: '旧字段事前预期',
      reality: '旧字段现实', mechanism: '旧字段机制', divergence: '旧字段分歧',
      implication: '旧字段市场含义', validation: '旧字段验证条件', sourceIds: ['test-source'], reportIds: ['test-report'],
      deepDive: index === 0 ? Object.fromEntries(['expectationTimeline', 'realityTimeline', 'mechanism', 'divergence', 'implicationTimeline', 'examples', 'validation'].map(key => [key, [{
        id: `test-entry-${key}`, date: key === 'expectationTimeline' ? '2026-05' : key === 'mechanism' ? null : '2026-06-01',
        title: `测试${key}节点`, text: `测试${key}首段。\n\n测试${key}次段。[test-opinion]`,
        sourceIds: ['test-source'], reportIds: ['test-report'], evidenceRefs: ['test-opinion'], dateNote: '测试：月级刊期不补造日',
      }]])) : undefined,
    })) },
}

it('五主题共用深度结构：七类分段、精度、署名、条件及实际引用，不露内部编号，旧字段逐块fallback', () => {
  const before = JSON.stringify(deepFixture)
  const view = render(<HistoryReplay data={deepFixture} onBack={() => {}} />)
  const analysis = screen.getByRole('region', { name: '综合市场分析' })
  const topics = analysis.querySelectorAll('.replay-analysis-topic')
  expect(topics).toHaveLength(5)
  const firstTopic = topics[0]
  expect(Array.from(firstTopic.querySelectorAll('dt')).map(node => node.textContent)).toEqual([
    '观点 / 事前预期', '现实', '机制', '分歧 / 预期差', '市场含义', '实例 / 原文与数据', '验证条件',
  ])
  for (const key of ['expectationTimeline', 'realityTimeline', 'mechanism', 'divergence', 'implicationTimeline', 'examples', 'validation']) {
    expect(firstTopic.querySelector('h5')?.closest('dl')).toHaveTextContent(`测试${key}节点`)
    expect(firstTopic).toHaveTextContent(`测试${key}首段。`)
    expect(firstTopic).toHaveTextContent(`测试${key}次段。`)
  }
  expect(firstTopic).toHaveTextContent('2026年5月')
  expect(firstTopic).toHaveTextContent('日期未详')
  expect(firstTopic.querySelector('.replay-date-unknown')).toHaveAttribute('title', '资料未注明具体日期，保留未知，不补造日期精度。')
  expect(firstTopic).not.toHaveTextContent('日期未注明（不补造）')
  expect(firstTopic).toHaveTextContent('测试：月级刊期不补造日')
  expect(firstTopic).toHaveTextContent('测试官方机构')
  expect(firstTopic).toHaveTextContent('作者：测试作者甲')
  expect(firstTopic).toHaveTextContent('条件：测试：就业持续走弱')
  expect(firstTopic).toHaveTextContent('期限：2026年第三季度')
  expect(firstTopic).toHaveTextContent('第2页')
  expect(firstTopic.textContent).not.toMatch(/test-entry-|test-opinion|test-report|test-source/)
  expect(topics[1]).toHaveTextContent('旧字段事前预期')
  expect(topics[1]).toHaveTextContent('旧字段验证条件')
  const nav = screen.getByRole('navigation', { name: '综合分析主题目录' })
  expect(nav.querySelectorAll('a')).toHaveLength(5)
  for (const link of nav.querySelectorAll('a')) expect(view.container.querySelector(link.getAttribute('href')!)).toBeTruthy()
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-06-30' } })
  expect(screen.queryByRole('region', { name: '综合市场分析' })).not.toBeInTheDocument()
  expect(screen.queryByRole('navigation', { name: '综合分析主题目录' })).not.toBeInTheDocument()
  expect(view.container.textContent).not.toContain('测试mechanism首段')
  expect(JSON.stringify(deepFixture)).toBe(before)
})

it('主题目录点击只滚动聚焦，保持hash路由和当前研究挂载', () => {
  render(<HistoryReplay data={deepFixture} onBack={() => {}} />)
  const before = window.location.hash
  const target = document.getElementById('replay-topic-4')!
  const scroll = vi.fn()
  Object.defineProperty(target, 'scrollIntoView', { value: scroll, configurable: true })
  fireEvent.click(screen.getByRole('navigation', { name: '综合分析主题目录' }).querySelector('a[href="#replay-topic-4"]')!)
  expect(scroll).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
  expect(target).toHaveFocus()
  expect(window.location.hash).toBe(before)
  expect(screen.getByRole('region', { name: '综合市场分析' })).toBeInTheDocument()
})

it('框架辅助图按实际单位分轴、月季观察期不补日，显式显示源与冻结/修订版本，null断线且严格历史卸载', () => {
  // TEST ONLY numeric observations. They are not real macro research data.
  const series = { id: 'test-only-monthly', title: 'TEST ONLY 月频序列', unit: '%', sourceUrl: 'https://example.org/test-series',
    status: '测试冻结修订版', limitations: ['测试：不代表首次发布值'], frequency: '月', sourceGeneratedAt: '2026-09-29',
    sourceMetadata: { provider: '测试提供商', institution: '测试统计机构', code: 'TEST_ONLY_CODE', rawUnit: '测试原单位', updateDate: '2026-09-20', inheritedTransformation: '测试：沿用冻结原图同比口径' },
    observations: [
      { date: '2026-04-01', observationPeriod: '2026-04', value: 1, releaseDate: null, historicalAsOfEligible: false, isPrehistory: true },
      { date: '2026-05-01', observationPeriod: '2026-05', value: null, releaseDate: null, historicalAsOfEligible: false, missingReason: 'TEST ONLY 缺口' },
      { date: '2026-06-01', observationPeriod: '2026-06', value: 2, releaseDate: '2026-09-10', historicalAsOfEligible: false },
    ] }
  const frameworkEvidence = [{ id: 'test-only-framework', moduleSlugs: ['us-inflation', 'us-housing', 'not-a-module'],
    title: 'TEST ONLY 框架通胀约束', explanation: '测试解释：不能从同期变化推断单一政策冲击。',
    sourceVintageNote: '测试冻结版本：非当时信息集，不替代官方首次发布稿。',
    datasetPins: [{ file: 'TEST_ONLY.json', sha256: 'TEST_ONLY_NOT_A_REAL_HASH', jsonPointer: '/test' }], retrospectiveOnly: true,
    researchWindow: { start: '2026-05-01', end: '2026-08-31' },
    series: [series, { ...series, id: 'test-only-quarterly', title: 'TEST ONLY 季频序列', frequency: '季', unit: '十亿美元',
      observations: [{ date: '2026-06-30', observationPeriod: '2026-Q2', value: 3, releaseDate: null, historicalAsOfEligible: false }] }],
  }]
  const data = { ...deepFixture, marketAnalysis: { ...deepFixture.marketAnalysis,
    sections: deepFixture.marketAnalysis.sections.map((section, index) => ({ ...section, frameworkEvidence: index === 0 ? frameworkEvidence : [] })) } }
  const raw = JSON.stringify(data)
  const view = render(<HistoryReplay data={data} onBack={() => {}} />)
  const region = screen.getByRole('region', { name: '货币政策 · 框架辅助证据' })
  expect(region).toHaveTextContent('测试解释：不能从同期变化推断单一政策冲击。')
  expect(region).toHaveTextContent('测试冻结版本：非当时信息集，不替代官方首次发布稿。')
  expect(region).toHaveTextContent('测试：不代表首次发布值')
  expect(region).toHaveTextContent('测试提供商')
  expect(region).toHaveTextContent('测试统计机构')
  expect(region).toHaveTextContent('测试原单位')
  expect(region).toHaveTextContent('2026年9月29日')
  expect(region).toHaveTextContent('2026年9月20日')
  expect(region).toHaveTextContent('测试：沿用冻结原图同比口径')
  expect(region).toHaveTextContent('2026年第二季度')
  expect(region).toHaveTextContent('2026年4月')
  expect(region).toHaveTextContent('前史')
  expect(region).not.toHaveTextContent('2026年4月1日')
  expect(region).not.toHaveTextContent('2026年6月30日')
  expect(region).toHaveTextContent('首次发布日期未确认')
  expect(region).toHaveTextContent('晚于复盘截止')
  const graphs = region.querySelectorAll('svg')
  expect(graphs).toHaveLength(2)
  for (const graph of graphs) expect(graph.querySelectorAll('path')).toHaveLength(1)
  const monthlyPath = graphs[0].querySelector('path')!.getAttribute('d')!
  expect(monthlyPath.match(/M/g)).toHaveLength(2)
  expect(monthlyPath).not.toContain('L')
  expect(graphs[0].querySelector('[data-research-window]')).toBeTruthy()
  expect(region.innerHTML).not.toMatch(/NaN|Infinity/)
  expect(region.querySelector('a[href="#framework/us-inflation"]')).toHaveTextContent('通胀')
  expect(region.querySelector('a[href="#framework/us-housing"]')).toHaveTextContent('住房')
  expect(region.querySelector('a[href="#framework/not-a-module"]')).toBeNull()
  expect(region.querySelector('a[href="https://example.org/test-series"]')).toBeTruthy()
  expect(region.textContent).not.toMatch(/test-only-framework|TEST_ONLY_NOT_A_REAL_HASH|\/test/)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2026-08-01' } })
  expect(screen.queryByRole('region', { name: '货币政策 · 框架辅助证据' })).not.toBeInTheDocument()
  expect(view.container.innerHTML).not.toContain('test-only-monthly')
  expect(JSON.stringify(data)).toBe(raw)
})
