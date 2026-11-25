import { render, cleanup } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { HistoryReplay } from './historyReplay'
import candidate from './data/policyRealityLegacy.fixture.json'
import reference from './data/historyReplayRateLiftoffQtGuidance.json'
afterEach(cleanup)
Object.defineProperty(HTMLElement.prototype,'scrollIntoView',{configurable:true,value:vi.fn()})
it('uses the populated template paragraph and source-link anatomy, not alias buttons',()=>{
 const ref=render(<HistoryReplay data={reference} readingControls onBack={()=>{}} />)
 const expected=ref.container.querySelector('#replay-topic-0-summary .replay-entry-references')!
 expect(expected.querySelector('.replay-source-ref a')).not.toBeNull()
 const cl=expected.className;ref.unmount()
 const {container}=render(<HistoryReplay data={candidate} readingControls onBack={()=>{}} />)
 const summary=container.querySelector('#replay-topic-0-summary')!
 expect(summary.querySelector('.reviewed-paragraph')).toBeNull()
 expect(summary.querySelector('[data-summary-paragraph] > p')).not.toBeNull()
 expect(summary.querySelector('.replay-entry-references')?.className).toBe(cl)
 expect(summary.querySelectorAll('[data-summary-paragraph] > .replay-entry-references')).toHaveLength(candidate.marketAnalysis.sections[0].periodSummary.paragraphs.length)
 expect(summary.querySelector('.replay-source-ref > a[target="_blank"]')).not.toBeNull()
 expect(summary.querySelector('.replay-entry-references button')).toBeNull()
 expect(container.querySelectorAll('.replay-analysis-conclusion > h3[data-reviewed-heading]')).toHaveLength(6)
 expect(container.querySelector('.replay-analysis-conclusion > p')).not.toHaveAttribute('data-analysis-text')
 expect(container.querySelectorAll('[data-reviewed-text]')).toHaveLength(130)
 for(const label of container.querySelectorAll('.replay-library .replay-source > small')) expect(label.textContent).not.toMatch(/^\s*·/)
 for(const text of container.querySelectorAll('[data-reviewed-text]')) expect(text.textContent).not.toMatch(/\*\*|\[@/)
 for(const entry of container.querySelectorAll('[data-analysis-entry]')) expect(entry.querySelector('[data-analysis-text]')?.parentElement).toBe(entry)
 const links=container.querySelectorAll<HTMLAnchorElement>('[data-citation-alias]')
 for(const link of links){const source=candidate.sources.find(s=>s.citationAliases.includes(link.dataset.citationAlias!))!;expect(source).toBeDefined();expect(link.textContent).not.toContain(link.dataset.citationAlias!);expect(link.closest('.replay-source-ref')).not.toBeNull();expect(link.dataset.sourceId).toBe(source.id)}
 expect(container.querySelector('[aria-label="完整逐月总结镜像"]')?.closest('#reading-library')).not.toBeNull()
})
