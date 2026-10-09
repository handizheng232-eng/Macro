import { render, cleanup, fireEvent, screen } from '@testing-library/react'
import { HistoryReplay } from './historyReplay'
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
    for (const topic of topics) {
      expect(Array.from(topic.querySelectorAll('dt')).map(node => node.textContent)).toEqual([
        '观点 / 事前预期', '现实', '机制', '分歧 / 预期差', '市场含义', '验证条件',
      ])
    }
    const library = screen.getByLabelText('来源库 / 研报库明细')
    expect(library).not.toHaveAttribute('open')
    fireEvent.click(library.querySelector(':scope > summary')!)
    expect(library).toHaveAttribute('open')
    cleanup()
  }
})
