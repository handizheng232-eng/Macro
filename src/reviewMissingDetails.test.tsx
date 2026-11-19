import { render, cleanup, fireEvent } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { HistoryReplay } from './historyReplay'
import candidate from './data/historyReplayAggressiveHikesQt.json'
import reference from './data/historyReplayRateLiftoffQtGuidance.json'
afterEach(cleanup)
it('does not turn omitted review detail or unknown holdings into zero; retains cutoff isolation', () => {
 const {container,getByLabelText}=render(<HistoryReplay data={candidate} readingControls onBack={()=>{}} />)
 for(const channel of ['星球','Wind','微信']) {
  const panel=getByLabelText(`${channel}观点明细`)
  expect(panel.querySelector('summary')).toHaveTextContent(channel==='星球'?'历史可得待确认':'未单列，见综合分析及来源库')
  expect(panel.textContent).not.toMatch(/·\s*0|暂无已核验/)
 }
 expect(container.querySelector('.replay-toolbar [role="status"]')).toHaveTextContent('本稿未提供逐日事件索引')
 expect(getByLabelText('来源库 / 研报库明细').querySelector('summary')).toHaveTextContent('引用书目记录 109')
 expect(getByLabelText('来源库 / 研报库明细').querySelector('summary')).not.toHaveTextContent('授权研报 0')
 expect(container.querySelector('.replay-library')).not.toHaveTextContent('授权研报 · 0')
 fireEvent.change(getByLabelText('按日期截止查看'),{target:{value:'2022-06-30'}})
 expect(container.querySelector('[aria-label="综合市场分析"]')).toBeNull()
 expect(container.querySelector('[aria-label="Wind观点明细"]')).toBeNull()
 expect(container.querySelector('.replay-toolbar [role="status"]')).toHaveTextContent('严格历史截面')
})
it('keeps sibling rendered output identical when the local coverage branch is absent', () => {
 const first=render(<HistoryReplay data={reference} readingControls onBack={()=>{}} />)
 const html=first.container.innerHTML; first.unmount()
 const second=render(<HistoryReplay data={{...reference,localReview:{...reference.localReview,verifiedCoverage:undefined}}} readingControls onBack={()=>{}} />)
 expect(second.container.innerHTML).toBe(html)
 expect(second.container.querySelector('.replay-toolbar [role="status"]')).toHaveTextContent(/\d+ 条事件/)
 expect(second.container.querySelector('[aria-label="来源库 / 研报库明细"] > summary')).toHaveTextContent('授权研报')
})
