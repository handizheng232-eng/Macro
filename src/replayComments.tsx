import { createElement, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import './replayComments.css'
import { CustomComments } from './customComments'
import { customCommentsOrigin } from './customCommentsClient'
import commentThemeCss from './replayCommentsTheme.css?raw'

// Official custom-theme URL: giscus loads this stylesheet inside its own iframe.
// No parent-frame CSS penetration, hosted-file deployment or auth access needed.
const COMMENT_THEME = `data:text/css;charset=utf-8,${encodeURIComponent(commentThemeCss)}`

export const COMMENT_ROUTE = 'history/inflation-qt-repricing/rate-liftoff-qt-guidance'
const DISCUSSION_URL = 'https://github.com/handizheng232-eng/Macro/discussions/1'
// Repository owner confirmed installation; official configuration verified before enabling.
const APP_READY = true

type Connection = 'loading' | 'ready' | 'slow' | 'error'
function OnlineDiscussion() {
  const host = useRef<HTMLDivElement>(null)
  const [connection, setConnection] = useState<Connection>('loading')
  const [loaded, setLoaded] = useState(false)
  useEffect(() => {
    let cancelled = false
    import('giscus').then(() => { if (!cancelled) setLoaded(true) }).catch(() => { if (!cancelled) setConnection('error') })
    return () => { cancelled = true }
  }, [])
  // The official component handles OAuth/session data. Do not read it here.
  // It removes the callback hash; preserve this hash router's exact article route.
  useLayoutEffect(() => {
    if (loaded && !window.location.hash) window.history.replaceState(window.history.state, '', `${window.location.pathname}${window.location.search}#${COMMENT_ROUTE}`)
  }, [loaded])
  useEffect(() => {
    const timer = window.setTimeout(() => setConnection(current => current === 'loading' ? 'slow' : current), 15000)
    const receive = (event: MessageEvent) => {
      const iframe = host.current?.querySelector('giscus-widget')?.shadowRoot?.querySelector('iframe')
      if (event.origin !== 'https://giscus.app' || !iframe?.contentWindow || event.source !== iframe.contentWindow) return
      const payload = event.data?.giscus
      if (!payload || typeof payload !== 'object') return
      if (typeof payload.error === 'string') { setConnection('error'); return }
      if (payload.discussion?.url === DISCUSSION_URL && (payload.discussion.number === undefined || payload.discussion.number === 1)) {
        window.clearTimeout(timer)
        setConnection('ready')
      }
    }
    window.addEventListener('message', receive)
    return () => { window.clearTimeout(timer); window.removeEventListener('message', receive) }
  }, [])
  return <div ref={host} className="replay-comments-widget">
    <p role="status" aria-live="polite">{connection === 'ready' ? '在线讨论已连接' : connection === 'error' ? '评论服务暂不可用，请重试或直接打开 GitHub 讨论。' : connection === 'slow' ? '尚未收到讨论确认；可能是网络或内容拦截，请重试或直接打开 GitHub 讨论。' : '正在连接 GitHub 公开讨论…'}</p>
    {loaded && createElement('giscus-widget', { id: COMMENT_ROUTE, repo: 'handizheng232-eng/Macro', repoid: 'R_kgDOUe7w2Q', category: 'Announcements', categoryid: 'DIC_kwDOUe7w2c4DLS_J', mapping: 'number', term: '1', strict: '1', reactionsenabled: '0', emitmetadata: '1', inputposition: 'top', theme: COMMENT_THEME, lang: 'zh-CN', loading: 'eager' })}
  </div>
}

function CommentsPanel({ appReady }: { appReady: boolean }) {
  const customOrigin = customCommentsOrigin(import.meta.env)
  const [expanded, setExpanded] = useState(() => window.matchMedia?.('(min-width: 1350px)').matches ?? false)
  const [attempt, setAttempt] = useState(0)
  return <aside className="replay-comments-panel" aria-label="公开留言与讨论">
    <div className="replay-comments-heading"><h2>公开留言与讨论</h2><span>访客讨论 · 非研究正文</span></div>
    <a href={DISCUSSION_URL} target="_blank" rel="noreferrer">在 GitHub 打开本篇讨论 ↗</a>
    <p><a href={DISCUSSION_URL} target="_blank" rel="noreferrer">修改／删除我的评论（前往 GitHub）↗</a></p>
    {!customOrigin && <p>使用发表评论的 GitHub 账号登录，在自己的评论右上角「…」菜单选择 Edit（编辑）或 Delete（删除）。权限由 GitHub 校验；删除前请确认，不能在本页撤销。</p>}
    {!customOrigin && <p>编辑或删除在 GitHub 完成后，返回这里点击「刷新评论」查看结果。当前嵌入框不提供直接编辑或删除。</p>}
    {!appReady && <p role="status">等待 giscus App 授权；可先在 GitHub 本篇讨论中留言。</p>}
    <div className="replay-comments-actions"><button type="button" aria-expanded={expanded} aria-controls="replay-online-comments" onClick={() => { if (customOrigin && expanded && !window.confirm('收起会清除未提交草稿和当前登录状态，继续？')) return; setExpanded(value => !value) }}>{expanded ? '收起在线评论' : '展开在线评论'}</button>{expanded && appReady && !customOrigin && <button type="button" onClick={() => setAttempt(value => value + 1)}>重新连接</button>}</div>
    <div id="replay-online-comments" hidden={!expanded}>
      {expanded && appReady && !customOrigin && <button type="button" onClick={() => setAttempt(value => value + 1)}>刷新评论</button>}
      {!customOrigin && <p>GitHub 登录后发表，所有访客可读。请勿发布私密资料或未获授权的研报全文。</p>}
      {!customOrigin && <p>点击评论框的提交按钮后，留言才保存到 GitHub Discussions；未提交的文字不代表已在线保存。</p>}
      <p>访客讨论独立于正式研究，不属于历史时点信息集；严格历史截面不展示。</p>
      {expanded && (customOrigin ? <CustomComments origin={customOrigin} /> : appReady && <OnlineDiscussion key={attempt} />)}
    </div>
  </aside>
}

export function ReplayCommentsLayout({ route, historical, children, appReady = APP_READY }: { route?: string; historical: boolean; children: ReactNode; appReady?: boolean }) {
  if (route !== COMMENT_ROUTE || historical) return children
  return <div className="replay-comments-layout">{children}<CommentsPanel appReady={appReady} /></div>
}
