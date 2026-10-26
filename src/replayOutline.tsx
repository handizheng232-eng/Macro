import { useEffect, useRef, useState, type ReactNode } from 'react'

import type { ReadingItem } from './replayHierarchy'
type Position = { id: string; offset: number; y: number }
const visible = (element: HTMLElement) => {
  if (element.closest('[hidden]')) return false
  for (let parent = element.parentElement; parent; parent = parent.parentElement) {
    if (parent instanceof HTMLDetailsElement && !parent.open) return false
  }
  return true
}
export function ReplayOutline({ items, navigate }: { items: ReadingItem[]; navigate: (id: string, scroll?: boolean) => void }) {
  const [open, setOpen] = useState(() => !window.matchMedia?.('(max-width: 1199px)').matches)
  const [active, setActive] = useState('replay-page-top')
  const [history, setHistory] = useState<Position[]>([])
  const frame = useRef(0)
  const restoreFrame = useRef(0)
  useEffect(() => () => cancelAnimationFrame(restoreFrame.current), [])
  useEffect(() => {
    const update = () => {
      cancelAnimationFrame(frame.current)
      frame.current = requestAnimationFrame(() => {
        let current = items[0]?.id || ''
        for (const item of items) {
          if ((item.depth || 0) > 2) continue
          const element = document.getElementById(item.id)
          if (element && visible(element) && element.getBoundingClientRect().top <= 150) current = item.id
        }
        setActive(previous => previous === current ? previous : current)
      })
    }
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    document.addEventListener('toggle', update, true)
    update()
    return () => {
      cancelAnimationFrame(frame.current)
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
      document.removeEventListener('toggle', update, true)
    }
  }, [items])
  const closeOnNarrow = () => { if (window.matchMedia?.('(max-width: 1199px)').matches) setOpen(false) }
  const jump = (id: string) => {
    cancelAnimationFrame(restoreFrame.current)
    const anchors = Array.from(document.querySelectorAll<HTMLElement>('.replay-reading-controls [id]')).filter(e => !e.closest('.replay-outline') && visible(e) && e.getBoundingClientRect().top <= 150)
    const origin = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const anchor = origin?.id && origin.matches('[data-reading-origin]') && visible(origin)
      ? origin : anchors.at(-1) || document.getElementById('replay-page-top')!
    setHistory(previous => [...previous.slice(-19), { id: anchor.id, offset: anchor.getBoundingClientRect().top, y: window.scrollY }])
    closeOnNarrow()
    navigate(id)
    setActive(id)
  }
  const back = () => {
    const position = history.at(-1)
    if (!position) return
    setHistory(previous => previous.slice(0, -1))
    closeOnNarrow()
    // Cancel any in-flight compositor scroll, then measure on the next frame.
    // Reading geometry in the same task can retain the previous animation offset.
    window.scrollTo({ top: window.scrollY, behavior: 'instant' })
    cancelAnimationFrame(restoreFrame.current)
    restoreFrame.current = requestAnimationFrame(() => {
      const target = document.getElementById(position.id)
      if (target) {
        navigate(position.id, false)
        window.scrollTo({ top: window.scrollY + target.getBoundingClientRect().top - position.offset, behavior: 'instant' })
      } else window.scrollTo({ top: position.y, behavior: 'instant' })
    })
  }
  type Branch = ReadingItem & { children: Branch[] }
  const roots: Branch[] = []
  const ancestors: Branch[] = []
  for (const item of items) {
    if ((item.depth || 0) > 2) continue
    const node = { ...item, children: [] } as Branch
    const depth = item.depth || 0
    if (depth && ancestors[depth - 1]) ancestors[depth - 1].children.push(node)
    else roots.push(node)
    ancestors[depth] = node
    ancestors.length = depth + 1
  }
  const renderBranches = (branches: Branch[]): ReactNode => <ol>{branches.map(item => <li key={item.id} data-depth={item.depth || 0}><button type="button" data-reading-target={item.id} aria-current={active === item.id ? 'location' : undefined} onClick={() => jump(item.id)}>{item.number && <span className="replay-heading-number" data-reading-number>{item.number} </span>}<span className="replay-heading-text">{item.title}</span></button>{item.children.length > 0 && renderBranches(item.children)}</li>)}</ol>
  return <aside className="replay-outline" aria-label="本篇阅读导航">
    <div className="replay-outline-actions"><button type="button" aria-expanded={open} aria-controls="replay-outline-list" onClick={() => setOpen(value => !value)}>{open ? '收起本篇目录' : '展开本篇目录'}</button><button type="button" disabled={!history.length} onClick={back}>返回刚才位置</button></div>
    <nav id="replay-outline-list" hidden={!open} aria-label="本篇目录"><strong>本篇目录</strong>{renderBranches(roots)}</nav>
  </aside>
}
