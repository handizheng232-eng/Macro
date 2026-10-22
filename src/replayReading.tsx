import { useContext, type ReactNode } from 'react'
import { ReadingLabels } from './replayHierarchy'
export function ReadingLabel({ id, children }: { id: string; children: ReactNode }) {
  const item = useContext(ReadingLabels).find(item => item.id === id)
  if (!item) return children
  return <>{item.number && <span className="replay-heading-number" data-reading-number>{item.number} </span>}<span className="replay-heading-text">{item.title}</span></>
}

export function ReadingColumn({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return <details className="replay-reading-column" data-reading-column data-column-label={title} id={id} onToggle={event => {
    const detail = event.currentTarget
    const summary = detail.querySelector<HTMLElement>(':scope > summary')!
    summary.setAttribute('aria-expanded', String(detail.open))
    if (!detail.open && detail.contains(document.activeElement)) summary.focus({ preventScroll: true })
  }}><summary aria-expanded="false" aria-controls={`${id}-body`}><h4><ReadingLabel id={id}>{title}</ReadingLabel></h4><small>展开 / 收起栏目</small></summary><div id={`${id}-body`}>
    {children}
    <button type="button" className="replay-column-return" onClick={event => {
      const detail = event.currentTarget.closest('details')!
      detail.open = false
      detail.querySelector<HTMLElement>(':scope > summary')?.focus({ preventScroll: true })
      detail.scrollIntoView({ behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
    }}>收起栏目并返回标题</button>
  </div></details>
}

export function ReadingBlock({ enabled, id, title, intro, children }: { enabled: boolean; id: string; title: string; intro: string; children: ReactNode }) {
  if (!enabled) return children
  return <details className="replay-reading-block" data-reading-block id={id} onToggle={event => {
    event.currentTarget.querySelector('summary')?.setAttribute('aria-expanded', String(event.currentTarget.open))
  }}><summary aria-expanded="false" aria-controls={`${id}-body`}><h2><ReadingLabel id={id}>{title}</ReadingLabel></h2><span>{intro}</span><small>展开 / 收起大板块</small></summary><div id={`${id}-body`}>{children}</div></details>
}
