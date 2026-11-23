import {useCallback, useEffect, useRef, useState} from 'react'
import {CommentsAuthError, createCommentsApi, type CommentsApi, type CommentPage, type CommentRow, type CommentUser} from './customCommentsClient'
import './customComments.css'
const merge = (old: CommentRow[], next: CommentRow[]) => [...new Map([...old, ...next].map(row => [row.id, row])).values()]
export type CommentsDraft = {body?: string; editing?: CommentRow | null; editBody?: string; replyTo?: CommentRow | null}
export function CustomComments({origin, api: supplied, draft}: {origin?: string; api?: CommentsApi; draft?: CommentsDraft}) {
  const [api] = useState(() => supplied ?? createCommentsApi(origin!))
  const [user, setUser] = useState<CommentUser | null>(null)
  const [page, setPage] = useState<CommentPage | null>(null)
  const [replies, setReplies] = useState<Record<string, CommentPage>>({})
  const [body, setBody] = useState(draft?.body ?? '')
  const [editing, setEditing] = useState<CommentRow | null>(draft?.editing ?? null)
  const [editBody, setEditBody] = useState(draft?.editBody ?? '')
  const [replyTo, setReplyTo] = useState<CommentRow | null>(draft?.replyTo ?? null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => { if (draft) Object.assign(draft, {body, editing, editBody, replyTo}) }, [draft, body, editing, editBody, replyTo])
  const lock = useRef(false)
  const live = useRef(true)
  const reload = useCallback(async (preserveReplyDraft = false) => { const value = await api.request('/comments') as CommentPage; if (live.current) {setPage(value); setReplies(current => preserveReplyDraft ? current : {})} }, [api])
  useEffect(() => {live.current = true; void reload().catch(e => {if (live.current) setError(e.message)}); return () => {live.current = false; api.dispose?.()}}, [api, reload])
  useEffect(() => { const protect = (event: BeforeUnloadEvent) => {if (body || editing) {event.preventDefault(); event.returnValue = ''}}; window.addEventListener('beforeunload', protect); return () => window.removeEventListener('beforeunload', protect) }, [body, editing])
  async function run(action: () => Promise<void>) {if (lock.current) return; lock.current = true; setBusy(true); setError(''); setNotice(''); try {await action()} catch (e) {if (live.current) {if (e instanceof CommentsAuthError) setUser(null); setError(e instanceof Error ? e.message : '操作失败，草稿保留')}} finally {lock.current = false; if (live.current) setBusy(false)}}
  async function loadReplies(row: CommentRow, more = false) {const old = replies[row.id]; const value = await api.request(`/comments/${encodeURIComponent(row.id)}/replies${more && old?.pageInfo.endCursor ? '?after=' + encodeURIComponent(old.pageInfo.endCursor) : ''}`) as CommentPage; setReplies(current => ({...current, [row.id]: {...value, nodes: more && old ? merge(old.nodes, value.nodes) : value.nodes}}))}
  async function saveEdit() {if (!editing) return; const value = await api.request(`/comments/${encodeURIComponent(editing.id)}`, 'PATCH', {body: editBody, updatedAt: editing.updatedAt}) as {comment: CommentRow}; setPage(old => old && {...old, nodes: old.nodes.map(row => row.id === value.comment.id ? value.comment : row)}); setReplies(old => Object.fromEntries(Object.entries(old).map(([id, p]) => [id, {...p, nodes: p.nodes.map(row => row.id === value.comment.id ? value.comment : row)}]))); setEditing(null); setEditBody(''); setNotice('修改已保存并由服务器读回确认')}
  function item(row: CommentRow) {return <article className="custom-comment" key={row.id}>
    <header><strong>{row.author?.login ?? '已注销用户'}</strong><span>{row.updatedAt}</span></header>
    <p className="custom-comment-body">{row.body}</p>
    {user && <div className="custom-comment-actions">{row.canEdit && <button disabled={busy} onClick={() => {if (editing && !window.confirm('放弃当前编辑草稿？')) return; setEditing(row); setEditBody(row.body)}}>编辑</button>}{row.canDelete && <button disabled={busy} onClick={() => {if (!window.confirm('确认永久删除这条评论？不可撤销。已有回复的顶层评论须前往 GitHub 管理；不会删除整篇讨论。')) return; void run(async () => {await api.request(`/comments/${encodeURIComponent(row.id)}`, 'DELETE', {updatedAt: row.updatedAt}); await reload(); setNotice('评论删除已由服务器读回确认')})}}>删除</button>}{!row.replyToId && <button disabled={busy} onClick={() => setReplyTo(row)}>回复</button>}</div>}
    {editing?.id === row.id && <form onSubmit={event => {event.preventDefault(); void run(saveEdit)}}><label>编辑留言<textarea aria-label="编辑留言" maxLength={5000} value={editBody} onChange={event => setEditBody(event.target.value)}/></label><button disabled={busy || !user || !editBody.trim()}>保存修改</button><button type="button" disabled={busy} onClick={() => {if (!window.confirm('放弃编辑草稿？')) return; setEditing(null)}}>取消编辑</button><p>版本冲突时不会覆盖。请复制草稿，刷新比较后重新编辑。</p></form>}
    {!row.replyToId && row.replyCount > 0 && <button disabled={busy} onClick={() => void run(() => loadReplies(row))}>查看回复（{row.replyCount}）</button>}
    {replies[row.id] && <div className="custom-comment-replies">{replies[row.id].nodes.map(item)}{replies[row.id].pageInfo.hasNextPage && <button disabled={busy} onClick={() => void run(() => loadReplies(row, true))}>更多回复</button>}<p>已显示 {replies[row.id].nodes.length} / {replies[row.id].totalCount} 条回复</p></div>}
  </article>}
  return <section className="custom-comments" aria-label="站内评论">
    <p>评论公开保存到复盘公共讨论，所有复盘时期共用。请勿提交私密资料。切换文章或收起后需重新登录；发表、回复与编辑草稿仅保留在本页内存，刷新页面会丢失。</p>
    {user ? <p>已登录：{user.login} <button disabled={busy} onClick={() => void run(async () => {try {await api.logout()} finally {setUser(null)} await reload()})}>退出登录</button></p> : <button disabled={busy} onClick={() => void run(async () => {const result = await api.login(); if (!live.current) return; setUser(result.user); await reload(!!editing?.replyToId)})}>使用 GitHub 登录 / 注册</button>}
    <button disabled={busy} onClick={() => {if (editing && !window.confirm('刷新列表将关闭编辑区域；请先复制编辑草稿。继续？')) return; void run(async () => {await reload(); setEditing(null)})}}>刷新站内评论</button>
    {error && <p role="alert">{error}</p>}<p role="status" aria-live="polite">{busy ? '正在处理，请勿重复提交…' : notice}</p>
    <form onSubmit={event => {event.preventDefault(); void run(async () => {await api.request('/comments', 'POST', {body, ...(replyTo ? {replyToId: replyTo.id} : {})}); setBody(''); setReplyTo(null); setNotice('发表已由服务器读回确认'); await reload()})}}>
      {replyTo && <p>回复 {replyTo.author?.login}<button type="button" onClick={() => setReplyTo(null)}>取消回复</button></p>}
      <label>发表留言<textarea aria-label="发表留言" maxLength={5000} value={body} onChange={event => setBody(event.target.value)}/></label><p>{body.length} / 5000</p><button disabled={busy || !user || !body.trim()}>发表</button>
    </form>
    {!page && !error && <p>正在加载真实评论…</p>}{page?.totalCount === 0 && <p>复盘公共讨论暂无评论。</p>}{page?.nodes.map(item)}
    {page?.pageInfo.hasNextPage && <button disabled={busy} onClick={() => void run(async () => {const next = await api.request('/comments?after=' + encodeURIComponent(page.pageInfo.endCursor!)) as CommentPage; setPage({...next, nodes: merge(page.nodes, next.nodes)})})}>更多评论</button>}
    {page && <p>已显示 {page.nodes.length} / {page.totalCount} 条顶层评论；回复单独展开。</p>}
  </section>
}
