import old from './data/policyRealityLegacy.fixture.json'
import { createHash } from 'node:crypto'
import { cleanup, render } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayAggressiveHikesQt.json'
import expected from './data/policyRealityExpected.fixture.json'
import frozenExpected from './data/aggressiveReviewExpected.fixture.json'
afterEach(cleanup)
it('binds the actual published candidate and unchanged prior paragraphs to both accepted contracts',()=>{
 const {container}=render(<HistoryReplay data={data} readingControls onBack={()=>{}} />)
 expect(data.marketAnalysis.sections[0].deepDive.realityTimeline).toEqual(expected.months)
 expect(data.localReview.publicReleaseAllowed).toBe(true)
 expect(data.reviewProjection.publicationAuthorized).toBe(true)
 expect(data.localReview.fullStageReady).toBe(false)
 expect(data.localReview.strictHistoricalEligible).toBe(false)
 expect(container.textContent).not.toContain('本次修订仅供本地审阅、未发布')
 expect(container.textContent).toContain('本篇已获阶段性公网发布授权')
 const replacedIds=new Set([...old.marketAnalysis.sections[0].deepDive.realityTimeline.map((p:{id:string})=>p.id),'aspect-topic-1-realityTimeline'])
 const nodes=[...data.reviewProjection.conclusion,...data.reviewProjection.readingNotes,...data.marketAnalysis.sections.flatMap(s=>[...s.periodSummary.reviewedParagraphs,...Object.values(s.deepDive).flat(),...Object.entries(s.aspectSummaries).map(([role,p])=>({id:`aspect-${s.id}-${role}`,...p}))])]
 for(const p of frozenExpected.filter(p=>!replacedIds.has(p.id))){
  const raw=nodes.find(n=>n.id===p.id)!
  expect(createHash('sha256').update(raw.text).digest('hex')).toBe(p.sha256)
  const el=container.querySelector(`[data-reviewed-text="${p.id}"]`)!
  const heading=container.querySelector(`[data-reviewed-heading="${p.id}"]`)
  expect((heading?heading.textContent+'｜':'')+el.textContent).toBe(raw.text.replace(/\*\*([^*]+)\*\*/g,'$1'))
  expect([...el.nextElementSibling!.querySelectorAll('[data-citation-alias]')].map(a=>a.getAttribute('data-citation-alias'))).toEqual(p.citationAliases)
 }
 const intro=data.marketAnalysis.sections[0].aspectSummaries.realityTimeline
 expect(container.querySelector('[data-reviewed-text="aspect-topic-1-realityTimeline"]')?.textContent).toBe(intro.text)
 expect(container.querySelectorAll('[data-reviewed-text]')).toHaveLength(frozenExpected.length-replacedIds.size+35+1)
})
