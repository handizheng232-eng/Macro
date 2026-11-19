import { createHash } from 'node:crypto'
import { fireEvent, render, screen, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'
Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
it('loads the new detail route and returns to the verified 09.2 parent', () => {
 window.history.replaceState(null, '', '#history/inflation-qt-repricing/aggressive-hikes-qt')
 const { container }=render(<App />)
 expect(container.querySelector('[data-reviewed-text="RR02-P001"]')).not.toBeNull()
 fireEvent.click(screen.getByRole('button', {name:'返回父阶段复盘'}))
 expect(window.location.hash).toBe('#history/inflation-qt-repricing')
 fireEvent.click(screen.getByRole('button', {name:/进入激进加息与QT并行阶段性研究版/}))
 expect(window.location.hash).toBe('#history/inflation-qt-repricing/aggressive-hikes-qt')
})
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayAggressiveHikesQt.json'
import expected from './data/aggressiveReviewExpected.fixture.json'
afterEach(cleanup)
it('projects all 130 accepted paragraphs with every citation and honest local status', () => {
 const { container }=render(<HistoryReplay data={data} readingControls commentRoute="history/inflation-qt-repricing/aggressive-hikes-qt" onBack={()=>{}} />)
 const texts=container.querySelectorAll<HTMLElement>('[data-reviewed-text]')
 expect(texts).toHaveLength(130)
 const original=[...data.reviewProjection.conclusion,...data.reviewProjection.readingNotes,...data.marketAnalysis.sections.flatMap(s=>[...s.periodSummary.reviewedParagraphs,...Object.values(s.deepDive).flat(),...Object.entries(s.aspectSummaries).map(([role,p])=>({id:`aspect-${s.id}-${role}`,...p}))])]
 for(const p of expected){ const raw=original.find(e=>e.id===p.id)!; const el=container.querySelector<HTMLElement>(`[data-reviewed-text="${p.id}"]`)!; expect(createHash('sha256').update(raw.text).digest('hex')).toBe(p.sha256); const heading=container.querySelector(`[data-reviewed-heading="${p.id}"]`); expect((heading ? heading.textContent+'｜' : '')+el.textContent).toBe(raw.text.replace(/\*\*([^*]+)\*\*/g,'$1')); expect(Array.from(el.nextElementSibling!.querySelectorAll('[data-citation-alias]')).map(a=>a.getAttribute('data-citation-alias'))).toEqual(p.citationAliases) }
 expect(container.textContent).not.toMatch(/81份PDF|全部54件|本版已获阶段性公网发布授权|2021年12月/)
 expect(screen.getByText('本篇已发布，评论尚未独立绑定')).toBeInTheDocument()
 expect(screen.getByRole('button',{name:'发送评论'})).toBeDisabled()
 expect(container.querySelector('giscus-widget,iframe')).toBeNull()
 expect(container.querySelectorAll('.replay-path-chart')).toHaveLength(4)
 expect(container.querySelectorAll('path[data-series-id]')).toHaveLength(8)
 expect(container.querySelectorAll('.replay-path-metadata > article')).toHaveLength(13)
 expect(container.querySelector('#reading-analysis')).not.toHaveAttribute('open')
 expect(container.querySelector('#reading-library')).not.toHaveAttribute('open')
 fireEvent.click(container.querySelector('[data-reading-target="replay-topic-1-summary"]')!)
 expect(container.querySelector('#reading-analysis')).toHaveAttribute('open')
 expect(container.querySelector('#replay-topic-1-summary')).toHaveAttribute('open')
 expect(container.querySelector('#replay-topic-body-topic-2')).not.toHaveAttribute('hidden')
 fireEvent.change(screen.getByLabelText('按日期截止查看'),{target:{value:'2022-09-01'}})
 expect(container.querySelector('[data-reviewed-text],.replay-comments-panel,path[data-series-id]')).toBeNull()
 expect(container.querySelectorAll('.replay-source')).toHaveLength(0)
})
it('renders accepted monthly reserves without fabricating unknown star counts', () => {
 const {container}=render(<HistoryReplay data={data} readingControls onBack={()=>{}} />)
 const table=screen.getByRole('table',{name:'已父准逐月渠道数量',hidden:true})
 expect(table.querySelectorAll('tbody tr')).toHaveLength(6)
 expect(Array.from(table.querySelectorAll('[data-wind-accepted]')).map(e=>e.textContent)).toEqual(['11','12','10','12','11','13'])
 expect(Array.from(table.querySelectorAll('[data-wechat-accepted]')).map(e=>e.textContent)).toEqual(['15','15','15','24','15','17'])
 expect(table.querySelectorAll('[data-star-state="unconfirmed"]')).toHaveLength(6)
 expect(table.textContent).not.toContain('无资料')
 expect(container.textContent).toContain('用户数量例外已接受')
 expect(container.textContent).toContain('本篇已获阶段性公网发布授权')
 expect(data.localReview.fullStageReady).toBe(false)
 expect(data.localReview.strictHistoricalEligible).toBe(false)
 expect(data.reviewProjection.fullStageReady).toBe(false)
 expect(data.reviewProjection.publicationAuthorized).toBe(true)
 expect(container.textContent).not.toMatch(/本地审阅、未发布|未获公网发布许可/)
 fireEvent.change(screen.getByLabelText('按日期截止查看'),{target:{value:'2022-09-01'}})
 expect(container.querySelector('[aria-label="已父准逐月渠道数量"]')).toBeNull()
})
