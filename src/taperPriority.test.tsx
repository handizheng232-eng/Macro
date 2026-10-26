import fixture from './data/taperPriorityPublic.fixture.json'
import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import data from './data/historyReplayTaper.json'
import { HistoryReplay } from './historyReplay'
const nodes: {nodeId: string; sectionId: string; role: string; node: {text: string}}[] = fixture.nodes
const plan: {summaryGroups: {sectionId: string; baselineText: string; month: string; contributions: {addition: string}[]}[]} = fixture.plan
afterEach(() => { cleanup(); vi.restoreAllMocks() })
it('projects all 33 parent-admitted body objects exactly once and both complete summary contributions', () => {
  const sections = data.marketAnalysis.sections
  for (const n of nodes) {
    const section = sections.find(s => s.id === n.sectionId)!
    const found = Object.values(section.deepDive).flat().filter(x => x.id === n.nodeId)
    expect(found, n.nodeId).toEqual([n.node])
  }
  expect(nodes).toHaveLength(33)
  for (const g of plan.summaryGroups) {
    const summary = sections.find(s => s.id === g.sectionId)!.periodSummary
    const text = [g.baselineText, ...g.contributions.map(c => c.addition)].join('\n\n')
    expect(summary.paragraphs.filter(p => p === text)).toHaveLength(1)
    expect(summary.monthlyProgress.find(m => m.month === g.month)?.text).toBe(text)
  }
})
it('new coverage citations jump to every admitted node and return to the actual initiating control', () => {
  HTMLElement.prototype.scrollIntoView = vi.fn()
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation(callback => { callback(0); return 1 })
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  for (const n of nodes) {
    const citation = container.querySelector(`[data-priority-target="${n.nodeId}"]`)
    expect(citation, n.nodeId).not.toBeNull()
    for (let parent = citation!.parentElement; parent; parent = parent.parentElement) {
      if (parent instanceof HTMLDetailsElement && !parent.open) fireEvent.click(parent.querySelector(':scope > summary')!)
    }
    fireEvent.click(citation!)
    expect(container.querySelector(`[data-analysis-entry="${n.nodeId}"]`)).toHaveFocus()
    fireEvent.click([...container.querySelectorAll('.replay-outline-actions button')].find(n => n.textContent === '返回刚才位置')!)
    expect(citation).toHaveFocus()
  }
})
it('shows real original/repost/account coverage without upgrading formal quota or historical eligibility', () => {
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  const coverage = container.querySelector('[aria-label="重点账号限定接入覆盖"]')
  expect(coverage).not.toBeNull()
  expect(coverage?.textContent).toContain('原发取得63篇')
  expect(coverage?.textContent).toContain('原发限定采用60篇')
  expect(coverage?.textContent).toContain('转载辅助2篇')
  for (const name of ['中信证券', '中金公司', '西部证券', '海通证券', '广发证券', '国金证券', '奇霖宏观', '泽平宏观', '经济学家圈', '张伟经济观察']) expect(coverage?.textContent).toContain(name)
  expect(coverage?.textContent).toContain('正式配额未验收')
  expect(data.localReview.fullStageReady).toBe(false)
})
it('renders complete new body and monthly prose then really unmounts all new information at strict cutoffs', () => {
  HTMLElement.prototype.scrollIntoView = vi.fn()
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} readingControls />)
  for (const n of nodes) expect(container.querySelector(`[data-analysis-entry="${n.nodeId}"]`)?.textContent).toContain(n.node.text)
  for (const g of plan.summaryGroups) for (const c of g.contributions) expect(container.textContent).toContain(c.addition)
  for (const cutoff of ['2021-12-15', '2022-02-01', '2022-03-14']) {
    fireEvent.change(container.querySelector('#replay-cutoff')!, { target: { value: cutoff } })
    for (const n of nodes) expect(container.querySelector(`[data-analysis-entry="${n.nodeId}"]`)).toBeNull()
    expect(container.querySelector('[aria-label="重点账号限定接入覆盖"]')).toBeNull()
    for (const g of plan.summaryGroups) for (const c of g.contributions) expect(container.textContent).not.toContain(c.addition)
  }
})
