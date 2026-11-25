import { cleanup, render } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'
import raw from './data/historyReplayAggressiveHikesQt.json'
import expected from './data/policyRealityExpected.fixture.json'
afterEach(cleanup)
const fixture = structuredClone(raw) as HistoryReplayData
fixture.marketAnalysis!.sections[0].deepDive!.realityTimeline = expected.months
fixture.sources = [...raw.sources.filter(s => !expected.sources.some(n => n.id === s.id)), ...expected.sources]
it('renders the admitted six months as 35 exact paragraphs with individual citations', () => {
 const {container}=render(<HistoryReplay data={fixture} readingControls onBack={()=>{}} />)
 expect(container.querySelectorAll('[data-reviewed-text^="PR01-2022-"]')).toHaveLength(35)
 for(const m of expected.months){
  const node=container.querySelector(`[data-analysis-entry="${m.id}"]`)!
  expect(node.querySelector('time')?.getAttribute('datetime')).toBe(m.month)
  expect(node.textContent).not.toContain('日期未详')
  expect(m.reviewedParagraphs.map(p=>p.text).join('\n\n')).toBe(m.text)
  for(const p of m.reviewedParagraphs){
   const el=node.querySelector(`[data-reviewed-text="${p.id}"]`)!
   expect(el.textContent).toBe(p.text)
   expect([...el.nextElementSibling!.querySelectorAll('[data-citation-alias]')].map(x=>x.getAttribute('data-citation-alias'))).toEqual(p.sourceIds)
   for(const a of el.nextElementSibling!.querySelectorAll<HTMLAnchorElement>('[data-source-id]')) expect(container.querySelector(a.getAttribute('href')!)).not.toBeNull()
  }
 }
 expect(container.textContent).not.toMatch(/PR01-2022-/)
})
it('displays new official source types with Chinese names without changing their DTOs',()=>{
 const {container}=render(<HistoryReplay data={fixture} readingControls onBack={()=>{}} />)
 const titles=[...container.querySelectorAll('[data-summary-source]')].map(a=>a.getAttribute('title')||'')
 expect(titles.some(t=>t.includes('议息会议记者会'))).toBe(true)
 expect(titles.some(t=>t.includes('主席讲话'))).toBe(true)
 expect(titles.some(t=>/press-conference|speech \/ /.test(t))).toBe(false)
})
