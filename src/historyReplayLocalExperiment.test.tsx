import { fireEvent, render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'
import raw from './data/historyReplayRenewedEasingQtEnd.json'

type Increment = { id: string; title: string; publicationDate: string; claims: {id: string; renderedView: string}[] }
const data = raw as unknown as HistoryReplayData & { windIncrement: Increment[] }
it('local progress: lossless 17, visible partial status, old channels, historical unmount and reset', () => {
  const {container} = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(screen.getByLabelText('有限研究发布说明')).toHaveTextContent('12月14篇按用户数量例外接受')
  expect(screen.getByLabelText('有限研究发布说明')).toHaveTextContent('合计呈现7段')
  expect(container.textContent).not.toContain('逐月覆盖通过·有限样本，非全量')
  for (const label of ['星球观点明细','Wind观点明细','微信观点明细']) expect(screen.getByLabelText(label)).toBeInTheDocument()
  const library=screen.getByLabelText('来源库 / 研报库明细')
  expect(library).not.toHaveAttribute('open')
  const section=screen.getByLabelText('本轮新增研究（已审核限定内容）')
  expect(library).toContainElement(section)
  expect(section).not.toHaveAttribute('open')
  expect(section.querySelectorAll('[data-wind-increment]')).toHaveLength(17)
  expect(screen.getByLabelText('新增研究目录').querySelectorAll('button')).toHaveLength(17)
  for(const node of data.windIncrement) {
    const article=container.querySelector(`[data-wind-increment="${node.id}"]`)!
    expect(article).toHaveTextContent(node.title)
    for(const claim of node.claims) expect(article.querySelector(`[data-increment-claim="${claim.id}"]`)?.textContent).toBe(claim.renderedView)
  }
  fireEvent.change(screen.getByLabelText('按日期截止查看'),{target:{value:'2025-12-30'}})
  expect(screen.queryByLabelText('本轮新增研究（已审核限定内容）')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('新增研究目录')).not.toBeInTheDocument()
  for(const node of data.windIncrement) expect(container.textContent).not.toContain(node.title)
  fireEvent.click(screen.getByRole('button',{name:'恢复资料截止日'}))
  expect(screen.getByLabelText('本轮新增研究（已审核限定内容）')).not.toHaveAttribute('open')
})
